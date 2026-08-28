import json
import pandas as pd
import pytest
from src.io_utils import load_config
from src.r4_weather_loader import read_weather,master_table,settings
from src.phenology_models import WeatherStore,PhenologyEngine
from src.r4_stage_features import WindowBuilder


@pytest.fixture(scope='module')
def windows(context):
    root,cfg=load_config(context[0]/'configs/r4_experiment_v3.yaml')
    daily,hourly,_=read_weather(root,cfg); master=master_table(root,cfg)
    model_cfg=settings(root,cfg,'phenology'); engine=PhenologyEngine(WeatherStore(daily,hourly,model_cfg),model_cfg)
    return root,cfg,master,engine,WindowBuilder(root,cfg,master,engine)


def test_w3_uses_cross_fitted_phenology_only(windows):
    root,cfg,master,engine,builder=windows
    row=master[master.season_id=='bannei_2024'].iloc[0]
    dates,trace=builder.chain([2022,2023,2025,2026],row)
    tampered=row.copy()
    for event in ['inflorescence_emergence','full_bloom','maturity']: tampered[event]=pd.Timestamp('2040-12-31')
    fresh=WindowBuilder(root,cfg,master,engine)
    dates2,trace2=fresh.chain([2022,2023,2025,2026],tampered)
    assert dates==dates2 and trace==trace2
    assert all(2024 not in t['training_years'] for t in trace)


def test_w3_training_rows_exclude_own_and_outer_year(windows):
    root,cfg,master,engine,builder=windows
    normal=master[master.yield_main_eligible.eq(1)]
    train=normal[normal.harvest_year!=2024]; test=normal[normal.harvest_year==2024]
    training,evaluation=builder.partition(train,test,'W3-PRED')
    for row in training.itertuples():
        for step in json.loads(row.chain_trace):
            assert 2024 not in step['training_years'] and row.harvest_year not in step['training_years']
    for row in evaluation.itertuples():
        for step in json.loads(row.chain_trace): assert 2024 not in step['training_years']


def test_median_window_never_uses_test_dates(windows):
    root,cfg,master,engine,builder=windows
    row=master[master.season_id=='bannei_2024'].iloc[0]
    first,_=builder.boundaries('W1-MEDIAN',[2022,2023,2025,2026],row)
    altered=master.copy()
    for event in ['autumn_flush_mature','inflorescence_emergence','full_bloom','maturity']:
        altered.loc[altered.harvest_year==2024,event]=pd.Timestamp('2040-12-31')
    other=WindowBuilder(root,cfg,altered,engine)
    second,_=other.boundaries('W1-MEDIAN',[2022,2023,2025,2026],row)
    assert first==second


def test_w3_hongming_2026_missing_start_not_fabricated(windows):
    builder=windows[-1]; master=windows[2]
    row=master[master.season_id=='hongming_2026'].iloc[0]
    dates,trace=builder.chain([2022,2023,2024,2025],row)
    assert all(pd.isna(date) for date in dates)
