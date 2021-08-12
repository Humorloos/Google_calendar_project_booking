"""
Script for setting up google calendar watches for specified time and save map from uuids to calendar ids
"""
import datetime as dt
import pickle
import uuid
from pathlib import Path

import googleApiScopes.calendar
from googleApiClientProvider import GoogleApiClientProvider
from utils import get_calendar_ids

SCOPES = [googleApiScopes.calendar.EVENTS, googleApiScopes.calendar.CALENDAR_READ_ONLY]
WATCH_DURATION = str(int(dt.timedelta(days=1, hours=6).total_seconds()))
CALENDAR_LOOKUP_PATH = Path('resources').joinpath('calendar_lookup.pickle')

client_provider = GoogleApiClientProvider(SCOPES)
calendar_service = client_provider.get_service(name="calendar", version='v3')

# Close old channels
with open(CALENDAR_LOOKUP_PATH, 'rb') as in_file:
    previous_channels = pickle.load(in_file)

for channel_id, id_dict in previous_channels.items():
    calendar_service.channels().stop(body={'id': channel_id, 'resourceId': id_dict['resource_id']})

# Open new channels
calendar_ids = get_calendar_ids(calendar_service)
calendar_lookup = {str(uuid.uuid1()): {'calendar_id': calendar_id} for calendar_id in calendar_ids}

responses = [calendar_service.events().watch(
    calendarId=id_dict['calendar_id'],
    body={
        "id": channel_id,
        "token": "my token",
        "type": "web_hook",
        "address": "https://humorloos.pythonanywhere.com/",
        "params": {
            "ttl": WATCH_DURATION
        }
    }
).execute() for channel_id, id_dict in calendar_lookup.items()]

for response in responses:
    calendar_lookup[response['id']]['resource_id'] = response['resourceId']
with open(CALENDAR_LOOKUP_PATH, 'wb') as out_file:
    pickle.dump(calendar_lookup, out_file)
