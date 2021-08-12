import datetime as dt
import pickle
import uuid
from pathlib import Path

import googleApiScopes.calendar
from googleApiClientProvider import GoogleApiClientProvider
from utils import get_calendar_ids

SCOPES = [googleApiScopes.calendar.EVENTS, googleApiScopes.calendar.CALENDAR_READ_ONLY]
WATCH_DURATION = str(int(dt.timedelta(minutes=2).total_seconds()))
CALENDAR_LOOKUP_PATH = Path()

client_provider = GoogleApiClientProvider(SCOPES)

calendar_service = client_provider.get_service(name="calendar", version='v3')

calendar_ids = get_calendar_ids(calendar_service)

calendar_lookup = {str(uuid.uuid1()): calendar_id for calendar_id in calendar_ids}

for channel_id, calendar_id in calendar_lookup.items():
    calendar_service.events().watch(
        calendarId=calendar_id,
        body={
            "id": channel_id,
            "token": "my token",
            "type": "web_hook",
            "address": "https://humorloos.pythonanywhere.com/",
            "params": {
                "ttl": WATCH_DURATION
            }
        }
    ).execute()

pickle.dump(calendar_lookup, )