import json
import numpy as np
import pandas as pd
import pytest
from src.io_utils import load_config
from src.r4_weather_loader import settings,read_weather,master_table,task_frame
from src.phenology_models import WeatherStore,fit_candidate
from src.scenario_simulation import perturb_air_temperature,simulate_fixed_fit


@pytest.fixture(scope='module')
def scenario_data(context):
    root,cfg=load_config(context[0]/'configs/r4_experiment_v3.yaml')
    d,h,_=read_weather(root,cfg); models=settings(root,cfg,'phenology')
    weather=WeatherStore(d,h,models)
    frame=task_frame(master_table(root,cfg),'P2')
    fit=fit_candidate(frame[frame.harvest_year!=2024],{'model_id':'P2-M1','kind':'gdd','temperature':10},weather,models)
    return weather,frame[frame.harvest_year==2024],fit


def test_scenario_does_not_refit_model(scenario_data,monkeypatch):
    weather,samples,fit=scenario_data
    original=json.dumps(fit,sort_keys=True)
    import src.phenology_models as model_module
    def forbidden(*args,**kwargs): raise AssertionError('Scenario attempted model refit')
    monkeypatch.setattr(model_module,'fit_candidate',forbidden)
    _=simulate_fixed_fit(fit,samples,weather,delta=1)
    assert json.dumps(fit,sort_keys=True)==original


def test_warming_perturbation_applies_only_to_temperature(scenario_data):
    weather,_,_=scenario_data
    changed=perturb_air_temperature(weather,1)
    for orchard in weather.daily:
        d=weather.daily[orchard]; h=weather.hourly[orchard]
        pd.testing.assert_frame_equal(d.drop(columns=['tmean_c','tmin_c','tmax_c']),changed.daily[orchard].drop(columns=['tmean_c','tmin_c','tmax_c']))
        pd.testing.assert_frame_equal(h.drop(columns=['temperature_c']),changed.hourly[orchard].drop(columns=['temperature_c']))
        assert np.allclose(changed.daily[orchard].tmean_c-d.tmean_c,1)
        assert np.allclose(changed.daily[orchard].tmin_c-d.tmin_c,1)
        assert np.allclose(changed.daily[orchard].tmax_c-d.tmax_c,1)


def test_flush_delay_changes_start_date_not_weather_history(scenario_data):
    weather,samples,fit=scenario_data
    before={o:w.copy(deep=True) for o,w in weather.daily.items()}
    starts=samples.start_date.copy()
    _=simulate_fixed_fit(fit,samples,weather,delay_days=7)
    pd.testing.assert_series_equal(samples.start_date,starts)
    for orchard in before: pd.testing.assert_frame_equal(before[orchard],weather.daily[orchard])


def test_saved_scenarios_obey_stage_gates_and_use_original_loyo_models(context):
    base=context[0]/'results/r4'
    status=pd.read_csv(base/'scenarios/scenario_status.csv').set_index('experiment_id')
    assert status.loc['S4-P2','status']=='executed'
    assert status.loc[['S1','S2','S3','S4-P3','S5'],'status'].eq('blocked').all()
    result=pd.read_csv(base/'scenarios/phenology_scenarios.csv',parse_dates=['reference_predicted_date','scenario_predicted_date'])
    original=pd.read_csv(base/'phenology/P2_cv_predictions.csv',parse_dates=['predicted_event_date'])
    original=original[(original.validation=='LOYO')&(original.model_id=='P2-M1')].set_index('season_id')
    assert len(result)==24 and result.parameters_refitted.eq(False).all()
    assert set(result.temperature_shift_c)=={1,2}
    for row in result.itertuples():
        assert row.reference_predicted_date==original.loc[row.season_id,'predicted_event_date']
        assert row.date_shift_days==(row.scenario_predicted_date-row.reference_predicted_date).days
        assert row.fit_id==f'main_P2_P2-M1_LOYO_{row.harvest_year}'


def test_no_unvalidated_typhoon_loss_or_yield_scenario(context):
    base=context[0]/'results/r4'
    case=pd.read_csv(base/'typhoon/bannei_2025_reference.csv').iloc[0]
    assert case.actual_yield_kg_mu==0
    assert pd.isna(case.normal_production_reference_kg_mu) and pd.isna(case.reference_gap_kg_mu)
    assert pd.read_csv(base/'scenarios/yield_scenarios.csv').empty
