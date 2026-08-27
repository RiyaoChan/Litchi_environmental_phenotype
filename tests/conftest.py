from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
import pandas as pd
from src.io_utils import load_config

@pytest.fixture(scope='session')
def context():
    return load_config(Path(__file__).resolve().parents[1]/'configs/base.yaml')

@pytest.fixture(scope='session')
def master(context):
    return pd.read_csv(context[0]/'data/processed/orchard_season_master.csv',keep_default_na=True).fillna({'damage_review_reason':''})
