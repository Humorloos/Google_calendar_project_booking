import datetime as dt
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pandas as pd
from flask import Flask, request
from flask_restful import Resource, Api

import googleApiScopes.calendar
from googleApiClientProvider import GoogleApiClientProvider
from utils import get_calendar_lookup, CALENDAR_LOOKUP_PATH, PROJECT_SUFFIX, local_datetime_from_string, \
    get_local_datetime, extract_local_datetime_or_nat, create_events_in_windows

FEIERABEND = dt.time(20)

CHANNEL_ID_KEY = 'X-Goog-Channel-Id'
SCOPES = [googleApiScopes.calendar.EVENTS, googleApiScopes.calendar.CALENDAR_READ_ONLY]
# Color ID that shall trigger splitting events (see https://lukeboyle.com/blog/posts/google-calendar-api-color-id)
SPLIT_COLOR_ID = '8'

app = Flask(__name__)
api = Api(app)

# setup logger
info_filehandler = RotatingFileHandler(Path('logs').joinpath('app.log'), maxBytes=10000000, backupCount=3)
info_filehandler.setLevel(logging.INFO)
logger = logging.getLogger()
logger.addHandler(info_filehandler)
logger.setLevel(logging.INFO)

# setup google calendar interface
api_provider = GoogleApiClientProvider(SCOPES)
calendar_service = api_provider.get_service('calendar', 'v3')


# log all requests
@app.before_request
def log_request_info():
    logger.info(f'Headers: {request.headers}')
    logger.info(f'Body: {request.get_data()}')


class CalendarHandler(Resource):
    @staticmethod
    def get():
        return 'This page only exists to handle calendar updates'

    @staticmethod
    def post():
        # only react to calendar API channel posts
        if CHANNEL_ID_KEY not in request.headers.keys():
            return
        channel_id = request.headers.get(CHANNEL_ID_KEY)

        # only react to channels in lookup table
        calendar_lookup = get_calendar_lookup()
        if channel_id not in calendar_lookup.index:
            return

        # get updated events
        calendar_row = calendar_lookup.loc[channel_id]
        target_calendar_id = calendar_row['calendar_id']
        updated_events_list_response = calendar_service.events().list(
            calendarId=target_calendar_id,
            syncToken=calendar_row['sync_token']
        ).execute()
        sync_token = updated_events_list_response['nextSyncToken']
        updated_events = pd.DataFrame(updated_events_list_response['items'])

        if len(updated_events) > 0 and 'updated' in updated_events.columns:
            updated_events = updated_events.sort_values(by='updated', ascending=False, ignore_index=True)
            # remember projects that were already updated to update each project only once
            updated_projects = set()
            for _, updated_event in updated_events.iterrows():
                if updated_event['status'] == 'confirmed':
                    # only trigger updates for events that belong to a project that hasn't been updated so far
                    if updated_event['summary'].endswith(PROJECT_SUFFIX) and \
                            updated_event['summary'] not in updated_projects:

                        # get events that belong to this project
                        project_events_list_response = calendar_service.events().list(
                            calendarId=target_calendar_id,
                            q=updated_event['summary'][:-3]
                        ).execute()
                        sync_token = project_events_list_response['nextSyncToken']

                        # update all events in this project except the event that triggered the update
                        new_description = updated_event['description']
                        for target_event in project_events_list_response['items']:
                            if target_event['id'] != updated_event['id'] and \
                                    target_event['summary'] == updated_event['summary'] and \
                                    target_event['description'] != new_description:
                                target_event['description'] = new_description
                                calendar_service.events().update(
                                    calendarId=target_calendar_id,
                                    eventId=target_event['id'],
                                    body=target_event,
                                ).execute()

                        updated_projects.add(updated_event['summary'])

                    if updated_event['colorId'] == SPLIT_COLOR_ID:
                        end_timestamp = local_datetime_from_string(updated_event['end']['dateTime'])
                        feierabend_timestamp = get_local_datetime(end_timestamp.date(), FEIERABEND)
                        split_timestamp = None
                        if end_timestamp > feierabend_timestamp:
                            split_timestamp = feierabend_timestamp
                        else:
                            interrupting_events_list_responses = [calendar_service.events().list(
                                calendarId=calendar_id,
                                # latest time that events may start
                                timeMax=updated_event['end']['dateTime'],
                                # earliest time that events may end
                                timeMin=updated_event['start']['dateTime'],
                                singleEvents=True,
                            ).execute() for calendar_id in calendar_lookup['calendar_id'].values]
                            sync_token = interrupting_events_list_responses[-1]['nextSyncToken']
                            interrupting_events = pd.DataFrame([
                                event for interrupting_events_list_response in interrupting_events_list_responses
                                for event in interrupting_events_list_response['items']
                                if event['id'] != updated_event['id'] and 'dateTime' in event['start'].keys()
                            ])
                            if len(interrupting_events) > 0:
                                split_timestamp = interrupting_events['start'].apply(extract_local_datetime_or_nat).min()
                        if split_timestamp is not None:
                            duration_to_trim = end_timestamp - split_timestamp

                            # update event to end at split timestamp
                            updated_event = updated_event.to_dict()
                            del updated_event['colorId']
                            updated_event['end']['dateTime'] = split_timestamp.isoformat()
                            calendar_service.events().update(
                                calendarId=target_calendar_id,
                                eventId=updated_event['id'],
                                body=updated_event
                            ).execute()

                            # create new event starting at next free position and ending after time cut from original event
                            # that is otherwise identical
                            create_events_in_windows(
                                calendar_ids=calendar_lookup['calendar_id'].values,
                                calendar_service=calendar_service,
                                start_timestamp=split_timestamp,
                                duration=duration_to_trim,
                                target_event_summary=updated_event['summary'],
                                target_event_description=updated_event['description'],
                                target_calendar_id=target_calendar_id,
                                feierabend=FEIERABEND,
                            )

        # remember the last time we retrieved events for next update
        calendar_lookup.loc[channel_id, 'sync_token'] = sync_token
        calendar_lookup.to_csv(CALENDAR_LOOKUP_PATH)


api.add_resource(CalendarHandler, '/')

if __name__ == '__main__':
    app.run(debug=True)
