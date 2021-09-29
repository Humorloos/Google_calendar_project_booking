from pathlib import Path
import pandas as pd

RESOURCES_PATH = Path(__file__).parent.joinpath('resources')
CALENDAR_LOOKUP_PATH = RESOURCES_PATH.joinpath('calendar_lookup.csv')

GOOGLE_API_PATH = RESOURCES_PATH.joinpath('google_api')
TOKEN_PATH = GOOGLE_API_PATH.joinpath('token.json')
CREDENTIALS_PATH = GOOGLE_API_PATH.joinpath('credentials.json')
PROJECT_ARGUMENT = '-p'


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
    """
    Gets earliest starting event starting after given event from given event_data.
    """
    following_event_start_times = event_data[event_data['start'] - event['end'] > pd.Timedelta(0)]['start']
    if len(following_event_start_times) > 0:
        return event_data.loc[following_event_start_times.idxmin()]
    else:
        return None


def get_calendar_lookup():
    print(f'Reading calendar lookup table from {CALENDAR_LOOKUP_PATH.absolute()}')
    return pd.read_csv(CALENDAR_LOOKUP_PATH, index_col='channel_id')


def event_row_to_body(updated_event):
    return updated_event[~updated_event.isnull()].to_dict()
