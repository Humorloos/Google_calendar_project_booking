from pathlib import Path
import pandas as pd

RESOURCES_PATH = Path(__file__).parent.joinpath('resources')
CALENDAR_LOOKUP_PATH = RESOURCES_PATH.joinpath('calendar_lookup.csv')

GOOGLE_API_PATH = RESOURCES_PATH.joinpath('google_api')
PROJECT_ARGUMENT = '-p'


def get_calendar_lookup():
    print(f'Reading calendar lookup table from {CALENDAR_LOOKUP_PATH.absolute()}')
    return pd.read_csv(CALENDAR_LOOKUP_PATH, index_col='channel_id')


def event_row_to_body(updated_event):
    return updated_event[~updated_event.isnull()].to_dict()
