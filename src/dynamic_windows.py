"""Observed stage windows and exact missing-day ranges; no weather imputation."""
import numpy as np
import pandas as pd

from .data_ingest import WEATHER_VARIABLES
from .weather_features import weather_window


def observed_dynamic_features(events,master,weather,windows):
    records=[]
    for season in master.itertuples():
        e=events[(events.orchard_id==season.orchard_id)&(events.harvest_year==season.harvest_year)].set_index('event_name')
        for name,(start_name,end_name) in windows['dynamic'].items():
            start,end=e.loc[start_name,'event_date'],e.loc[end_name,'event_date']
            valid=pd.notna(start) and pd.notna(end) and end>=start
            r={'season_id':season.season_id,'orchard_id':season.orchard_id,'harvest_year':season.harvest_year,
               'station_id':season.station_id,'window_name':name,'start_event':start_name,'end_event':end_name,
               'window_start':start,'window_end':end,'boundaries_valid':int(valid),
               'expected_days':np.nan,'observed_days':np.nan,'date_coverage_ratio':np.nan,
               'feature_status':'blocked_missing_or_reversed_dates'}
            for var in WEATHER_VARIABLES:
                r[var+'_coverage_ratio']=np.nan
                r[var+'_mean']=np.nan
            r['precip_mm_sum']=np.nan
            if valid:
                block=weather_window(weather,season.station_id,start,end)
                n=(end-start).days+1
                r.update(expected_days=n,observed_days=len(block),date_coverage_ratio=len(block)/n)
                for var in WEATHER_VARIABLES:
                    r[var+'_coverage_ratio']=int(block[var].notna().sum())/n
                    if len(block)==n and block[var].notna().all():
                        r[var+'_mean']=float(block[var].mean())
                        if var=='precip_mm': r['precip_mm_sum']=float(block[var].sum())
                r['feature_status']='complete' if r['tmean_c_coverage_ratio']==r['precip_mm_coverage_ratio']==1 else 'blocked_missing_weather'
            records.append(r)
    return pd.DataFrame(records)


def transition_weather_gaps(transitions,weather):
    records=[]
    for row in transitions[transitions.complete_date_pair==1].itertuples():
        station=row.station_id
        expected=pd.date_range(row.observed_start_date,row.observed_end_date)
        block=weather_window(weather,station,row.observed_start_date,row.observed_end_date)
        for variable in ['tmean_c','precip_mm']:
            missing=expected.difference(block.loc[block[variable].notna(),'date'])
            series=pd.Series(missing)
            for _,run in series.groupby(series.diff().ne(pd.Timedelta(days=1)).cumsum()):
                records.append({'season_id':row.season_id,'orchard_id':row.orchard_id,'harvest_year':row.harvest_year,
                                'station_id':station,'task':row.task,'variable':variable,
                                'missing_start':run.min(),'missing_end':run.max(),'missing_days':len(run),
                                'main_analysis_eligible':row.main_complete_date_pair})
    return pd.DataFrame(records)
