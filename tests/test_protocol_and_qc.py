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
from src.data_ingest import parse_full_date,normalize_season_date,read_yield
from src.build_master import weighted_average,normal_yield_subset
from src.phenology_validation import baseline_predict,metrics
from src.weather_features import weather_window
from src.validation_contracts import loyo_indices


def test_no_raw_mutation(context):
    assert_inputs_unchanged(*context)


def test_cross_year_dates():
    a,_,flag=parse_full_date('2021-09-25',CALENDAR_WINDOWS_1900)
    b,_,_=parse_full_date('2022-01-20',CALENDAR_WINDOWS_1900)
    assert flag=='ok' and (b-a).days==117
    assert pd.isna(parse_full_date('9月25日',CALENDAR_WINDOWS_1900)[0])


def test_a39_matches_latest_user_confirmed_2026(context):
    wb=openpyxl.load_workbook(context[0]/'测产.xlsx',data_only=True)
    actual=wb['Sheet1']['A39'].value
    wb.close()
    assert actual==context[1]['constraints']['a39_expected']==2026


def test_authorized_cross_year_normalization(context):
    events=pd.read_csv(context[0]/'data/processed/phenology_event_long.csv').set_index('source_cell')
    assert events.loc['E2','event_date']=='2021-09-25'
    assert events.loc['F2','event_date']=='2021-12-25'
    assert events.loc['G2','event_date']=='2022-01-20'
    assert events.loc['E14','event_date']=='2025-09-25'
    assert events.loc['G14','event_date']=='2026-01-10'
    assert events.loc['E2','harvest_year_source_cell']=='A2'
    dates=events[events.event_date.notna()]
    assert len(dates)==147 and dates.date_year_rebased.sum()==123
    normalized=pd.to_datetime(dates.event_date)
    decoded=pd.to_datetime(dates.decoded_candidate_date)
    assert normalized.dt.strftime('%m-%d').equals(decoded.dt.strftime('%m-%d'))
    expected=dates.harvest_year-(normalized.dt.month>=7).astype(int)
    assert normalized.dt.year.eq(expected).all()


def test_no_silent_invalid_leap_day_repair(context):
    parsed,_,flag,_=normalize_season_date('2024-02-29',CALENDAR_WINDOWS_1900,2023,'full_bloom',context[1]['constraints'])
    assert pd.isna(parsed) and flag=='invalid_rebased_calendar_date'


def test_overlapping_population_stages_not_shifted_to_force_order(context):
    events=pd.read_csv(context[0]/'data/processed/phenology_event_long.csv')
    case=events[(events.orchard_id=='bannei')&(events.harvest_year==2022)].set_index('event_name')
    assert case.loc['end_bloom','event_date']=='2022-03-15'
    assert case.loc['fruit_drop_1','event_date']=='2022-03-10'
    assert case.loc['end_bloom','qc_flag']==case.loc['fruit_drop_1','qc_flag']=='ok'


def test_month_day_text_uses_explicit_user_authority(context):
    parsed,_,flag,_=normalize_season_date('9月25日',CALENDAR_WINDOWS_1900,2022,'autumn_flush_mature',context[1]['constraints'])
    assert parsed==pd.Timestamp('2021-09-25') and flag=='ok'
    without_authority=dict(context[1]['constraints'],seasonal_year_normalization=False)
    assert pd.isna(normalize_season_date('9月25日',CALENDAR_WINDOWS_1900,2022,'autumn_flush_mature',without_authority)[0])


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


@pytest.mark.parametrize('model_id',['P1-B0','P1-B1'])
def test_baseline_fit_uses_training_only_and_ignores_test_target(model_id):
    train=pd.DataFrame({'orchard_id':['bannei']*2,'harvest_year':[2022,2023],
                        'season_id':['bannei_2022','bannei_2023'],'observed_duration_days':[117,118],
                        'observed_end_date':['2022-01-20','2023-01-21']})
    test=pd.DataFrame({'orchard_id':['bannei'],'harvest_year':[2024],'season_id':['bannei_2024'],
                      'observed_start_date':['2023-09-25'],'observed_end_date':['2024-01-25'],
                      'observed_duration_days':[122]})
    prediction=baseline_predict(train,test,model_id)
    mutated=test.assign(observed_end_date='2040-12-31',observed_duration_days=10000)
    pd.testing.assert_frame_equal(prediction,baseline_predict(train,mutated,model_id))
    assert prediction.iloc[0].predicted_event_date==pd.Timestamp('2024-01-21')
    assert prediction.iloc[0].n_fit_samples==2
    assert prediction.iloc[0].training_years=='2022;2023'
    fallback=baseline_predict(train,test.assign(orchard_id='new_orchard'),model_id)
    assert fallback.iloc[0].fit_scope=='pooled_training_fallback'
    assert fallback.iloc[0].predicted_event_date==prediction.iloc[0].predicted_event_date


@pytest.mark.skip(reason='Weather gate: no fitted weather-driven phenology model or W3 windows exist.')
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


@pytest.mark.skip(reason='Weather gate: no validated weather model or scenario implementation; not a verified scenario.')
def test_scenario_does_not_refit_model():
    pass


def test_reproducibility(context):
    root,_=context
    outputs=[root/x for x in ['data/processed/phenology_event_long.csv','data/processed/yield_observation_long.csv',
                              'data/processed/weather_daily.csv','data/processed/orchard_season_master.csv',
                              'results/qc/analysis_gate.json','reports/00_DATA_FEASIBILITY_REPORT.md',
                              'results/phenology/P1_cv_predictions.csv']]
    before={str(p):sha256(p) for p in outputs}
    completed=subprocess.run([sys.executable,'-m','src.cli','all','--config','configs/base.yaml'],cwd=root,capture_output=True)
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


def test_user_confirmation_resolves_year_conflict(master):
    assert master.year_protocol_conflict.eq(0).all()
    current=master[master.harvest_year==2026]
    assert len(current)==3
    assert set(current[current.yield_main_eligible==1].orchard_id)=={'bannei','luhong'}


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


def test_gate_allows_calendar_baselines_but_prevents_weather_models(context):
    gate=json.loads((context[0]/'results/qc/analysis_gate.json').read_text(encoding='utf-8'))
    assert gate['overall_status']=='partial' and gate['dates_ready'] and not gate['yield']['formal_prediction_allowed']
    assert all(p['baseline_allowed'] and not p['weather_models_allowed'] for p in gate['phenology'].values())
    statuses=pd.read_csv(context[0]/'results/qc/experiment_status.csv')
    baselines={'P1-B0','P1-B1','P2-B0','P3-B0','PHENO-TYPHOON-SENSITIVITY'}
    assert statuses[statuses.experiment_id.isin(baselines)].status.eq('executed').all()
    assert statuses[statuses.experiment_id.str.startswith(('P1-M','P2-M','P3-M','Y-','S1','S2','S3','S4'))].status.eq('blocked').all()


def test_real_loyo_folds_hold_out_entire_year(context):
    for task in ['P1','P2','P3']:
        rows=pd.read_csv(context[0]/f'results/phenology/{task}_cv_predictions.csv')
        assert rows.groupby('model_id').size().eq(12).all()
        for row in rows.itertuples():
            assert row.harvest_year==row.holdout_year
            assert str(row.holdout_year) not in row.training_years.split(';')
            assert row.season_id not in row.all_training_season_ids.split(';')
            assert all(not key.endswith('_'+str(row.holdout_year)) for key in row.all_training_season_ids.split(';'))
        for model,group in rows.groupby('model_id'):
            reported=pd.read_csv(context[0]/f'results/phenology/{task}_model_comparison.csv').set_index('model_id')
            assert reported.loc[model,'MAE_days']==pytest.approx(metrics(group)['MAE_days'])
        assert rows.prediction_interval_lower.isna().all()


def test_weather_gaps_follow_corrected_start_not_october_first(context):
    rows=pd.read_csv(context[0]/'results/qc/transition_review.csv')
    row=rows[(rows.season_id=='bannei_2022')&(rows.task=='P1')].iloc[0]
    assert row.observed_start_date=='2021-09-25' and row.observed_end_date=='2022-01-20'
    assert row.observed_duration_days==117 and row.expected_days==118
    assert row.missing_tmean_days==6 and row.model_eligible==0
    assert rows.groupby('task').main_complete_date_pair.sum().eq(12).all()
    assert rows.model_eligible.sum()==0


def test_w2_boundaries_not_confused_with_complete_weather(context):
    rows=pd.read_csv(context[0]/'results/windows/observed_dynamic_features.csv')
    assert len(rows)==75 and rows.boundaries_valid.sum()==66
    assert not rows.feature_status.eq('complete').any()


def test_typhoon_baseline_sensitivity_not_main_sample(context):
    main=pd.read_csv(context[0]/'results/phenology/P1_cv_predictions.csv')
    alt=pd.read_csv(context[0]/'results/phenology/typhoon_sensitivity_cv_predictions.csv')
    assert 'bannei_2025' not in set(main.season_id)
    assert set(alt[alt.season_id=='bannei_2025'].task)=={'P1'}
