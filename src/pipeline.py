from __future__ import annotations

import importlib.metadata
import json
import platform
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd
import yaml

from .io_utils import assert_inputs_unchanged, inventory, prepare_dirs, write_csv, write_json
from .data_ingest import read_phenology, read_yield, read_weather, read_document_evidence, number
from .weather_features import clean_weather, coverage_tables
from .build_master import build_master
from .data_qc import transition_audit, overlap_audit, analysis_gate
from .reporting import write_reports
from .dynamic_windows import observed_dynamic_features, transition_weather_gaps


def source_matches(yields, doc_cells):
    rows=[]
    docs=doc_cells[doc_cells.source_file.str.startswith('示范园/')]
    grouped=list(docs.groupby(['source_file','table_index','row'],sort=True))
    for block,g in yields.groupby('source_block_id',sort=True):
        first=g.iloc[0]
        signature=[first[f'sample_tree_{i}_yield_kg'] for i in (1,2,3)]
        if not np.isfinite(signature).all(): continue
        for (file,table,row),cells in grouped:
            values=[number(text) for text in cells.text]
            if all(any(np.isfinite(n) and abs(n-v)<1e-8 for n in values) for v in signature):
                rows.append({'source_block_id':block,'excel_row':int(first.source_row),'excel_harvest_year':int(first.harvest_year),
                             'word_source_file':file,'word_table':int(table),'word_row':int(row),
                             'word_report_year_from_filename':int(re.search(r'/(\d{4})',file).group(1)),
                             'matched_tree_yields_kg':';'.join(map(str,signature)),
                             'interpretation':'numeric_evidence_only_no_year_override'})
    return pd.DataFrame(rows,columns=['source_block_id','excel_row','excel_harvest_year','word_source_file','word_table','word_row','word_report_year_from_filename','matched_tree_yields_kg','interpretation'])


def experiment_status(gate,baselines_run=False):
    executed=[('QC-0','standardization_and_data_gate'),('DESC-Y','raw_yield_description'),
              ('DESC-W','weather_coverage_description'),('W1-QC','fixed_window_coverage_audit'),
              ('W2-QC','normalized_observed_stage_boundaries_and_weather_coverage'),
              ('TYPHOON-DESC','source_evidence_and_zero_vs_NA_coding')]
    baseline_ids=['P1-B0','P1-B1','P2-B0','P3-B0','PHENO-TYPHOON-SENSITIVITY']
    baseline_rows=[{'experiment_id':k,'status':'executed' if baselines_run else 'pending' if gate['dates_ready'] else 'blocked',
                    'reason':'weather_independent_LOYO_baselines_only' if gate['dates_ready'] else 'date_gate'} for k in baseline_ids]
    blocked=['P1-B2','P1-M1','P1-M2','P1-M3','P1-M4',
             'P2-M1','P2-M2','P3-M1','P3-M2','P1-white-tip',
             'W3','Y-B0','Y-B1','Y-W1','Y-W2','Y-W3','Y-W3P','Y-PREV','Y-DEC',
             'TYPHOON-BASELINE','TYPHOON-INCLUSION','S1','S2','S3','S4']
    return pd.DataFrame([{'experiment_id':k,'status':'executed','reason':r} for k,r in executed]+
                        baseline_rows+[{'experiment_id':'W2','status':'partial','reason':'date_windows_available_but_stage_weather_incomplete'}]+
                        [{'experiment_id':k,'status':'blocked','reason':'continuous_stage_weather_unavailable_or_required_weather_model_not_validated'} for k in blocked])


def run(root: Path,cfg: dict,all_stages=False):
    prepare_dirs(root)
    assert_inputs_unchanged(root,cfg)
    np.random.seed(cfg['seed'])
    events=read_phenology(root,cfg)
    yields,a39=read_yield(root,cfg)
    raw_weather,weather_mapping,rejected=read_weather(root,cfg)
    weather,weather_issues,duplicates=clean_weather(raw_weather,cfg)
    documents,evidence,doc_cells=read_document_evidence(root,cfg)
    master,blocks=build_master(yields,events,cfg)
    window_cfg=yaml.safe_load((root/cfg['weather_windows_config']).read_text(encoding='utf-8'))
    coverage,gaps,fixed=coverage_tables(weather,master,cfg,window_cfg)
    master['weather_coverage_ratio']=master.season_id.map(coverage.set_index('season_id').date_coverage_ratio)
    master['weather_coverage_window']='previous_Oct01_to_harvest_Jun30_inclusive'
    transitions=transition_audit(events,master,weather,cfg)
    dynamic=observed_dynamic_features(events,master,weather,window_cfg)
    gate=analysis_gate(events,yields,master,blocks,transitions,coverage,fixed,a39,cfg,dynamic)
    predictions,comparison=None,None
    status=experiment_status(gate,False)
    matches=source_matches(yields,doc_cells)
    tables={
        'data/processed/phenology_event_long.csv':events,
        'data/processed/yield_observation_long.csv':yields,
        'data/processed/orchard_season_master.csv':master,
        'data/processed/weather_daily.csv':weather,
        'data/interim/weather_observation_long.csv':raw_weather,
        'data/interim/yield_block_summary.csv':blocks,
        'data/metadata/weather_column_mapping.csv':weather_mapping,
        'results/inventory/raw_file_inventory.csv':pd.DataFrame(inventory(root,cfg)),
        'results/qc/phenology_date_review.csv':events[events.qc_flag!='ok'],
        'results/qc/phenology_date_normalization.csv':events[events.event_date.notna()],
        'results/qc/source_block_review.csv':blocks,
        'results/qc/transition_review.csv':transitions,
        'results/qc/phenology_overlap_review.csv':overlap_audit(events),
        'results/qc/weather_value_review.csv':weather_issues,
        'results/qc/weather_duplicate_review.csv':duplicates,
        'results/qc/weather_rejected_rows.csv':rejected,
        'results/qc/weather_coverage_by_orchard_season.csv':coverage,
        'results/qc/weather_gap_ranges.csv':gaps,
        'results/qc/weather_missing_by_transition.csv':transition_weather_gaps(transitions,weather),
        'results/qc/yield_class_mean_review.csv':yields[yields.class_mean_mismatch==1],
        'results/qc/annual_source_numeric_matches.csv':matches,
        'results/qc/experiment_status.csv':status,
        'results/descriptive/phenology_duration.csv':transitions,
        'results/descriptive/weather_by_stage.csv':dynamic,
        'results/descriptive/yield_summary.csv':master,
        'results/windows/fixed_window_features.csv':fixed,
        'results/windows/observed_dynamic_features.csv':dynamic,
        'results/windows/window_comparison.csv':pd.DataFrame([
            {'window_type':k,'status':v,'performance_comparison_available':False} for k,v in gate['windows'].items()]),
    }
    # Explicitly distinguish a missing result from a numeric zero.
    case=pd.DataFrame([{'orchard_id':'bannei','harvest_year':2025,'observed_yield':0,
                        'normal_production_baseline_prediction':np.nan,'prediction_interval_lower':np.nan,
                        'prediction_interval_upper':np.nan,'absolute_gap':np.nan,
                        'relative_gap_to_prediction':np.nan,'status':'blocked_no_normal_model',
                        'typhoon_event_date':None,'abandon_production_decision_date':'2025-03-01'}])
    tables['results/typhoon_case/bannei_2025_case.csv']=case
    for path,df in tables.items(): write_csv(root/path,df)
    write_json(root/'results/qc/analysis_gate.json',gate)
    write_json(root/'results/qc/protocol_conflicts.json',{'A39':a39,'raw_file_changed_by_pipeline':False,
        'resolution_authority':cfg['constraints']['user_amendment'],'seasonal_year_authority':'Excel column A',
        'previous_A39_and_date_year_blocks_resolved':not a39['conflict'] and gate['dates_ready']})
    write_json(root/'results/logs/environment.json',{'python_version':platform.python_version(),
        'python_executable':sys.executable,'platform':platform.platform(),'seed':cfg['seed'],
        'packages':{p:importlib.metadata.version(p) for p in ['numpy','pandas','openpyxl','PyYAML','pytest','matplotlib']}})
    schema=[]
    units={'event_date':'YYYY-MM-DD; validated only','decoded_candidate_date':'AUDIT ONLY; not analysis-ready',
           'date':'YYYY-MM-DD','final_yield_kg_per_mu':'kg/mu','mean_yield_per_tree_kg':'kg/tree',
           'mean_single_fruit_weight_g':'g/fruit','fruit_number_proxy':'estimated fruits/tree; not actual count',
           'tmean_c':'degC','tmin_c':'degC','tmax_c':'degC','precip_mm':'mm',
           'sunshine_h':'hours/day','relative_humidity_pct':'percent','wind_speed':'not available',
           'source_block_id':'immutable source block, not independent environmental sample',
           'station_id':'internal regional source alias, not verified official station number'}
    for file in [x for x in tables if x.startswith('data/processed/')]:
        for col in tables[file]:
            schema.append({'table':file,'field':col,'unit_or_definition':units.get(col,'see source locator / report'),
                           'missing_representation':'NA; never replace missing measurement with 0'})
    write_csv(root/'data/metadata/data_dictionary.csv',schema)
    if all_stages and gate['dates_ready']:
        from .phenology_validation import run_baselines
        predictions,comparison=run_baselines(root,transitions,gate,cfg)
        status=experiment_status(gate,True)
        write_csv(root/'results/qc/experiment_status.csv',status)
    write_reports(root,gate,events,master,coverage,fixed,weather_issues,evidence,transitions,status,matches,
                  dynamic=dynamic,comparison=comparison)
    if all_stages:
        from .plots import create_descriptive_figures
        create_descriptive_figures(root,events,master,weather,transitions,cfg,predictions=predictions)
    assert_inputs_unchanged(root,cfg)
    print(json.dumps({'status':gate['overall_status'],'stage':'allowed_stages_completed' if all_stages else 'stage0_completed',
                      'counts':gate['counts'],'phenology':gate['phenology'],
                      'report':'reports/FINAL_EXPERIMENT_REPORT.md'},ensure_ascii=False,indent=2))
    return 2 if gate.get('has_blocked_experiments',False) else 0
