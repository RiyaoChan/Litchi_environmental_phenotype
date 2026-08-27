from __future__ import annotations

from datetime import datetime
import json
import subprocess
import sys

import numpy as np
import openpyxl
import pandas as pd
import pytest
from openpyxl.utils.datetime import CALENDAR_WINDOWS_1900

from src.io_utils import assert_inputs_unchanged,sha256
from src.data_ingest import parse_full_date,read_yield
from src.build_master import weighted_average,normal_yield_subset
from src.weather_features import weather_window
from src.validation_contracts import loyo_indices


def test_no_raw_mutation(context):
    assert_inputs_unchanged(*context)


def test_cross_year_dates():
    a,_,flag=parse_full_date('2021-09-25',CALENDAR_WINDOWS_1900)
    b,_,_=parse_full_date('2022-01-20',CALENDAR_WINDOWS_1900)
    assert flag=='ok' and (b-a).days==117
    assert pd.isna(parse_full_date('9月25日',CALENDAR_WINDOWS_1900)[0])


def test_a39_remains_2025(context):
    wb=openpyxl.load_workbook(context[0]/'测产.xlsx',data_only=True)
    actual=wb['Sheet1']['A39'].value
    wb.close()
    if actual!=2025:
        pytest.xfail(f'Unmet source invariant: protocol A39=2025, actual={actual}. Raw source preserved; modeling blocked.')
    assert actual==2025


def test_source_blocks_preserved(context):
    rows,_=read_yield(*context)
    output=pd.read_csv(context[0]/'data/processed/yield_observation_long.csv')
    assert len(rows)==len(output)==45
    assert set(rows.source_block_id)==set(output.source_block_id)
    assert rows.groupby('source_block_id').size().eq(3).all()


def test_group_split_by_year(context):
    rows,_=read_yield(*context)
    for year,train,test in loyo_indices(rows.harvest_year):
        assert set(rows.iloc[train].harvest_year).isdisjoint(rows.iloc[test].harvest_year)
        assert rows.iloc[test].harvest_year.eq(year).all()


def test_no_tree_level_leakage(context):
    rows,_=read_yield(*context)
    for _,train,test in loyo_indices(rows.harvest_year):
        assert set(rows.iloc[train].source_block_id).isdisjoint(rows.iloc[test].source_block_id)


@pytest.mark.skip(reason='Stop 1: no model/preprocessing pipeline has been implemented or fitted.')
def test_train_only_preprocessing():
    pass


@pytest.mark.skip(reason='Stop 1: no fitted phenology models or cross-fitted W3 windows exist.')
def test_cross_fitted_windows():
    pass


def test_typhoon_yield_is_zero(master):
    case=master[master.season_id=='bannei_2025'].iloc[0]
    assert case.final_yield_kg_per_mu==0
    assert case.normal_production_year==0 and case.typhoon_damage==1


def test_typhoon_components_are_missing(master):
    case=master[master.season_id=='bannei_2025'].iloc[0]
    assert case[['mean_yield_per_tree_kg','mean_single_fruit_weight_g','fruit_number_proxy','observed_fruit_number']].isna().all()


def test_typhoon_excluded_from_normal_yield_fit(master):
    assert 'bannei_2025' not in set(normal_yield_subset(master).season_id)


def test_typhoon_phenology_eligibility_rule(master):
    case=master[master.season_id=='bannei_2025'].iloc[0]
    assert case.phenology_main_eligible==0
    assert case.phenology_sensitivity_eligible==1
    assert pd.isna(case.typhoon_event_date)
    assert case.abandon_production_decision_date=='2025-03-01'


def test_weather_window_boundaries():
    w=pd.DataFrame({'station_id':['s']*4,'date':pd.date_range('2021-12-30',periods=4)})
    assert len(weather_window(w,'s','2021-12-31','2022-01-01'))==2
    with pytest.raises(ValueError): weather_window(w,'s','2022-01-01','2021-12-31')


def test_weighted_aggregation():
    assert weighted_average([10,20],[1,3])==17.5
    assert np.isnan(weighted_average([10,np.nan],[1,3]))
    assert weighted_average([10,np.nan],[1,0])==10


@pytest.mark.skip(reason='Stop 1: no validated model or scenario implementation; no claim of scenario verification.')
def test_scenario_does_not_refit_model():
    pass


def test_reproducibility(context):
    root,_=context
    outputs=[root/x for x in ['data/processed/phenology_event_long.csv','data/processed/yield_observation_long.csv',
                              'data/processed/weather_daily.csv','data/processed/orchard_season_master.csv',
                              'results/qc/analysis_gate.json','reports/00_DATA_FEASIBILITY_REPORT.md']]
    before={str(p):sha256(p) for p in outputs}
    completed=subprocess.run([sys.executable,'-m','src.cli','stage0','--config','configs/base.yaml'],cwd=root,capture_output=True)
    assert completed.returncode==2,completed.stderr.decode(errors='replace')
    assert before=={str(p):sha256(p) for p in outputs}


def test_untyped_serials_are_audit_only():
    parsed,candidate,flag=parse_full_date(46290,CALENDAR_WINDOWS_1900)
    assert pd.isna(parsed) and candidate==pd.Timestamp('2026-09-25')
    assert 'requires_confirmation' in flag


def test_weather_mapping_tracks_header_changes(context):
    w=pd.read_csv(context[0]/'data/interim/weather_observation_long.csv')
    row=w[(w.station_id=='lingshui_region_proxy')&(w.date=='2026-01-01')].iloc[0]
    assert row.sunshine_h==7.5 and row.relative_humidity_pct==76
    row=w[(w.station_id=='lingshui_region_proxy')&(w.date=='2021-10-01')].iloc[0]
    assert row.sunshine_h==9.8 and row.relative_humidity_pct==87


def test_temperature_conflicts_not_swapped(context):
    w=pd.read_csv(context[0]/'data/processed/weather_daily.csv')
    row=w[(w.station_id=='lingshui_region_proxy')&(w.date=='2023-01-01')].iloc[0]
    assert row[['tmin_c','tmean_c','tmax_c']].isna().all()
    assert float(row.tmax_c_raw)==17.8 and float(row.tmin_c_raw)==19.3


def test_incomplete_weather_never_fabricated(context):
    w=pd.read_csv(context[0]/'results/windows/fixed_window_features.csv')
    flowering=w[w.window_name=='flowering']
    assert flowering.tmean_c_mean.isna().all() and flowering.precip_mm_sum.isna().all()


def test_missing_positive_count_class_prevents_full_mean(master):
    row=master[master.season_id=='hongming_2026'].iloc[0]
    assert row.weighted_mean_tree_coverage_ratio==.9
    assert pd.isna(row.mean_yield_per_tree_kg)


def test_damage_review_excluded_from_normal_candidates(master):
    assert {'hongming_2025','hongming_2026'}.isdisjoint(set(normal_yield_subset(master).season_id))


def test_protocol_conflict_blocks_without_editing_year(master):
    rows=master[master.year_protocol_conflict==1]
    assert len(rows)==3 and rows.harvest_year.eq(2026).all()
    assert rows.yield_main_eligible.eq(0).all()


def test_class_mean_discrepancy_preserved(context):
    rows=pd.read_csv(context[0]/'data/processed/yield_observation_long.csv')
    r=rows[rows.source_row==12].iloc[0]
    assert r.reported_class_mean_yield_kg==50.88 and r.class_mean_mismatch==1


def test_diseased_pest_rate_not_mislabeled(context):
    rows=pd.read_csv(context[0]/'data/processed/yield_observation_long.csv')
    assert 'diseased_pest_fruit_pct' in rows and 'drop_rate_pct' not in rows


def test_document_duplicate_detected(context):
    docs=pd.read_csv(context[0]/'results/inventory/document_inventory.csv')
    assert len(docs)==7 and docs.sha256.nunique()==6


def test_gate_prevents_all_model_fitting(context):
    gate=json.loads((context[0]/'results/qc/analysis_gate.json').read_text(encoding='utf-8'))
    assert gate['overall_status']=='blocked' and not gate['yield']['formal_prediction_allowed']
    statuses=pd.read_csv(context[0]/'results/qc/experiment_status.csv')
    assert statuses[statuses.experiment_id.str.startswith(('P1','P2','P3','Y-','S1','S2','S3','S4'))].status.eq('blocked').all()
