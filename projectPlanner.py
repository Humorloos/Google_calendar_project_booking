import datetime as dt
from typing import Dict

import pandas as pd

import googleApiScopes.calendar
import googleApiScopes.tasks
from googleApiClientProvider import GoogleApiClientProvider
from utils import PROJECT_ARGUMENT

# Summary for the events to create for the project
PROJECT_SUMMARY = 'CS 715 Research and Analysis'
# Description for the events to create for the project
PROJECT_DESCRIPTION = """recherche	8h
data analysis	4h"""
# Estimated duration of the project to book
PROJECT_DURATION = pd.Timedelta(hours=12, minutes=0)
# color id for events to create, see https://lukeboyle.com/blog/posts/google-calendar-api-color-id
COLOR_ID = 7
# Name of calendar to create events in
TARGET_CALENDAR_NAME = 'Privat'

# Day at which to start creating events
START_DAY = dt.date.today()
# Time at which to start creating events
START_TIME = dt.datetime.utcnow().time()
# Time after which not to create any more events
FEIERABEND = dt.time(20)
# # Time to block for tasks
# TASK_DURATION = dt.timedelta(minutes=15)

SCOPES = [googleApiScopes.calendar.CALENDAR_READ_ONLY,
          googleApiScopes.calendar.EVENTS,
          googleApiScopes.tasks.TASKS_READ_ONLY]


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
        target_event_summary=PROJECT_SUMMARY + PROJECT_ARGUMENT,
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
