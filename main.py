from __future__ import print_function

import datetime as dt

import pandas as pd

# If modifying these scopes, delete the file token.json.
from utils import get_google_calendar_service, get_local_datetime, local_datetime_from_string, get_consecutive_event, \
    get_following_event

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/calendar.events']

# Day at which to start creating events
START_DAY = dt.date.today()
# Time after which not to create any more events
FEIERABEND = dt.time(20)
# Estimated duration of the project to book
PROJECT_DURATION = pd.Timedelta(hours=14)
# Summary for the events to create for the project
PROJECT_SUMMARY = 'IE 674 Assignment 2'


def main():
    service = get_google_calendar_service(SCOPES)
    remaining_duration = PROJECT_DURATION
    calendar_ids = [item['id'] for item in service.calendarList().list().execute()['items'] if
                    item['accessRole'] == 'owner' and not item['summary'] == 'Scheduler']
    current_day = START_DAY
    while remaining_duration > pd.Timedelta(0):
        # get all events for the current day
        events = []
        end_datetime = get_local_datetime(current_day, FEIERABEND)
        for calendar_id in calendar_ids:
            events.extend(service.events().list(
                calendarId=calendar_id,
                timeMin=get_local_datetime(current_day, dt.time(0)).isoformat(),
                singleEvents=True,
                orderBy='startTime',
                timeMax=end_datetime.isoformat()
            ).execute()['items'])
        event_data = pd.DataFrame({
            'start': [local_datetime_from_string(event['start']['dateTime']) for event in events],
            'end': [local_datetime_from_string(event['end']['dateTime']) for event in events]
        })
        event_data = event_data.append({'start': end_datetime, 'end': pd.NaT}, ignore_index=True)
        time_windows = pd.DataFrame(columns=['start', 'end'])
        current_event = event_data.loc[event_data['start'].idxmin()]
        # find all time windows for the current day
        while pd.notnull(current_event['end']) and current_event['end'] < end_datetime:
            try:
                # check if there is an adjacent/overlapping event
                current_event = get_consecutive_event(event=current_event, event_data=event_data)
            except ValueError:
                # if not, add the time window and jump to the next event
                window_start = current_event['end']
                # go to first event after end of current event
                current_event = get_following_event(event=current_event, event_data=event_data)
                window_end = current_event['start']
                # Add only time windows larger than 15 minutes
                if window_end - window_start > pd.Timedelta(minutes=15):
                    time_windows = time_windows.append({'start': window_start, 'end': window_end}, ignore_index=True)
        # create events for all time windows
        for _, row in time_windows.iterrows():
            window_width = row['end'] - row['start']
            if remaining_duration > window_width:
                create_event(service=service, start=row['start'], end=row['end'], summary=PROJECT_SUMMARY, colorId=2)
                remaining_duration -= window_width
            else:
                create_event(service=service, start=row['start'], end=row['start'] + remaining_duration, summary=PROJECT_SUMMARY,
                             colorId=2)
                remaining_duration -= remaining_duration
                break
        current_day += pd.Timedelta(days=1)


def create_event(service, start, end, summary, description='', colorId=1):
    service.events().insert(calendarId='primary', body={
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
