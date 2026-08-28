import json
import pandas as pd
import pytest
from src.io_utils import load_config
from src.r4_weather_loader import read_weather,master_table,freeze_r4


@pytest.fixture(scope='module')
def r4(context):
    root,cfg=load_config(context[0]/'configs/r4_experiment_v3.yaml')
    return root,cfg,*read_weather(root,cfg)


def test_r4_daily_row_count(r4):
    assert len(r4[2])==5385 and r4[2].groupby('orchard_id').size().eq(1795).all()


def test_r4_hourly_row_count(r4):
    assert len(r4[3])==129240 and r4[3].groupby('orchard_id').size().eq(43080).all()


def test_r4_exact_orchard_coordinates(r4):
    for orchard,(lat,lon) in r4[1]['orchards'].items():
        for frame in r4[2:4]:
            g=frame[frame.orchard_id==orchard]
            assert (g.requested_latitude-lat).abs().max()<1e-8
            assert (g.requested_longitude-lon).abs().max()<1e-8


def test_r4_daily_continuity(r4):
    expected=pd.date_range('2021-08-01','2026-06-30')
    assert all(pd.DatetimeIndex(g.date).equals(expected) for _,g in r4[2].groupby('orchard_id'))


def test_r4_hourly_continuity(r4):
    expected=pd.date_range('2021-08-01','2026-06-30 23:00',freq='h')
    assert all(pd.DatetimeIndex(g.time).equals(expected) for _,g in r4[3].groupby('orchard_id'))


def test_r4_no_duplicate_dates(r4):
    assert not r4[2].duplicated(['orchard_id','date']).any()
    assert not r4[3].duplicated(['orchard_id','time']).any()


def test_r4_temperature_order(r4):
    d=r4[2]
    assert ((d.tmin_c<=d.tmean_c)&(d.tmean_c<=d.tmax_c)).all()


def test_r4_humidity_precip_soil_ranges(r4):
    h=r4[3]
    assert h.relative_humidity_pct.between(0,100).all()
    assert h.vpd_kpa.ge(0).all() and h.precip_mm.ge(0).all()
    assert h.filter(like='soil_moisture').ge(0).all().all()
    assert h.filter(like='soil_moisture').le(1).all().all()


def test_r4_source_freeze_and_master_eligibility(r4):
    root,cfg=r4[:2]
    freeze_r4(root,cfg)
    m=master_table(root,cfg)
    assert len(m)==15 and not m.season_id.duplicated().any()
    assert m.loc[m.season_id=='bannei_2022','autumn_flush_mature'].iloc[0]==pd.Timestamp('2021-09-25')
    assert set(m[m.yield_main_eligible.eq(1)].season_id).isdisjoint({'bannei_2025','hongming_2025','hongming_2026'})
    assert m.loc[m.season_id=='bannei_2025','final_yield_kg_per_mu'].iloc[0]==0


def test_r4_grids_not_copied(r4):
    d=r4[2]
    assert d[['grid_latitude','grid_longitude']].drop_duplicates().shape[0]==3
    a=d[d.orchard_id=='bannei'].set_index('date')
    b=d[d.orchard_id=='hongming'].set_index('date')
    assert not a.tmean_c.equals(b.tmean_c) and not a.precip_mm.equals(b.precip_mm)
