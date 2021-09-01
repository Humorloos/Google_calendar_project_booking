import datetime as dt
from functools import cached_property
from typing import Tuple, List, Dict, Optional

import pandas as pd
from pytz import timezone

from utils import get_consecutive_event, get_following_event

CALENDARS_TO_IGNORE = {'Scheduler', 'Blocker'}


class CalendarService:
    def __init__(self, service):
        self.service = service

    @cached_property
    def calendar_dict(self):
        return {
            item['summary']: item['id'] for item in self.service.calendarList().list().execute()['items']
            if item['accessRole'] == 'owner' and
               not item['summary'] in CALENDARS_TO_IGNORE
        }

    @cached_property
    def calendar_ids(self):
        return [calendar_id for calendar_id in self.calendar_dict.values()]

    @cached_property
    def timezone(self):
        return timezone(self.service.settings().get(setting='timezone').execute()['value'])

    def get_event_df_and_next_sync_token(self, calendar_id, sync_token=None, query=None, time_max=None,
                                         time_min=None):
        events, sync_token = self.get_events_and_next_sync_token(calendar_id, query, sync_token, time_max, time_min)
        return pd.DataFrame(events), sync_token

    def get_events_and_next_sync_token(self, calendar_id: str, query: Optional[str], sync_token: Optional[str],
                                       time_max: Optional[str], time_min: Optional[str]) -> Tuple[List[Dict], str]:
        """
        Gets all events subject to the provided parameters as returned by google api and the sync token to find updated
        events with the next request
        :param calendar_id: id of the calendar from which to retrieve the events
        :param query: query for filtering events in the google api call
        :param sync_token: last sync token to only get updated events
        :param time_max: latest time that events may start
        :param time_min: earliest time that events may end
        :return: List of all events satisfying the specified conditions and the new sync token
        """
        updated_events_list_response = self.service.events().list(
            calendarId=calendar_id,
            syncToken=sync_token,
            maxResults=2500,
            singleEvents=True,
            q=query,
            timeMax=time_max,
            timeMin=time_min,
        ).execute()
        events = updated_events_list_response['items']
        while 'nextSyncToken' not in updated_events_list_response.keys():
            updated_events_list_response = self.service.events().list(
                calendarId=calendar_id,
                syncToken=sync_token,
                maxResults=2500,
                singleEvents=True,
                q=query,
                timeMax=time_max,
                timeMin=time_min,
                pageToken=updated_events_list_response['nextPageToken'],
            ).execute()
            events.extend(updated_events_list_response['items'])
        return events, updated_events_list_response['nextSyncToken']

    def create_events_in_windows(self, start_timestamp: pd.Timestamp, duration: pd.Timedelta, target_calendar_id: str,
                                 target_event_summary: str, calendar_ids: List[str],
                                 feierabend: dt.time, target_event_color_id: Optional[int] = None,
                                 **optional_fields) -> None:
        """
        Starting at the specified time, creates events at all slots that are empty in all specified calendars
        :param start_timestamp: datetime at which to start creating events
        :param duration: total duration created events should cover
        :param target_calendar_id: id of the calendar in which to create the events
        :param target_event_summary: summary of the events to create
        :param calendar_ids: ids of the calendars whose events should not be covered when creating new events
        :param feierabend: latest time that created events may end
        :param target_event_color_id: color id of the events to create (see
        https://lukeboyle.com/blog/posts/google-calendar-api-color-id)
        :param optional_fields: additional fields like 'location' or 'description' to add to the created events
        """
        time_windows = pd.DataFrame(columns=['start', 'end'])
        remaining_duration = duration
        first_week = True
        while remaining_duration > pd.Timedelta(0):
            # get all events for one week
            end_timestamp = start_timestamp + dt.timedelta(weeks=1)
            start_rfc_3339_timestamp = start_timestamp.isoformat()
            end_rfc_3339_timestamp = end_timestamp.isoformat()
            events = pd.DataFrame([
                event for calendar_id in calendar_ids for event in self.service.events().list(
                    calendarId=calendar_id,
                    timeMax=end_rfc_3339_timestamp,
                    timeMin=start_rfc_3339_timestamp,
                    singleEvents=True,
                ).execute()['items']
                if 'dateTime' in event['start'].keys()
            ])
            events[['start', 'end']] = events[['start', 'end']].apply(
                lambda col: col.apply(self.extract_local_datetime_or_nat))
            events = events.sort_values(by='start', ignore_index=True)

            # # get all tasks for the current day
            # tasks = [task for tasklist_id in tasklist_ids for task in items_or_empty_list(tasks_service.tasks().list(
            #     tasklist=tasklist_id,
            #     dueMin=start_rfc_3339_timestamp,
            #     dueMax=end_rfc_3339_timestamp,
            # ).execute())]
            if first_week:
                current_event = events.loc[0]
                first_week = False
            # find all time windows for this week
            while True:
                # If the last event of the week was reached, add time window until end of day if necessary and exit loop
                if current_event.name == events.index.max():
                    if current_event['end'].time() < feierabend:
                        time_windows = time_windows.append({
                            'start': current_event['end'],
                            'end': self.get_local_datetime(window_start.date(), feierabend)
                        }, ignore_index=True)
                    break

                # check if there is an adjacent/overlapping event
                consecutive_event = get_consecutive_event(event=current_event, event_data=events)
                if consecutive_event is None:
                    # if not, add the time window and jump to the next event
                    window_start = current_event['end']
                    # go to first event after end of current event
                    current_event = get_following_event(event=current_event, event_data=events)
                    window_end = current_event['start']
                    # if next event is on next day, set window until feierabend or jump to next day
                    if window_end.date() - window_start.date() > dt.timedelta(0):
                        if window_start.time() < feierabend:
                            window_end = self.get_local_datetime(window_start.date(), feierabend)
                        else:
                            continue
                    # Add only time windows larger than 15 minutes
                    window_width = window_end - window_start
                    if window_width > pd.Timedelta(minutes=15):
                        if window_width < remaining_duration:
                            time_windows = time_windows.append(
                                {'start': window_start, 'end': window_end}, ignore_index=True)
                            remaining_duration -= window_width
                        else:
                            time_windows = time_windows.append(
                                {'start': window_start, 'end': window_start + remaining_duration}, ignore_index=True)
                            remaining_duration -= remaining_duration
                            break

                else:
                    current_event = consecutive_event
            start_timestamp = end_timestamp

        # create events for all time windows
        for _, row in time_windows.iterrows():
            self.create_event(start=row['start'], end=row['end'], summary=target_event_summary,
                              color_id=target_event_color_id, calendar_id=target_calendar_id, **optional_fields)

    def local_datetime_from_string(self, datetime_string):
        return pd.Timestamp(datetime_string).tz_convert(self.timezone)

    def get_local_datetime(self, day, time):
        return pd.Timestamp(dt.datetime.combine(day, time), tzinfo=self.timezone)

    def create_event(self, start: pd.Timestamp, end: pd.Timestamp, summary: str, calendar_id: str = 'primary',
                     color_id: int = None, **optional_fields):
        body = {
            'start': {'dateTime': start.isoformat()},
            'end': {'dateTime': end.isoformat()},
            'summary': summary,
            **optional_fields,
        }
        if color_id is not None:
            body['colorId'] = color_id
        self.insert_event(body, calendar_id)

    def insert_event(self, body, calendar_id):
        self.service.events().insert(calendarId=calendar_id, body=body).execute()

    def delete_event(self, calendar_id, event_id):
        self.service.events().delete(calendarId=calendar_id, eventId=event_id, ).execute()

    def extract_local_datetime_or_nat(self, dict_in):
        if 'dateTime' in dict_in.keys():
            return self.local_datetime_from_string(dict_in['dateTime'])
        else:
            return pd.NaT

    def update_event(self, body, calendar_id):
        self.service.events().update(
            calendarId=calendar_id,
            eventId=body['id'],
            body=body,
        ).execute()
