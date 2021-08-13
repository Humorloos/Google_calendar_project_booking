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
    try:
        return event_data.loc[event_data[
            (event_data['start'] <= event['end'].ceil(f'{precision}min')) & (event_data['end'] > event['end'])
            ]['end'].idxmax()]
    except ValueError:
        return None


def get_following_event(event, event_data):
    return event_data.loc[event_data[event_data['start'] - event['end'] > pd.Timedelta(0)]['start'].idxmin()]


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
