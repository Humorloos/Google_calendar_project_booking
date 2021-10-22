import pandas as pd

from googleCalendarApp.constants import CALENDAR_LOOKUP_PATH


def get_calendar_lookup():
    print(f'Reading calendar lookup table from {CALENDAR_LOOKUP_PATH.absolute()}')
    return pd.read_csv(CALENDAR_LOOKUP_PATH, index_col='channel_id')


def event_row_to_body(updated_event):
    return updated_event[~updated_event.isnull()].to_dict()
