import datetime as dt
import os.path

import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from tzlocal import get_localzone


def get_google_calendar_service(scopes):
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', scopes)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', scopes)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)


def get_local_datetime(day, time):
    return pd.Timestamp(dt.datetime.combine(day, time), tzinfo=get_localzone())


def local_datetime_from_string(datetime_string):
    return pd.Timestamp(datetime_string).tz_convert(get_localzone())


def get_consecutive_event(event, event_data, precision=0):
    return event_data.loc[event_data[
        (event_data['start'] <= event['end'].ceil(f'{precision}min')) & (event_data['end'] > event['end'])
        ]['end'].idxmax()]


def get_following_event(event, event_data):
    return event_data.loc[event_data[event_data['start'] - event['end'] > pd.Timedelta(0)]['start'].idxmin()]
