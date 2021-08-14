import datetime as dt
from pathlib import Path

import pandas as pd
from tzlocal import get_localzone

CALENDAR_LOOKUP_PATH = Path('resources').joinpath('calendar_lookup.csv')
PROJECT_SUFFIX = ' -p'


def get_local_datetime(day, time):
    return pd.Timestamp(dt.datetime.combine(day, time), tzinfo=get_localzone())


def local_datetime_from_string(datetime_string):
    return pd.Timestamp(datetime_string).tz_convert(get_localzone())


def get_consecutive_event(event, event_data, precision=0):
    """
    Gets consecutive or overlapping event that ends at the latest point if there is any, otherwise returns None
    """
    overlapping_or_consecutive_events = event_data[
        (event_data['start'] <= event['end'].ceil(f'{precision}min')) &
        (event_data['end'] > event['end'])
        ]
    if len(overlapping_or_consecutive_events) > 0:
        return event_data.loc[overlapping_or_consecutive_events['end'].idxmax()]
    else:
        return None


def get_following_event(event, event_data):
    return event_data.loc[
        event_data[
            event_data['start'] - event['end'] > pd.Timedelta(0)
            ]['start'].idxmin()
    ]


# noinspection PyPep8Naming
class cached_property(object):
    """
    property for caching of attributes, code adapted from
    https://stackoverflow.com/questions/17330160/how-does-the-property-decorator-work
    """

    def __init__(self, fget, fset=None, fdel=None, name=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.__name__ = name or fget.__name__
        self.__module__ = fget.__module__
        self.__doc__ = doc or fget.__doc__

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        try:
            return obj.__dict__[self.__name__]
        except KeyError:
            value = self.fget(obj)
            obj.__dict__[self.__name__] = value
            return value

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")
        self.fset(obj, value)

    def __delete__(self, obj):
        try:
            del obj.__dict__[self.__name__]
        except KeyError:
            pass
        if self.fdel is not None:
            self.fdel(obj)

    def setter(self, fset):
        return type(self)(self.fget, fset, self.fdel, self.__name__, self.__doc__)

    def deleter(self, fdel):
        return type(self)(self.fget, self.fset, fdel, self.__name__, self.__doc__)


def get_calendar_ids(calendar_service):
    return [item['id'] for item in calendar_service.calendarList().list().execute()['items'] if
            item['accessRole'] == 'owner' and not item['summary'] == 'Scheduler']


def calendar_id_from_summary(calendar_service, summary):
    return next(
        item for item in calendar_service.calendarList().list().execute()['items'] if item['summary'] == summary
    )['id']


def get_calendar_lookup():
    return pd.read_csv(CALENDAR_LOOKUP_PATH, index_col='channel_id')


def extract_local_datetime_or_nat(dict_in):
    if 'dateTime' in dict_in.keys():
        return local_datetime_from_string(dict_in['dateTime'])
    else:
        return pd.NaT


def create_event(service, start, end, summary, description='', calendar_id='primary', color_id=None):
    body = {
        'start': {
            'dateTime': start.isoformat()
        },
        'end': {
            'dateTime': end.isoformat()
        },
        'summary': summary,
        'description': description,
    }
    if color_id is not None:
        body['colorId'] = color_id
    service.events().insert(calendarId=calendar_id, body=body).execute()


def create_events_in_windows(calendar_ids, calendar_service, start_timestamp, duration,
                             target_event_summary, target_event_description, target_calendar_id, feierabend,
                             target_event_color_id=None):
    time_windows = pd.DataFrame(columns=['start', 'end'])
    remaining_duration = duration
    first_week = True
    while remaining_duration > pd.Timedelta(0):
        # get all events for one week
        end_timestamp = start_timestamp + dt.timedelta(weeks=1)  #get_local_datetime(current_day, FEIERABEND)
        start_rfc_3339_timestamp = start_timestamp.isoformat()
        end_rfc_3339_timestamp = end_timestamp.isoformat()
        events = pd.DataFrame([
            event for calendar_id in calendar_ids for event in calendar_service.events().list(
                calendarId=calendar_id,
                timeMax=end_rfc_3339_timestamp,
                timeMin=start_rfc_3339_timestamp,
                singleEvents=True,
            ).execute()['items']
            if 'dateTime' in event['start'].keys()
        ])
        events[['start', 'end']] = events[['start', 'end']].apply(lambda col: col.apply(extract_local_datetime_or_nat))
        events = events.sort_values(by='start', ignore_index=True)

        # # get all tasks for the current day
        # tasks = [task for tasklist_id in tasklist_ids for task in items_or_empty_list(tasks_service.tasks().list(
        #     tasklist=tasklist_id,
        #     dueMin=start_rfc_3339_timestamp,
        #     dueMax=end_rfc_3339_timestamp,
        # ).execute())]
        if first_week:
            current_event = events.loc[0]
        # find all time windows for the current day
        while True:
            if current_event.name == events.index.max():
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
                        window_end = get_local_datetime(window_start.date(), feierabend)
                    else:
                        continue
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
        start_timestamp = end_timestamp

    # create events for all time windows
    for _, row in time_windows.iterrows():
        create_event(service=calendar_service, start=row['start'], end=row['end'],
                     summary=target_event_summary, description=target_event_description, color_id=target_event_color_id,
                     calendar_id=target_calendar_id)


def get_event_df_and_next_sync_token(calendar_service, calendar_id, sync_token=None, query=None, time_max=None,
                                     time_min=None):
    events, sync_token = get_events_and_next_sync_token(
        calendar_id, calendar_service, query, sync_token, time_max, time_min)
    return pd.DataFrame(events), sync_token


def get_events_and_next_sync_token(calendar_id, calendar_service, query, sync_token, time_max, time_min):
    updated_events_list_response = calendar_service.events().list(
        calendarId=calendar_id,
        syncToken=sync_token,
        maxResults=2500,
        singleEvents=True,
        q=query,
        # latest time that events may start
        timeMax=time_max,
        # earliest time that events may end
        timeMin=time_min,
    ).execute()
    events = updated_events_list_response['items']
    while 'nextSyncToken' not in updated_events_list_response.keys():
        updated_events_list_response = calendar_service.events().list(
            calendarId=calendar_id,
            syncToken=sync_token,
            maxResults=2500,
            singleEvents=True,
            q=query,
            # latest time that events may start
            timeMax=time_max,
            # earliest time that events may end
            timeMin=time_min,
            pageToken=updated_events_list_response['nextPageToken'],
        ).execute()
        events.extend(updated_events_list_response['items'])
    sync_token = updated_events_list_response['nextSyncToken']
    return events, sync_token


def event_row_to_body(updated_event):
    return updated_event[~updated_event.isnull()].to_dict()
