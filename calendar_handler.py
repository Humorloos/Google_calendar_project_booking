import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pandas as pd
from flask import Flask, request
from flask_restful import Resource, Api

import googleApiScopes.calendar
from googleApiClientProvider import GoogleApiClientProvider
from utils import get_calendar_lookup, CALENDAR_LOOKUP_PATH, PROJECT_SUFFIX

CHANNEL_ID_KEY = 'X-Goog-Channel-Id'
SCOPES = [googleApiScopes.calendar.EVENTS, googleApiScopes.calendar.CALENDAR_READ_ONLY]

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
        updated_events = pd.DataFrame(updated_events_list_response['items']).sort_values(by='updated', ascending=False)

        if len(updated_events) > 0:
            # remember projects that were already updated to update each project only once
            updated_projects = set()
            for _, updated_event in updated_events.iterrows():
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

        # remember the last time we retrieved events for next update
        calendar_lookup.loc[channel_id, 'sync_token'] = sync_token
        calendar_lookup.to_csv(CALENDAR_LOOKUP_PATH)


api.add_resource(CalendarHandler, '/')

if __name__ == '__main__':
    app.run(debug=True)
