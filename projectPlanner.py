from __future__ import print_function

import datetime as dt

import pandas as pd

# If modifying these scopes, delete the file token.json.
from googleApiClientProvider import GoogleApiClientProvider
from utils import get_local_datetime, local_datetime_from_string, get_consecutive_event, \
    get_following_event

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/calendar.events',
          'https://www.googleapis.com/auth/tasks.readonly']

# Day at which to start creating events
START_DAY = dt.date.today()
# Time after which not to create any more events
FEIERABEND = dt.time(20)
# Estimated duration of the project to book
PROJECT_DURATION = pd.Timedelta(hours=43, minutes=15)
# Name of calendar to create events in
TARGET_CALENDAR_NAME = 'Privat'
# color id for events to create, see https://lukeboyle.com/blog/posts/google-calendar-api-color-id
COLOR_ID = 7
# Summary for the events to create for the project
PROJECT_SUMMARY = 'IE 672 Prüfungsvorbereitung'
# Description for the events to create for the project
PROJECT_DESCRIPTION = """Prüfungsvorbereitung	
Karten	
1825	2:00:00
1708	2:00:00
1590	2:00:00
1473	2:00:00
1355	2:00:00
1238	2:00:00
1120	2:00:00
1003	2:00:00
885	2:00:00
767	2:00:00
650	2:00:00
532	2:00:00
415	2:00:00
297	2:00:00
180	2:00:00
62	2:00:00
0	0:45:00
Exercises	
Exercise 1 durchgehen	0:45:00
Exercise 2 durchgehen	0:45:00
Exercise 3 durchgehen	0:45:00
Exercise 4 durchgehen	0:45:00
Exercise 5 durchgehen	0:45:00
Exercise 6 durchgehen	0:45:00
Assignments	
Assignment 1 durchgehen	2:00:00
Assignment 2 durchgehen	2:00:00
Assignment 3 durchgehen	2:00:00
gesamt	43:15:00"""


def main():
    client_provider = GoogleApiClientProvider(SCOPES)
    calendar_service = client_provider.get_google_calendar_service('calendar', 'v3')
    remaining_duration = PROJECT_DURATION
    calendar_ids = [item['id'] for item in calendar_service.calendarList().list().execute()['items'] if
                    item['accessRole'] == 'owner' and not item['summary'] == 'Scheduler']
    current_day = START_DAY
    while remaining_duration > pd.Timedelta(0):
        # get all events for the current day
        events = []
        end_datetime = get_local_datetime(current_day, FEIERABEND)
        for calendar_id in calendar_ids:
            events.extend(calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=get_local_datetime(current_day, dt.time(0)).isoformat(),
                singleEvents=True,
                orderBy='startTime',
                timeMax=end_datetime.isoformat()
            ).execute()['items'])

        # Remove 'All Day' events
        events = [event for event in events if 'dateTime' in event['start'].keys()]

        event_data = pd.DataFrame({
            'start': [local_datetime_from_string(event['start']['dateTime']) for event in events],
            'end': [local_datetime_from_string(event['end']['dateTime']) for event in events]
        })
        event_data = event_data.append({'start': end_datetime, 'end': pd.NaT}, ignore_index=True)
        time_windows = pd.DataFrame(columns=['start', 'end'])
        current_event = event_data.loc[event_data['start'].idxmin()]
        # find all time windows for the current day
        while pd.notnull(current_event['end']) and current_event['end'] < end_datetime:
            # check if there is an adjacent/overlapping event
            current_event = get_consecutive_event(event=current_event, event_data=event_data)
            if not current_event:
                # if not, add the time window and jump to the next event
                window_start = current_event['end']
                # go to first event after end of current event
                current_event = get_following_event(event=current_event, event_data=event_data)
                window_end = current_event['start']
                # Add only time windows larger than 15 minutes
                if window_end - window_start > pd.Timedelta(minutes=15):
                    time_windows = time_windows.append({'start': window_start, 'end': window_end}, ignore_index=True)

        target_calendar_id = next(item['id'] for item in calendar_service.calendarList().list().execute()['items'] if
                                  item['accessRole'] == 'owner' and item['summary'] == TARGET_CALENDAR_NAME)

        # create events for all time windows
        for _, row in time_windows.iterrows():
            window_width = row['end'] - row['start']
            if remaining_duration > window_width:
                create_event(service=calendar_service, start=row['start'], end=row['end'], summary=PROJECT_SUMMARY,
                             description=PROJECT_DESCRIPTION, colorId=COLOR_ID, calendar_id=target_calendar_id)
                remaining_duration -= window_width
            else:
                create_event(service=calendar_service, start=row['start'], end=row['start'] + remaining_duration,
                             summary=PROJECT_SUMMARY, description=PROJECT_DESCRIPTION, colorId=COLOR_ID,
                             calendar_id=target_calendar_id)
                remaining_duration -= remaining_duration
                break
        current_day += pd.Timedelta(days=1)


def create_event(service, start, end, summary, description='', colorId=1, calendar_id='primary'):
    service.events().insert(calendarId=calendar_id, body={
        'start': {
            'dateTime': start.isoformat()
        },
        'end': {
            'dateTime': end.isoformat()
        },
        'summary': summary,
        'description': description,
        'colorId': colorId
    }).execute()


if __name__ == '__main__':
    main()
