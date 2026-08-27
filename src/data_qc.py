from __future__ import annotations

import numpy as np
import pandas as pd

from .data_ingest import TRANSITIONS
from .build_master import normal_yield_subset
from .weather_features import weather_window


def transition_audit(events, master, weather):
    rows = []
    for (orchard,year,block),g in events.groupby(['orchard_id','harvest_year','source_block_id'],sort=True):
        season = master[master.season_id == f'{orchard}_{year}'].iloc[0]
        by_event = g.set_index('event_name')
        for task,(start_name,end_name) in TRANSITIONS.items():
            start,end = by_event.loc[start_name],by_event.loc[end_name]
            candidate_complete = pd.notna(start.decoded_candidate_date) and pd.notna(end.decoded_candidate_date)
            duration_candidate = (end.decoded_candidate_date-start.decoded_candidate_date).days if candidate_complete else np.nan
            complete = pd.notna(start.event_date) and pd.notna(end.event_date) and end.event_date>start.event_date
            date_coverage, temperature_coverage = np.nan,np.nan
            if complete:
                data = weather_window(weather,season.station_id,start.event_date,end.event_date)
                n = (end.event_date-start.event_date).days+1
                date_coverage = len(data)/n
                temperature_coverage = int(data.tmean_c.notna().sum())/n
            flags = []
            if not complete:
                flags.append('complete_dates_not_validated')
            if candidate_complete and duration_candidate<=0:
                flags.append('candidate_end_not_after_start')
            if candidate_complete and not (start.decoded_candidate_date.year in (year-1,year) and end.decoded_candidate_date.year in (year-1,year)):
                flags.append('candidate_year_conflict')
            if season.typhoon_damage==1:
                flags.append('typhoon_main_excluded')
            if season.damage_review_reason:
                flags.append('other_damage_review')
            rows.append({'season_id':season.season_id,'orchard_id':orchard,'harvest_year':int(year),
                         'source_block_id':block,'task':task,'start_event':start_name,'end_event':end_name,
                         'start_source_cell':start.source_cell,'end_source_cell':end.source_cell,
                         'observed_start_date':start.event_date,'observed_end_date':end.event_date,
                         'candidate_start_date':start.decoded_candidate_date,'candidate_end_date':end.decoded_candidate_date,
                         'candidate_duration_days_AUDIT_ONLY':duration_candidate,
                         'observed_duration_days':(end.event_date-start.event_date).days if complete else np.nan,
                         'raw_endpoint_pair_present':int(candidate_complete),'complete_date_pair':int(complete),
                         'main_complete_date_pair':int(complete and season.phenology_main_eligible==1),
                         'weather_coverage_ratio':date_coverage,'tmean_coverage_ratio':temperature_coverage,
                         'model_eligible':int(complete and season.phenology_main_eligible==1 and temperature_coverage==1.0),
                         'qc_flag':';'.join(flags) or 'ok'})
    return pd.DataFrame(rows)


def overlap_audit(events):
    rows = []
    # These population stages may overlap. Only annotate; never rewrite or exclude for overlap alone.
    for (orchard,year),g in events.groupby(['orchard_id','harvest_year']):
        e=g.set_index('event_name')
        for a,b in [('end_bloom','initial_fruit_set'),('full_bloom','fruit_drop_1'),('end_bloom','fruit_drop_1')]:
            da,db=e.loc[a,'decoded_candidate_date'],e.loc[b,'decoded_candidate_date']
            if pd.notna(da) and pd.notna(db) and db<=da:
                rows.append({'orchard_id':orchard,'harvest_year':int(year),'first_event':a,'second_event':b,
                             'candidate_first_date':da,'candidate_second_date':db,'action':'audit_only_no_date_change',
                             'note':'Population stages may overlap; candidate years remain unvalidated.'})
    return pd.DataFrame(rows)


def analysis_gate(events, yields, master, blocks, transitions, coverage, fixed, a39):
    invalid_nonmissing = ~events.qc_flag.isin(['ok','missing','qualitative_not_date'])
    bad_sequence = transitions.qc_flag.str.contains('candidate_end_not_after_start|candidate_year_conflict').any()
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
                     'status':'blocked' if not dates_ready else ('baseline_only' if n<8 else 'simple' if n<12 else 'nonlinear_allowed'),
                     'reason':'Stop 1: date encoding/year/sequence unresolved' if not dates_ready else 'sample-size gate'}
    reasons=[]
    if not dates_ready: reasons.append('Stop 1: full phenology dates not validated')
    if a39['conflict']: reasons.append('A39 expected 2025 but actual source is 2026; user confirmation required')
    if len(normal)<10: reasons.append('fewer than 10 conservative normal orchard-season records')
    if normal.harvest_year.nunique()<4: reasons.append('fewer than 4 eligible harvest years')
    if blocks.blocks_in_same_season.gt(1).any(): reasons.append('unresolved repeated blocks')
    if not fixed.feature_status.eq('complete').all(): reasons.append('W1 contains missing daily weather')
    if not transitions.complete_date_pair.all(): reasons.append('W2 unavailable: event dates not validated/absent')
    return {
        'overall_status':'blocked',
        'stop_rule':'Stop 1' if not dates_ready else 'downstream_implementation_deferred_until_new_input_review',
        'raw_mutation':False,'dates_ready':bool(dates_ready),'a39':a39,
        'counts':{'phenology_orchard_seasons':int(events[['orchard_id','harvest_year']].drop_duplicates().shape[0]),
                  'phenology_event_slots':len(events),'validated_event_dates':int(events.event_date.notna().sum()),
                  'unformatted_excel_serials':int(events.qc_flag.str.contains('unformatted_excel_serial').sum()),
                  'yield_class_rows':len(yields),'yield_source_blocks':len(blocks),'yield_orchard_seasons':len(master),
                  'raw_nonzero_yield_seasons':int(master.raw_final_yield_kg_per_mu.gt(0).sum()),
                  'normal_yield_eligible_seasons_before_weather_gate':len(normal),
                  'normal_eligible_years':sorted(map(int,normal.harvest_year.unique())),
                  'protocol_disaster_seasons':int(master.typhoon_damage.eq(1).sum()),
                  'other_damage_review_seasons':int(master.damage_review_reason.ne('').sum())},
        'phenology':tasks,
        'yield':{'status':'blocked','formal_prediction_allowed':False,'reasons':reasons,
                 'note':'No regression is run while Stop 1 and chronology conflicts remain.'},
        'windows':{'W1':'coverage audit only; incomplete stages not summarized as complete',
                   'W2':'blocked: unvalidated dates','W3':'blocked: no valid LOYO phenology predictions'},
        'typhoon':{'orchard_id':'bannei','harvest_year':2025,'final_yield_kg_per_mu':0,
                   'phenology_main_eligible':False,'phenology_sensitivity_eligible':True,
                   'typhoon_event_date':None,'abandon_production_decision_date':'2025-03-01',
                   'normal_model_baseline_available':False,
                   'reason':'Annual report documents weak/damaged shoots during floral induction; exact typhoon date unconfirmed. Decision date is NOT typhoon event date.'},
        'scenarios':{'S1':'blocked_no_validated_P1','S2':'blocked_no_validated_P1',
                     'S3':'blocked_no_validated_moisture_model','S4':'blocked_no_validated_yield_model'},
        'implemented_scope':'stage0_audit_plus_nonmodel_descriptive_outputs',
        'downstream_model_implementation':'deferred_after_Stop1_resolution; no fitted models or simulated metrics',
    }
