from __future__ import print_function

import datetime as dt
import os.path

import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from tzlocal import get_localzone

# If modifying these scopes, delete the file token.json.
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
    service = get_google_calendar_service()
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
                current_event = event_data.loc[event_data[
                    (event_data['start'] <= current_event['end']) & (event_data['end'] > current_event['end'])
                    ]['end'].idxmax()]
            except ValueError:
                # if not, add the time window and jump to the next event
                window_start = current_event['end']
                # go to first event after end of current event
                current_event = event_data.loc[event_data[
                    event_data['start'] - current_event['end'] > pd.Timedelta(0)
                    ]['start'].idxmin()]
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


def get_local_datetime(day, time):
    return pd.Timestamp(dt.datetime.combine(day, time), tzinfo=get_localzone())


def local_datetime_from_string(datetime_string):
    return pd.Timestamp(datetime_string).tz_convert(get_localzone())


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


def get_google_calendar_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)


if __name__ == '__main__':
    main()
