from __future__ import print_function

import datetime as dt
from typing import Dict

import pandas as pd
import googleApiScopes.calendar
import googleApiScopes.tasks

# If modifying these scopes, delete the file token.json.
from googleApiClientProvider import GoogleApiClientProvider
from utils import get_local_datetime, local_datetime_from_string, get_consecutive_event, \
    get_following_event, get_calendar_ids, PROJECT_SUFFIX

SCOPES = [googleApiScopes.calendar.CALENDAR_READ_ONLY,
          googleApiScopes.calendar.EVENTS,
          googleApiScopes.tasks.TASKS_READ_ONLY]

# Day at which to start creating events
START_DAY = dt.date.today()
# Time after which not to create any more events
FEIERABEND = dt.time(20)
# Estimated duration of the project to book
PROJECT_DURATION = pd.Timedelta(hours=43, minutes=15)
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
1825	2:00:00
1708	2:00:00
1590	2:00:00
1473	2:00:00
1355	2:00:00
1238	2:00:00
1120	2:00:00
1003	2:00:00
885	2:00:00
767	2:00:00
650	2:00:00
532	2:00:00
415	2:00:00
297	2:00:00
180	2:00:00
62	2:00:00
0	0:45:00
Exercises	
Exercise 1 durchgehen	0:45:00
Exercise 2 durchgehen	0:45:00
Exercise 3 durchgehen	0:45:00
Exercise 4 durchgehen	0:45:00
Exercise 5 durchgehen	0:45:00
Exercise 6 durchgehen	0:45:00
Assignments	
Assignment 1 durchgehen	2:00:00
Assignment 2 durchgehen	2:00:00
Assignment 3 durchgehen	2:00:00
gesamt	43:15:00"""


def main():
    client_provider = GoogleApiClientProvider(SCOPES)

    calendar_service = client_provider.get_service('calendar', 'v3')
    calendar_ids = get_calendar_ids(calendar_service)
    # TODO: When tasks api is better (tasks are retrieved with correct due date), add the task lines again.
    # tasks_service = client_provider.get_google_calendar_service('tasks', 'v1')
    # tasklist_ids = [item['id'] for item in tasks_service.tasklists().list().execute()['items']]
    time_windows = pd.DataFrame(columns=['start', 'end'])
    remaining_duration = PROJECT_DURATION
    current_day = START_DAY
    while remaining_duration > pd.Timedelta(0):
        # get all events for the current day
        end_datetime = get_local_datetime(current_day, FEIERABEND)
        start_rfc_3339_timestamp = get_local_datetime(current_day, dt.time(0)).isoformat()
        end_rfc_3339_timestamp = end_datetime.isoformat()
        events = [event for calendar_id in calendar_ids for event in calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=start_rfc_3339_timestamp,
            timeMax=end_rfc_3339_timestamp,
            singleEvents=True,
            orderBy='startTime',
        ).execute()['items'] if 'dateTime' in event['start'].keys()]

        # # get all tasks for the current day
        # tasks = [task for tasklist_id in tasklist_ids for task in items_or_empty_list(tasks_service.tasks().list(
        #     tasklist=tasklist_id,
        #     dueMin=start_rfc_3339_timestamp,
        #     dueMax=end_rfc_3339_timestamp,
        # ).execute())]

        event_df = pd.DataFrame(
            # Events
            [{
                'start': local_datetime_from_string(event['start']['dateTime']),
                'end': local_datetime_from_string(event['end']['dateTime'])
            } for event in events] +
            # # Tasks
            # [get_task_timeframe(task) for task in tasks] +
            # End placeholder
            [{'start': end_datetime, 'end': pd.NaT}]
        ).sort_values(by='start')

        current_event = event_df.iloc[0]
        # find all time windows for the current day
        while pd.notnull(current_event['end']) and current_event['end'] < end_datetime:
            # check if there is an adjacent/overlapping event
            consecutive_event = get_consecutive_event(event=current_event, event_data=event_df)
            if consecutive_event is None:
                # if not, add the time window and jump to the next event
                window_start = current_event['end']
                # go to first event after end of current event
                current_event = get_following_event(event=current_event, event_data=event_df)
                window_end = current_event['start']
                # Add only time windows larger than 15 minutes
                window_width = window_end - window_start
                if window_width > pd.Timedelta(minutes=15):
                    if window_width < remaining_duration:
                        time_windows = time_windows.append({'start': window_start, 'end': window_end},
                                                           ignore_index=True)
                        remaining_duration -= window_width
                    else:
                        time_windows = time_windows.append(
                            {'start': window_start, 'end': window_start + remaining_duration}, ignore_index=True)
                        remaining_duration -= remaining_duration
                        break

            else:
                current_event = consecutive_event
        current_day += pd.Timedelta(days=1)

    target_calendar_id = next(item['id'] for item in calendar_service.calendarList().list().execute()['items'] if
                              item['accessRole'] == 'owner' and item['summary'] == TARGET_CALENDAR_NAME)

    # create events for all time windows
    for _, row in time_windows.iterrows():
        create_event(service=calendar_service, start=row['start'], end=row['end'],
                     summary=PROJECT_SUMMARY + PROJECT_SUFFIX, description=PROJECT_DESCRIPTION, colorId=COLOR_ID,
                     calendar_id=target_calendar_id)


def create_event(service, start, end, summary, description='', colorId=1, calendar_id='primary'):
    service.events().insert(calendarId=calendar_id, body={
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
