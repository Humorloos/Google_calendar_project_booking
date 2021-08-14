import uuid
import datetime as dt
import googleApiScopes.calendar
from googleApiClientProvider import GoogleApiClientProvider
from utils import get_calendar_ids, calendar_id_from_summary

TARGET_TITLE = " -p"
NEW_DESCRIPTION = """Prüfungsvorbereitung
Karten
1825 2:00:00
1708 2:00:00
1590 2:00:00
1473 2:00:00
1355 2:00:00
1238 2:00:00
1120 2:00:00
1003 2:00:00
885 2:00:00
767 2:00:00
650 2:00:00
532 2:00:00
415 2:00:00
297 2:00:00
180 2:00:00
62 2:00:00
0 0:45:00
Exercises
Exercise 1 durchgehen 0:45:00
Exercise 2 durchgehen 0:45:00
Exercise 3 durchgehen 0:45:00
Exercise 4 durchgehen 0:45:00
Exercise 5 durchgehen 0:45:00
Exercise 6 durchgehen 0:45:00
Assignments
Assignment 1 durchgehen 2:00:00
Assignment 2 durchgehen 2:00:00
Assignment 3 durchgehen 2:00:00
gesamt 43:15:00"""

SCOPES = [googleApiScopes.calendar.EVENTS, googleApiScopes.calendar.CALENDAR_READ_ONLY]

client_provider = GoogleApiClientProvider(SCOPES)

calendar_service = client_provider.get_calendar_service()

calendar_ids = calendar_service.calendar_ids


channel_ids = [str(uuid.uuid1()) for _ in calendar_ids]
watch_duration = str(int(dt.timedelta(days=1).total_seconds()))
watch_responses = [
    calendar_service.service.events().watch(
        calendarId=calendar_id,
        body={
            "id": channel_id,
            "token": "my token",
            "type": "web_hook",
            "address": "https://humorloos.pythonanywhere.com/",
            "params": {
                "ttl": watch_duration
            }
        }

    ).execute() for calendar_id, channel_id in zip(calendar_ids, channel_ids)
]

target_events = [item for calendar_id in calendar_ids for item in
                 calendar_service.service.events().list(calendarId=calendar_id, q=TARGET_TITLE).execute()['items'] if
                 item['summary'] == TARGET_TITLE]

for target_event in target_events:
    target_event['description'] = NEW_DESCRIPTION
