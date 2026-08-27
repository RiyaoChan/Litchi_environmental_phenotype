from __future__ import annotations

import numpy as np
import pandas as pd

from .data_ingest import TRANSITIONS
from .build_master import normal_yield_subset
from .weather_features import weather_window


def transition_audit(events, master, weather, cfg):
    rows = []
    for (orchard,year,block),g in events.groupby(['orchard_id','harvest_year','source_block_id'],sort=True):
        season = master[master.season_id == f'{orchard}_{year}'].iloc[0]
        by_event = g.set_index('event_name')
        for task,(start_name,end_name) in TRANSITIONS.items():
            start,end = by_event.loc[start_name],by_event.loc[end_name]
            candidate_complete = pd.notna(start.decoded_candidate_date) and pd.notna(end.decoded_candidate_date)
            duration_candidate = (end.decoded_candidate_date-start.decoded_candidate_date).days if candidate_complete else np.nan
            complete = pd.notna(start.event_date) and pd.notna(end.event_date) and end.event_date>start.event_date
            date_coverage, temperature_coverage, precip_coverage = np.nan,np.nan,np.nan
            expected_days, observed_days, missing_temperature_days = np.nan,np.nan,np.nan
            if complete:
                data = weather_window(weather,season.station_id,start.event_date,end.event_date)
                n = (end.event_date-start.event_date).days+1
                date_coverage = len(data)/n
                temperature_coverage = int(data.tmean_c.notna().sum())/n
                precip_coverage = int(data.precip_mm.notna().sum())/n
                expected_days, observed_days = n,len(data)
                missing_temperature_days = n-int(data.tmean_c.notna().sum())
            flags = []
            if not complete:
                flags.append('complete_dates_not_validated')
            if pd.notna(start.event_date) and pd.notna(end.event_date) and end.event_date<=start.event_date:
                flags.append('normalized_end_not_after_start')
            if complete and temperature_coverage < cfg['gates']['required_weather_coverage']:
                flags.append('incomplete_stage_weather')
            if season.typhoon_damage==1:
                flags.append('typhoon_main_excluded')
            if season.damage_review_reason:
                flags.append('other_damage_review')
            rows.append({'season_id':season.season_id,'orchard_id':orchard,'station_id':season.station_id,'harvest_year':int(year),
                         'source_block_id':block,'task':task,'start_event':start_name,'end_event':end_name,
                         'start_source_cell':start.source_cell,'end_source_cell':end.source_cell,
                         'observed_start_date':start.event_date,'observed_end_date':end.event_date,
                         'candidate_start_date':start.decoded_candidate_date,'candidate_end_date':end.decoded_candidate_date,
                         'candidate_duration_days_AUDIT_ONLY':duration_candidate,
                         'observed_duration_days':(end.event_date-start.event_date).days if complete else np.nan,
                         'raw_endpoint_pair_present':int(candidate_complete or complete),'complete_date_pair':int(complete),
                         'main_complete_date_pair':int(complete and season.phenology_main_eligible==1),
                         'sensitivity_complete_date_pair':int(complete and (season.phenology_main_eligible==1 or season.phenology_sensitivity_eligible==1)),
                         'weather_coverage_ratio':date_coverage,'tmean_coverage_ratio':temperature_coverage,
                         'precip_coverage_ratio':precip_coverage,'expected_days':expected_days,
                         'observed_weather_days':observed_days,'missing_tmean_days':missing_temperature_days,
                         'model_eligible':int(complete and season.phenology_main_eligible==1 and temperature_coverage>=cfg['gates']['required_weather_coverage']),
                         'qc_flag':';'.join(flags) or 'ok'})
    return pd.DataFrame(rows)


def overlap_audit(events):
    rows = []
    # These population stages may overlap. Only annotate; never rewrite or exclude for overlap alone.
    for (orchard,year),g in events.groupby(['orchard_id','harvest_year']):
        e=g.set_index('event_name')
        for a,b in [('end_bloom','initial_fruit_set'),('full_bloom','fruit_drop_1'),('end_bloom','fruit_drop_1')]:
            da,db=e.loc[a,'event_date'],e.loc[b,'event_date']
            if pd.notna(da) and pd.notna(db) and db<=da:
                rows.append({'orchard_id':orchard,'harvest_year':int(year),'first_event':a,'second_event':b,
                             'first_event_date':da,'second_event_date':db,'action':'audit_only_no_date_change',
                             'note':'Population stages may overlap; user-authorized seasonal years applied.'})
    return pd.DataFrame(rows)


def analysis_gate(events, yields, master, blocks, transitions, coverage, fixed, a39, cfg, dynamic):
    invalid_nonmissing = ~events.qc_flag.isin(['ok','missing','qualitative_not_date'])
    bad_sequence = transitions.qc_flag.str.contains('normalized_end_not_after_start').any()
    dates_ready = not invalid_nonmissing.any() and events.event_date.notna().any() and not bad_sequence
    normal=normal_yield_subset(master)
    tasks={}
    for task in TRANSITIONS:
        g=transitions[transitions.task==task]
        n=int(g.model_eligible.sum())
        tasks[task]={'raw_endpoint_pairs':int(g.raw_endpoint_pair_present.sum()),
                     'validated_date_pairs':int(g.complete_date_pair.sum()),
                     'main_complete_pairs':int(g.main_complete_date_pair.sum()),
                     'weather_complete_model_samples':n,
                     'baseline_allowed':bool(dates_ready and g.main_complete_date_pair.sum()>0),
                     'weather_models_allowed':bool(dates_ready and n>=cfg['gates']['simple_phenology_min_n']),
                     'status':'blocked_dates' if not dates_ready else ('baseline_only' if n<cfg['gates']['simple_phenology_min_n'] else 'weather_model_implementation_pending'),
                     'reason':'Stop 1: normalized dates/sequence unresolved' if not dates_ready else ('insufficient_complete_daily_weather' if n<cfg['gates']['simple_phenology_min_n'] else 'weather_model_gate_passed')}
    reasons=[]
    if not dates_ready: reasons.append('Stop 1: full phenology dates not validated')
    if a39['conflict']: reasons.append('A39 differs from current user-confirmed expected year')
    if len(normal)<cfg['gates']['yield_min_n']: reasons.append('insufficient conservative normal orchard-season records')
    if normal.harvest_year.nunique()<cfg['gates']['yield_min_years']: reasons.append('insufficient eligible harvest years')
    if blocks.blocks_in_same_season.gt(1).any(): reasons.append('unresolved repeated blocks')
    if not fixed.feature_status.eq('complete').all(): reasons.append('W1 contains missing daily weather')
    if not dynamic.feature_status.eq('complete').all(): reasons.append('W2 stage weather incomplete even where event boundaries are available')
    return {
        'overall_status':'blocked' if not dates_ready else 'partial',
        'has_blocked_experiments':True,
        'stop_rule':'Stop 1' if not dates_ready else 'weather_coverage_gate',
        'raw_mutation':False,'dates_ready':bool(dates_ready),'a39':a39,
        'counts':{'phenology_orchard_seasons':int(events[['orchard_id','harvest_year']].drop_duplicates().shape[0]),
                  'phenology_event_slots':len(events),'validated_event_dates':int(events.event_date.notna().sum()),
                  'unformatted_excel_serials':int(events.qc_flag.str.contains('unformatted_excel_serial').sum()),
                  'dates_year_rebased':int(events.date_year_rebased.sum()),
                  'yield_class_rows':len(yields),'yield_source_blocks':len(blocks),'yield_orchard_seasons':len(master),
                  'raw_nonzero_yield_seasons':int(master.raw_final_yield_kg_per_mu.gt(0).sum()),
                  'normal_yield_eligible_seasons_before_weather_gate':len(normal),
                  'normal_eligible_years':sorted(map(int,normal.harvest_year.unique())),
                  'protocol_disaster_seasons':int(master.typhoon_damage.eq(1).sum()),
                  'other_damage_review_seasons':int(master.damage_review_reason.ne('').sum())},
        'phenology':tasks,
        'yield':{'status':'blocked','formal_prediction_allowed':False,'reasons':reasons,
                 'note':'A39 and seasonal dates resolved. Yield features still lack continuous daily weather.'},
        'windows':{'W1':'coverage audit only; incomplete stages not summarized as complete',
                   'W2':'observed date boundaries and coverage audit; stage weather incomplete',
                   'W3':'blocked: no weather-driven phenology model and incomplete weather features'},
        'dynamic_window_counts':{'total':len(dynamic),'valid_date_boundaries':int(dynamic.boundaries_valid.sum()),
                                  'complete_weather_features':int(dynamic.feature_status.eq('complete').sum())},
        'typhoon':{'orchard_id':'bannei','harvest_year':2025,'final_yield_kg_per_mu':0,
                   'phenology_main_eligible':False,'phenology_sensitivity_eligible':True,
                   'typhoon_event_date':None,'abandon_production_decision_date':'2025-03-01',
                   'normal_model_baseline_available':False,
                   'reason':'Annual report documents weak/damaged shoots during floral induction; exact typhoon date unconfirmed. Decision date is NOT typhoon event date.'},
        'scenarios':{'S1':'blocked_no_validated_P1','S2':'blocked_no_validated_P1',
                     'S3':'blocked_no_validated_moisture_model','S4':'blocked_no_validated_yield_model'},
        'implemented_scope':'seasonal_date_normalization_stage0_LOYO_calendar_baselines_W2_coverage',
        'downstream_model_implementation':'weather_driven_models_deferred_until_continuous_weather_available',
    }
