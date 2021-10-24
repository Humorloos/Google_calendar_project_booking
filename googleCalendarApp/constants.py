from pathlib import Path

MODULE_DIR = Path(__file__).parent.parent
PROJECT_DIR = MODULE_DIR.parent
RESOURCES_PATH = MODULE_DIR.joinpath('resources')
CALENDAR_LOOKUP_PATH = RESOURCES_PATH.joinpath('calendar_lookup.csv')
GOOGLE_API_PATH = RESOURCES_PATH.joinpath('google_api')

PROJECT_ARGUMENT = '-p'
CALENDAR_URI = 'calendar'
