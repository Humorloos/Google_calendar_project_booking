from pathlib import Path

import pandas as pd

RESOURCES_PATH = Path(__file__).parent.joinpath('resources')
CALENDAR_LOOKUP_PATH = RESOURCES_PATH.joinpath('calendar_lookup.csv')

GOOGLE_API_PATH = RESOURCES_PATH.joinpath('google_api')
TOKEN_PATH = GOOGLE_API_PATH.joinpath('token.json')
CREDENTIALS_PATH = GOOGLE_API_PATH.joinpath('credentials.json')
PROJECT_SUFFIX = ' -p'


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


def get_calendar_lookup():
    print(f'Reading calendar lookup table from {CALENDAR_LOOKUP_PATH.absolute()}')
    return pd.read_csv(CALENDAR_LOOKUP_PATH, index_col='channel_id')


def event_row_to_body(updated_event):
    return updated_event[~updated_event.isnull()].to_dict()
