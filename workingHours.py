import datetime as dt

import pandas as pd
from dateutil.relativedelta import relativedelta

import googleApiScopes.calendar
from calendarUtils import get_consecutive_event, get_following_event
from googleApiClientProvider import GoogleApiClientProvider
from utils import GOOGLE_API_PATH

SCOPES = [googleApiScopes.calendar.CALENDAR_READ_ONLY]
START_DATE = dt.date(year=2021, month=9, day=1)

if __name__ == '__main__':
    calendar_service = GoogleApiClientProvider(SCOPES, GOOGLE_API_PATH).get_calendar_service()
    start_datetime = calendar_service.get_local_datetime(START_DATE, dt.time(0))
    events = calendar_service.get_event_df_and_next_sync_token(
        calendar_id=calendar_service.calendar_dict['Arbeit'],
        time_min=start_datetime.isoformat(),
        time_max=(start_datetime + relativedelta(months=1)).isoformat(),
    )[0]
    events[['start', 'end']] = events[['start', 'end']].applymap(calendar_service.extract_local_datetime_or_nat)
    events['date'] = events['start'].apply(lambda start: start.date())
    events_by_date = events.sort_values(by='start').groupby(by='date')


    def get_working_hours(event_df):
        current_event = event_df.iloc[0]
        datum = current_event['start'].strftime('%d.%m.%Y')
        von = current_event['start'].strftime("%H:%M")
        pause = pd.Timedelta(0)
        while True:
            # check if there is an adjacent/overlapping event (within 15 minutes)
            consecutive_event = get_consecutive_event(event=current_event, event_data=event_df, precision=15)
            if consecutive_event is not None:
                current_event = consecutive_event
            else:
                # if not, add the time window and jump to the next event
                # ceil to 15 minutes to handle odd meeting times
                # (see https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases)
                window_start = current_event['end'].ceil('15min')
                # go to first event after end of current event
                following_event = get_following_event(event=current_event, event_data=event_df)
                if following_event is None:
                    # if no more events are left this day, go to next day
                    bis = current_event['end'].strftime("%H:%M")
                    break
                current_event = following_event
                pause += current_event['start'] - window_start
        return pd.Series({'datum': datum, 'von': von, 'bis': bis, 'pause': pause.seconds // 60})


    events_by_date.apply(get_working_hours).to_csv('target/Zeiterfassung.csv', index=False)
