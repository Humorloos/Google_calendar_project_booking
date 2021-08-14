from __future__ import print_function

import datetime as dt
from typing import Dict

import pandas as pd
import googleApiScopes.calendar
import googleApiScopes.tasks

# If modifying these scopes, delete the file token.json.
from googleApiClientProvider import GoogleApiClientProvider
from utils import get_local_datetime, get_calendar_ids, PROJECT_SUFFIX, calendar_id_from_summary, \
    create_events_in_windows

SCOPES = [googleApiScopes.calendar.CALENDAR_READ_ONLY,
          googleApiScopes.calendar.EVENTS,
          googleApiScopes.tasks.TASKS_READ_ONLY]

# Day at which to start creating events
START_DAY = dt.date.today()
# Time at which to start creating events
START_TIME = dt.time(0)
# Time after which not to create any more events
FEIERABEND = dt.time(20)
# Estimated duration of the project to book
PROJECT_DURATION = pd.Timedelta(hours=3)
# Name of calendar to create events in
TARGET_CALENDAR_NAME = 'Privat'
# color id for events to create, see https://lukeboyle.com/blog/posts/google-calendar-api-color-id
COLOR_ID = 7
# # Time to block for tasks
# TASK_DURATION = dt.timedelta(minutes=15)
# Summary for the events to create for the project
PROJECT_SUMMARY = 'test'
# Description for the events to create for the project
PROJECT_DESCRIPTION = """test"""


def main():
    client_provider = GoogleApiClientProvider(SCOPES)

    calendar_service = client_provider.get_service('calendar', 'v3')
    calendar_ids = get_calendar_ids(calendar_service)
    # TODO: When tasks api is better (tasks are retrieved with correct due date), add the task lines again.
    # tasks_service = client_provider.get_google_calendar_service('tasks', 'v1')
    # tasklist_ids = [item['id'] for item in tasks_service.tasklists().list().execute()['items']]

    create_events_in_windows(
        calendar_ids=calendar_ids,
        calendar_service=calendar_service,
        start_timestamp=get_local_datetime(day=START_DAY, time=START_TIME),
        duration=PROJECT_DURATION,
        feierabend=FEIERABEND,
        target_calendar_id=calendar_id_from_summary(calendar_service, TARGET_CALENDAR_NAME),
        target_event_description=PROJECT_DESCRIPTION,
        target_event_summary=PROJECT_SUMMARY + PROJECT_SUFFIX,
        target_event_color_id=COLOR_ID,
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
