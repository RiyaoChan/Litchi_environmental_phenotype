import numpy as np
import pandas as pd
import pytest
from src.yield_models import fit_ridge,predict_ridge,historical_yield_predict


def small_training():
    features=pd.DataFrame({'season_id':['bannei_2022','bannei_2023'],'orchard_id':['bannei']*2,
                           'harvest_year':[2022,2023],'x':[1.,3.]})
    targets=pd.DataFrame({'season_id':features.season_id,'final_yield_kg_per_mu':[100.,200.]})
    return features,targets


def test_ridge_scaler_fit_on_training_only():
    features,targets=small_training()
    fit=fit_ridge(features,targets,['x'],1,['bannei','hongming','luhong'])
    assert fit['mean']==[2.] and fit['scale']==[1.]
    test=features.iloc[:1].copy(); test['x']=1e9; test['harvest_year']=2024
    _=predict_ridge(fit,test)
    assert fit['mean']==[2.] and fit['scale']==[1.]
    assert 2024 not in fit['training_years']


def test_yield_feature_count_limit():
    features,targets=small_training()
    with pytest.raises(ValueError,match='limit'):
        fit_ridge(features,targets,['x']*7,1,['bannei','hongming','luhong'])


def test_yield_no_missing_feature_imputation():
    features,targets=small_training(); features.loc[0,'x']=np.nan
    with pytest.raises(ValueError,match='Missing'):
        fit_ridge(features,targets,['x'],1,['bannei','hongming','luhong'])


def test_bannei_2025_excluded_from_normal_yield_fit(context):
    m=pd.read_csv(context[0]/'data/processed/r4_orchard_season_master.csv')
    assert 'bannei_2025' not in set(m[m.yield_main_eligible.eq(1)].season_id)


def test_hongming_damage_main_exclusion(context):
    m=pd.read_csv(context[0]/'data/processed/r4_orchard_season_master.csv')
    assert {'hongming_2025','hongming_2026'}.isdisjoint(set(m[m.yield_main_eligible.eq(1)].season_id))


def test_tree_classes_not_split_across_cv(context):
    m=pd.read_csv(context[0]/'data/processed/r4_orchard_season_master.csv')
    assert m.season_id.nunique()==len(m)==15
    assert m[['orchard_id','harvest_year']].drop_duplicates().shape[0]==15
