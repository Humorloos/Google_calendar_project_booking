from __future__ import print_function

import datetime as dt

import pandas as pd

# If modifying these scopes, delete the file token.json.
from utils import get_google_calendar_service, get_local_datetime, local_datetime_from_string, get_consecutive_event, \
    get_following_event

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/calendar.events']

# Day at which to start creating events
START_DAY = dt.date.today()
# Time after which not to create any more events
FEIERABEND = dt.time(20)
# Estimated duration of the project to book
PROJECT_DURATION = pd.Timedelta(hours=14)
# Name of calendar to create events in
TARGET_CALENDAR_NAME = 'Privat'
# color id for events to create, see https://lukeboyle.com/blog-posts/2016/04/google-calendar-api---color-id
COLOR_ID = 7
# Summary for the events to create for the project
PROJECT_SUMMARY = 'IE 672 Prüfungsvorbereitung'
# Description for the events to create for the project
PROJECT_DESCRIPTION = """<div><table>

 <colgroup><col>
 <col>
 <col>
 </colgroup><tbody><tr>
  <td>Topic</td>
  <td>skim-time</td>
  <td>Exercise time</td>
 </tr>
 <tr>
  <td>DM01-DataPreprocessing-V1.pdf</td>
  <td>01:15:00</td>
  <td>1.5</td>
 </tr>
 <tr>
  <td>DM03-AnomalyDetection-V1.pdf</td>
  <td>01:30:00</td>
  <td>2</td>
 </tr>
 <tr>
  <td>DM04-Ensembles.pdf&nbsp;</td>
  <td>01:15:00</td>
  <td>2</td>
 </tr>
 <tr>
  <td>DM05-TimeSeries-V1.pdf</td>
  <td>01:15:00</td>
  <td>1</td>
 </tr>
 <tr>
  <td>DM06-NeuraINetsAndDeepLearning_V…</td>
  <td>00:30:00</td>
  <td>0.5</td>
 </tr>
 <tr>
  <td>&nbsp;DM07-Parameter-Tuning-V1.pdf</td>
  <td>01:15:00</td>
  <td>1</td>
 </tr>
 <tr>
  <td>DM08-Validation-V1.pdf</td>
  <td>00:15:00</td>
  <td>1.5</td>
 </tr>
 <tr>
  <td></td>
  <td></td>
  <td></td>
 </tr>
 <tr>
  <td></td>
  <td>04:30:00</td>
  <td>9.5</td>
 </tr>

</tbody></table></div>"""


def main():
    service = get_google_calendar_service(SCOPES)
    remaining_duration = PROJECT_DURATION
    calendar_ids = [item['id'] for item in service.calendarList().list().execute()['items'] if
                    item['accessRole'] == 'owner' and not item['summary'] == 'Scheduler']
    current_day = START_DAY
    while remaining_duration > pd.Timedelta(0):
        # get all events for the current day
        events = []
        end_datetime = get_local_datetime(current_day, FEIERABEND)
        for calendar_id in calendar_ids:
            events.extend(service.events().list(
                calendarId=calendar_id,
                timeMin=get_local_datetime(current_day, dt.time(0)).isoformat(),
                singleEvents=True,
                orderBy='startTime',
                timeMax=end_datetime.isoformat()
            ).execute()['items'])

        # Remove 'All Day' events
        events = [event for event in events if 'dateTime' in event['start'].keys()]

        event_data = pd.DataFrame({
            'start': [local_datetime_from_string(event['start']['dateTime']) for event in events],
            'end': [local_datetime_from_string(event['end']['dateTime']) for event in events]
        })
        event_data = event_data.append({'start': end_datetime, 'end': pd.NaT}, ignore_index=True)
        time_windows = pd.DataFrame(columns=['start', 'end'])
        current_event = event_data.loc[event_data['start'].idxmin()]
        # find all time windows for the current day
        while pd.notnull(current_event['end']) and current_event['end'] < end_datetime:
            try:
                # check if there is an adjacent/overlapping event
                current_event = get_consecutive_event(event=current_event, event_data=event_data)
            except ValueError:
                # if not, add the time window and jump to the next event
                window_start = current_event['end']
                # go to first event after end of current event
                current_event = get_following_event(event=current_event, event_data=event_data)
                window_end = current_event['start']
                # Add only time windows larger than 15 minutes
                if window_end - window_start > pd.Timedelta(minutes=15):
                    time_windows = time_windows.append({'start': window_start, 'end': window_end}, ignore_index=True)

        target_calendar_id = next(item['id'] for item in service.calendarList().list().execute()['items'] if
                                  item['accessRole'] == 'owner' and item['summary'] == TARGET_CALENDAR_NAME)

        # create events for all time windows
        for _, row in time_windows.iterrows():
            window_width = row['end'] - row['start']
            if remaining_duration > window_width:
                create_event(service=service, start=row['start'], end=row['end'], summary=PROJECT_SUMMARY,
                             description=PROJECT_DESCRIPTION, colorId=COLOR_ID, calendar_id=target_calendar_id)
                remaining_duration -= window_width
            else:
                create_event(service=service, start=row['start'], end=row['start'] + remaining_duration,
                             summary=PROJECT_SUMMARY, description=PROJECT_DESCRIPTION, colorId=COLOR_ID,
                             calendar_id=target_calendar_id)
                remaining_duration -= remaining_duration
                break
        current_day += pd.Timedelta(days=1)


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


if __name__ == '__main__':
    main()
