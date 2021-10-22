from pathlib import Path

RESOURCES_PATH = Path(__file__).parent.joinpath('resources')
CALENDAR_LOOKUP_PATH = RESOURCES_PATH.joinpath('calendar_lookup.csv')
GOOGLE_API_PATH = RESOURCES_PATH.joinpath('google_api')

PROJECT_ARGUMENT = '-p'
