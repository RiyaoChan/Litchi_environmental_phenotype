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
