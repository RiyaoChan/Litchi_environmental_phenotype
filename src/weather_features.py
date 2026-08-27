"""Weather QC and coverage only. Never interpolate or relabel temperatures."""
from __future__ import annotations

import json
import numpy as np
import pandas as pd

from .data_ingest import WEATHER_VARIABLES
from .io_utils import season_bound


def clean_weather(raw, cfg):
    df = raw.copy(deep=True)
    issues = []
    for idx, row in df.iterrows():
        flags = []
        lo, hi = cfg['qc']['temperature_bounds_c']
        temps = ['tmin_c', 'tmean_c', 'tmax_c']
        for var in temps:
            if pd.notna(row[var]) and not lo <= row[var] <= hi:
                flags.append(f'{var}_out_of_range')
                df.loc[idx, var] = np.nan
        if all(pd.notna(row[v]) for v in temps) and not row.tmin_c <= row.tmean_c <= row.tmax_c:
            flags.append('temperature_order_inconsistent')
            df.loc[idx, temps] = np.nan
        for var, bounds in [('relative_humidity_pct',cfg['qc']['relative_humidity_bounds_pct']), ('sunshine_h',cfg['qc']['sunshine_bounds_h'])]:
            if pd.notna(row[var]) and not bounds[0] <= row[var] <= bounds[1]:
                flags.append(f'{var}_out_of_range')
                df.loc[idx,var] = np.nan
        if pd.notna(row.precip_mm) and row.precip_mm < 0:
            flags.append('negative_precipitation')
            df.loc[idx,'precip_mm'] = np.nan
        df.loc[idx,'qc_flag'] = ';'.join(flags) or 'ok'
        if flags:
            issues.append({k:row[k] for k in ['station_id','date','source_file','source_sheet','source_row',*WEATHER_VARIABLES]} | {'qc_flag':';'.join(flags)})
    unique = []
    duplicates = []
    for (_, _), group in df.groupby(['station_id','date'], sort=True):
        rec = group.iloc[0].to_dict()
        rec['n_source_rows'] = len(group)
        rec['source_references'] = json.dumps(group[['source_file','source_sheet','source_row']].to_dict('records'), ensure_ascii=False)
        if len(group) > 1:
            conflicting = []
            for var in WEATHER_VARIABLES:
                # Different observed values, or a missing-vs-measured discrepancy, require review.
                if group[var].nunique(dropna=False) > 1:
                    rec[var] = np.nan
                    conflicting.append(var)
            rec['qc_flag'] += ';duplicate_date_' + ('conflicting' if conflicting else 'identical')
            duplicates.append({'station_id':rec['station_id'], 'date':rec['date'], 'n_source_rows':len(group), 'conflicting_variables':';'.join(conflicting)})
        unique.append(rec)
    return pd.DataFrame(unique), pd.DataFrame(issues,columns=['station_id','date','source_file','source_sheet','source_row',*WEATHER_VARIABLES,'qc_flag']), pd.DataFrame(duplicates,columns=['station_id','date','n_source_rows','conflicting_variables'])


def weather_window(weather, station, start, end):
    """Both endpoints inclusive; reversed bounds are rejected, not swapped."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if end < start:
        raise ValueError('weather window end precedes start')
    return weather[(weather.station_id == station) & weather.date.between(start,end)].copy()


def coverage_tables(weather, seasons, cfg, windows):
    coverage, gaps, fixed = [], [], []
    for s in seasons.itertuples():
        start = season_bound(cfg['coverage']['start'],s.harvest_year)
        end = season_bound(cfg['coverage']['end'],s.harvest_year)
        expected = pd.date_range(start,end)
        observed = weather_window(weather,s.station_id,start,end)
        rec = {'season_id':s.season_id,'orchard_id':s.orchard_id,'region_id':s.region_id,
               'station_id':s.station_id,'harvest_year':s.harvest_year,
               'window_start':start,'window_end':end,'expected_days':len(expected),
               'observed_days':len(observed),'date_coverage_ratio':len(observed)/len(expected)}
        for var in WEATHER_VARIABLES:
            rec[var + '_coverage_ratio'] = int(observed[var].notna().sum()) / len(expected)
        coverage.append(rec)
        missing_days = expected.difference(observed.date)
        if len(missing_days):
            runs = pd.Series(missing_days).groupby(pd.Series(missing_days).diff().ne(pd.Timedelta(days=1)).cumsum())
            for _, run in runs:
                gaps.append({'season_id':s.season_id,'station_id':s.station_id,'missing_start':run.min(),'missing_end':run.max(),'n_days':len(run)})
        for window_name, bounds in windows['fixed'].items():
            a,b = season_bound(bounds['start'],s.harvest_year),season_bound(bounds['end'],s.harvest_year)
            block = weather_window(weather,s.station_id,a,b)
            n = (b-a).days+1
            item = {'season_id':s.season_id,'orchard_id':s.orchard_id,'harvest_year':s.harvest_year,
                    'station_id':s.station_id,'window_name':window_name,'window_start':a,'window_end':b,
                    'expected_days':n,'observed_days':len(block),'date_coverage_ratio':len(block)/n}
            for var in WEATHER_VARIABLES:
                complete = len(block)==n and block[var].notna().all()
                item[var+'_coverage_ratio'] = int(block[var].notna().sum())/n
                # No sum/mean of an incomplete window is passed off as the whole window.
                item[var+'_mean'] = float(block[var].mean()) if complete else np.nan
                if var == 'precip_mm':
                    item['precip_mm_sum'] = float(block[var].sum()) if complete else np.nan
            item['feature_status'] = 'complete' if (len(block)==n and block[['tmean_c','precip_mm']].notna().all().all()) else 'blocked_missing_weather'
            fixed.append(item)
    return pd.DataFrame(coverage),pd.DataFrame(gaps),pd.DataFrame(fixed)
