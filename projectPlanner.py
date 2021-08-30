from __future__ import print_function

import datetime as dt
from typing import Dict

import pandas as pd

import googleApiScopes.calendar
import googleApiScopes.tasks
from googleApiClientProvider import GoogleApiClientProvider
from utils import PROJECT_SUFFIX

SCOPES = [googleApiScopes.calendar.CALENDAR_READ_ONLY,
          googleApiScopes.calendar.EVENTS,
          googleApiScopes.tasks.TASKS_READ_ONLY]

# Day at which to start creating events
START_DAY = dt.date.today()
# Time at which to start creating events
START_TIME = dt.datetime.utcnow().time()
# Time after which not to create any more events
FEIERABEND = dt.time(20)
# Estimated duration of the project to book
PROJECT_DURATION = pd.Timedelta(hours=20, minutes=15)
# Name of calendar to create events in
TARGET_CALENDAR_NAME = 'Privat'
# color id for events to create, see https://lukeboyle.com/blog/posts/google-calendar-api-color-id
COLOR_ID = 7
# # Time to block for tasks
# TASK_DURATION = dt.timedelta(minutes=15)
# Summary for the events to create for the project
PROJECT_SUMMARY = 'IE 674 Prüfungsvorbereitung'
# Description for the events to create for the project
PROJECT_DESCRIPTION = """Prüfungsvorbereitung
Karten
1825 2:00:00 ✅
1708 2:00:00 ✅
1590 2:00:00 ✅
1473 2:00:00 ✅
1355 2:00:00 ✅
1238 2:00:00 ✅
1120 2:00:00 ✅
1003 2:00:00 ✅
885 2:00:00 ✅
767 2:00:00 ✅
650 2:00:00 ✅
532 2:00:00 rest: 1:00
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


def main():
    client_provider = GoogleApiClientProvider(SCOPES)

    calendar_service = client_provider.get_calendar_service()
    calendar_ids = calendar_service.calendar_ids
    # TODO: When tasks api is better (tasks are retrieved with correct due date), add the task lines again.
    # tasks_service = client_provider.get_google_calendar_service('tasks', 'v1')
    # tasklist_ids = [item['id'] for item in tasks_service.tasklists().list().execute()['items']]

    calendar_service.create_events_in_windows(
        calendar_ids=calendar_ids,
        start_timestamp=calendar_service.get_local_datetime(day=START_DAY, time=START_TIME),
        duration=PROJECT_DURATION,
        feierabend=FEIERABEND,
        target_calendar_id=calendar_service.calendar_dict[TARGET_CALENDAR_NAME],
        target_event_summary=PROJECT_SUMMARY + PROJECT_SUFFIX,
        target_event_color_id=COLOR_ID,
        description=PROJECT_DESCRIPTION,
    )


def items_or_empty_list(response: Dict):
    if 'items' in response.keys():
        return response['items']
    else:
        return []


# def get_task_timeframe(task: Dict):
#     start_time = local_datetime_from_string(task['due'])
#     return {'start': start_time, 'end': start_time + TASK_DURATION}


if __name__ == '__main__':
    main()
