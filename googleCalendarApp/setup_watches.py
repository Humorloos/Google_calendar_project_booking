"""
Script for setting up google calendar watches for specified time and save map from uuids to calendar ids
"""
import datetime as dt
import sys
import uuid

import pandas as pd

from constants import GOOGLE_API_PATH, CALENDAR_LOOKUP_PATH, PROJECT_DIR, CALENDAR_URI

# add your project directory to the sys.path
sys.path = list({path for path in [str(PROJECT_DIR.joinpath(project_name)) for project_name in [
    'googleCalendarApp',
    'GoogleApiHelper',
    'bouldernFormsApp'
]] + sys.path})

import googleApiScopes.calendar
from googleApiHelper.googleApiClientProvider import GoogleApiClientProvider
from utils import get_calendar_lookup

SCOPES = [googleApiScopes.calendar.EVENTS, googleApiScopes.calendar.CALENDAR_READ_ONLY]
WATCH_DURATION = str(int(dt.timedelta(days=1, hours=6).total_seconds()))

client_provider = GoogleApiClientProvider(SCOPES, GOOGLE_API_PATH)
calendar_service = client_provider.get_calendar_service()

# Close old channels
calendar_lookup = get_calendar_lookup()

for channel_id, row in calendar_lookup.iterrows():
    calendar_service.service.channels().stop(body={'id': channel_id, 'resourceId': row['resource_id']})

# Open new channels
calendar_ids = calendar_service.calendar_ids
calendar_lookup = calendar_lookup[calendar_lookup['calendar_id'].isin(calendar_ids)]
if len(calendar_ids) > len(calendar_lookup):
    calendar_lookup = calendar_lookup.append(
        {'calendar_id': calendar_id for calendar_id in calendar_ids if
         calendar_id not in calendar_lookup['calendar_id'].values}, ignore_index=True
    )
calendar_lookup.index = pd.Series([str(uuid.uuid1()) for _ in calendar_lookup.index], name='channel_id')

responses = [calendar_service.service.events().watch(
    calendarId=row['calendar_id'],
    body={
        "id": channel_id,
        "token": "my token",
        "type": "web_hook",
        "address": f"https://humorloos.pythonanywhere.com/{CALENDAR_URI}/",
        "params": {
            "ttl": WATCH_DURATION
        }
    }
).execute() for channel_id, row in calendar_lookup.iterrows()]

calendar_lookup['resource_id'] = [response['resourceId'] for response in responses]
calendar_lookup.to_csv(CALENDAR_LOOKUP_PATH)
