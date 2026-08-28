import json
import re
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


def test_saved_w3_lineage_excludes_outer_inner_and_own_training_year(context):
    rows=pd.read_csv(context[0]/'results/r4/yield/feature_partition_manifest.csv',keep_default_na=False)
    rows=rows[rows.model_id.isin(['Y-W3P','Y-W3P+PHENO'])]
    assert len(rows)>0 and rows.context.str.contains('_inner_').any()
    for row in rows.itertuples():
        excluded=set(map(int,re.findall(r'(?:outer|inner)_(\d{4})',row.context)))
        partition=set(map(int,filter(None,row.partition_training_years.split(';'))))
        boundary=set(map(int,filter(None,row.boundary_training_years.split(';'))))
        assert not partition.intersection(excluded)
        assert boundary.issubset(partition)
        if row.role=='training':
            excluded.add(int(row.season_id.rsplit('_',1)[1]))
        assert not boundary.intersection(excluded)
        for stage in json.loads(row.chain_trace):
            assert not set(stage['training_years']).intersection(excluded)
            assert set(stage['training_years']).issubset(boundary)
            if row.role=='training': assert row.season_id not in stage.get('training_season_ids',[])


def test_saved_yield_fits_and_scalers_use_training_rows_only(context):
    base=context[0]/'results/r4'
    fits=json.loads((base/'yield/fitted_models.json').read_text(encoding='utf-8'))
    names={'Y-W1C':'W1_calendar_features','Y-W1M':'W1_median_features',
           'Y-W2O':'W2_observed_features','Y-W3P':'W3_predicted_features','Y-W3P+PHENO':'W3_predicted_features'}
    for fit_id,fit in fits.items():
        holdout=int(re.search(r'outer_(\d{4})',fit_id)[1])
        assert holdout not in fit['training_years']
        assert 'bannei_2025' not in fit['training_season_ids']
        if not fit_id.startswith('MAIN_LOYO_') or fit_id.endswith('_Y-B0'): continue
        model=fit_id.split('_Y-',1)[1]; model='Y-'+model
        features=pd.read_csv(base/'windows'/(names[model]+'.csv'))
        train=features[(features.outer_holdout_year==holdout)&(features.role=='training')]
        assert set(train.season_id)==set(fit['training_season_ids'])
        x=train[fit['columns']].to_numpy(dtype=float)
        scale=x.std(axis=0); scale[scale==0]=1
        # CSV features are serialized to 10 significant digits; JSON fits retain full precision.
        np.testing.assert_allclose(fit['mean'],x.mean(axis=0),rtol=1e-8,atol=1e-8)
        np.testing.assert_allclose(fit['scale'],scale,rtol=1e-8,atol=1e-8)


def test_partial_yield_predictions_never_count_as_formal_success(context):
    base=context[0]/'results/r4/yield'
    summary=pd.read_csv(base/'model_comparison.csv')
    main=summary[(summary.cohort=='MAIN')&(summary.validation=='LOYO')].set_index('model_id')
    gate=json.loads((base/'yield_gate.json').read_text(encoding='utf-8'))
    assert main.loc['Y-W3P','status']=='partial_not_matched_main'
    assert main.loc['Y-W3P','n_predictions']==8
    assert not gate['formal_yield_comparison_complete'] and not gate['Y_W3P_success']
    assert main.loc['Y-B0','n_predictions']==12
