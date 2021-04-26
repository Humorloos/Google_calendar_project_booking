import datetime as dt
import pandas as pd
from dateutil.relativedelta import relativedelta

from utils import get_google_calendar_service, get_local_datetime, local_datetime_from_string
from calendar import monthrange

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
START_DATE = dt.date.today().replace(day=1)

if __name__ == '__main__':
    service = get_google_calendar_service(SCOPES)
    work_calendar_id = next(item['id'] for item in service.calendarList().list().execute()['items'] if
                            item['summary'] == 'Arbeit')
    start_datetime = get_local_datetime(START_DATE, dt.time(0))
    events = service.events().list(
        calendarId=work_calendar_id,
        timeMin=start_datetime.isoformat(),
        singleEvents=True,
        orderBy='startTime',
        timeMax=(start_datetime + relativedelta(months=1)).isoformat()
    ).execute()['items']
    event_data = pd.DataFrame(columns=['summary', 'start', 'end'])
    for event in events:
        if 'dateTime' in event['start'].keys():
            event_data = event_data.append({
                'summary': event['summary'],
                'start': local_datetime_from_string(event['start']['dateTime']),
                'end': local_datetime_from_string(event['end']['dateTime'])
            }, ignore_index=True)
    current_date = START_DATE
    out = pd.DataFrame(columns=['datum', 'von', 'bis', 'pause'])
    while current_date < START_DATE + relativedelta(months=1):
        current_date_event_data = event_data[
            (event_data['start'] >= get_local_datetime(current_date, dt.time(0))) &
            (event_data['end'] < get_local_datetime(current_date + pd.Timedelta(days=1), dt.time(0)))
            ]
        current_date += pd.Timedelta(days=1)
        if current_date_event_data.empty:
            continue
        current_event = current_date_event_data.loc[current_date_event_data['start'].idxmin()]
        datum = current_event['start'].strftime('%d.%m.%Y')
        von = current_event['start'].strftime("%H:%M")
        pause = pd.Timedelta(0)
        while True:
            try:
                # check if there is an adjacent/overlapping event (within 15 minutes)
                current_event = current_date_event_data.loc[current_date_event_data[
                    (current_date_event_data['start'] < current_event['end'] + pd.Timedelta(minutes=15)) &
                    (current_date_event_data['end'] > current_event['end'])
                    ]['end'].idxmax()]
            except ValueError:
                # if not, add the time window and jump to the next event
                # ceil to 15 minutes to handle odd meeting times
                # (see https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases)
                window_start = current_event['end'].ceil('15min')
                try:
                    # go to first event after end of current event
                    current_event = current_date_event_data.loc[current_date_event_data[
                        current_date_event_data['start'] - current_event['end'] > pd.Timedelta(0)
                        ]['start'].idxmin()]
                except ValueError:
                    bis = current_event['end'].strftime("%H:%M")
                    break
                pause += current_event['start'] - window_start
        out = out.append({'datum': datum, 'von': von, 'bis': bis, 'pause': pause.seconds // 60}, ignore_index=True)
    out.to_csv('target/Zeiterfassung.csv', index=False)
