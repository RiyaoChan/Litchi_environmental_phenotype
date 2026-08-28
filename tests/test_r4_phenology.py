import json
import numpy as np
import pandas as pd
import pytest

from src.io_utils import load_config
from src.r4_weather_loader import read_weather,master_table,task_frame,settings
from src.phenology_models import WeatherStore,PhenologyEngine,predict_fit,fit_candidate,score_predictions


@pytest.fixture(scope='module')
def pheno(context):
    root,cfg=load_config(context[0]/'configs/r4_experiment_v3.yaml')
    d,h,_=read_weather(root,cfg)
    settings_=settings(root,cfg,'phenology')
    engine=PhenologyEngine(WeatherStore(d,h,settings_),settings_)
    return root,cfg,master_table(root,cfg),engine


def test_loyo_holds_entire_year(pheno):
    root,_,_,_=pheno
    path=root/'results/r4/phenology/P1_cv_predictions.csv'
    if not path.exists(): pytest.skip('P1 phase not executed yet')
    rows=pd.read_csv(path)
    for row in rows.itertuples():
        train=list(map(int,row.training_years.split(';')))
        assert row.holdout_year not in train
        if row.validation=='rolling': assert max(train)<row.holdout_year
        assert all(not s.endswith('_'+str(row.holdout_year)) for s in row.training_season_ids.split(';'))


def test_threshold_selection_train_only(pheno,monkeypatch):
    _,_,master,engine=pheno
    frame=task_frame(master,'P1')
    train=frame[frame.harvest_year!=2024]
    seen=[]
    import src.phenology_models as module
    original=module.fit_candidate
    def recording_fit(data,*args):
        seen.append(set(data.harvest_year))
        return original(data,*args)
    monkeypatch.setattr(module,'fit_candidate',recording_fit)
    fresh=PhenologyEngine(engine.weather,engine.config)
    fit=fresh.fit(train,'P1','P1-D1')
    assert seen and all(2024 not in years for years in seen)
    assert 2024 not in fit['training_years']
    assert len(fit['candidate_scores'])==8


def test_no_holdout_year_in_parameter_fit(pheno):
    _,_,master,engine=pheno
    frame=task_frame(master,'P1'); train=frame[frame.harvest_year!=2024]; test=frame[frame.harvest_year==2024]
    fit=engine.fit(train,'P1','P1-H1')
    prediction=predict_fit(fit,test,engine.weather)
    tampered=test.assign(end_date=pd.Timestamp('2040-01-01'),duration_days=10000)
    pd.testing.assert_frame_equal(prediction,predict_fit(fit,tampered,engine.weather))
    for orchard,ids in fit['fit_season_ids'].items(): assert set(ids).isdisjoint(test.season_id)


def test_predicted_date_after_observed_start(pheno):
    _,_,master,engine=pheno
    frame=task_frame(master,'P1')
    fit=engine.fit(frame[frame.harvest_year!=2024],'P1','P1-H3')
    test=frame[frame.harvest_year==2024]
    result=test.merge(predict_fit(fit,test,engine.weather),on='season_id')
    good=result[result.predicted_event_date.notna()]
    assert (good.predicted_event_date>good.start_date).all()


def test_hourly_low_temperature_count_uses_within_day_variation(pheno):
    cfg=pheno[3].config
    d=pd.DataFrame({'orchard_id':['s'],'date':pd.to_datetime(['2022-01-01']),'tmean_c':[20],'tmin_c':[10]})
    h=pd.DataFrame({'orchard_id':['s']*24,'time':pd.date_range('2022-01-01',periods=24,freq='h'),
                    'temperature_c':[10]*12+[30]*12})
    store=WeatherStore(d,h,cfg)
    assert store.increments('s',{'kind':'cold_count_day','variable':'tmean_c','temperature':20})[0]==0
    assert store.increments('s',{'kind':'cold_count_hour','temperature':20})[0]==12


def test_failed_accumulation_predictions_not_dropped(pheno):
    _,_,master,engine=pheno
    frame=task_frame(master,'P1').head(2)
    fit=fit_candidate(frame,{'model_id':'P1-D2','kind':'cold_degree_day','temperature':18},engine.weather,engine.config)
    fit['parameters']={o:1e20 for o in fit['parameters']}
    result=score_predictions(frame,predict_fit(fit,frame,engine.weather),engine.config)
    assert len(result)==2 and result.predicted_event_date.isna().all()
    assert result.absolute_error_score_days.eq(365).all()


def test_baseline_matches_r2_registered_result(pheno):
    root=pheno[0]
    path=root/'results/r4/phenology/P1_model_comparison.csv'
    if not path.exists(): pytest.skip('P1 phase not executed yet')
    rows=pd.read_csv(path)
    value=rows[(rows.model_id=='P1-B0')&(rows.validation=='LOYO')].iloc[0]
    assert value.n_samples==value.n_predictions==12
    assert value.MAE_days==pytest.approx(4.8333333333)


def test_all_p1_models_use_same_test_seasons(pheno):
    path=pheno[0]/'results/r4/phenology/P1_cv_predictions.csv'
    if not path.exists(): pytest.skip('P1 phase not executed yet')
    rows=pd.read_csv(path); rows=rows[rows.validation=='LOYO']
    groups=[set(g.season_id) for _,g in rows.groupby('model_id')]
    assert all(s==groups[0] for s in groups) and len(groups[0])==12
