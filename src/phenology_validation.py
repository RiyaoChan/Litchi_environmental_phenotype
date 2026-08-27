"""Weather-independent LOYO baselines. These do not test meteorological effects."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
import yaml

from .validation_contracts import loyo_indices
from .io_utils import write_csv


def day_offset(day,harvest_year):
    return (pd.Timestamp(day)-pd.Timestamp(int(harvest_year),1,1)).days


def baseline_predict(train,test,model_id):
    """Fit using train only; test target is never accessed here."""
    predictions=[]
    for row in test.itertuples():
        local=train[train.orchard_id==row.orchard_id]
        fit=local if len(local) else train
        if fit.empty: raise ValueError('No training seasons for baseline')
        if model_id.endswith('B1'):
            # P1 target is in Jan/Feb in this dataset. Year-relative offsets also
            # handle a possible December target without discontinuous DOY medians.
            values=[day_offset(r.observed_end_date,r.harvest_year) for r in fit.itertuples()]
            parameter=float(np.median(values))
            prediction=pd.Timestamp(int(row.harvest_year),1,1)+pd.Timedelta(days=math.floor(parameter+.5))
            parameter_kind='median_target_day_offset_from_harvest_Jan01'
        else:
            parameter=float(fit.observed_duration_days.median())
            prediction=pd.Timestamp(row.observed_start_date)+pd.Timedelta(days=math.floor(parameter+.5))
            parameter_kind='median_duration_days'
        predictions.append({'season_id':row.season_id,'predicted_event_date':prediction,
                            'predicted_duration_days':(prediction-pd.Timestamp(row.observed_start_date)).days,
                            'parameter_value':parameter,'parameter_kind':parameter_kind,
                            'fit_scope':'orchard' if len(local) else 'pooled_training_fallback',
                            'n_fit_samples':len(fit),'training_years':';'.join(map(str,sorted(train.harvest_year.unique()))),
                            'fit_season_ids':';'.join(sorted(fit.season_id)),
                            'all_training_season_ids':';'.join(sorted(train.season_id))})
    return pd.DataFrame(predictions)


def metrics(rows):
    errors=rows.error_days.astype(float)
    obs,pred=rows.observed_season_day,rows.predicted_season_day
    r=float(obs.rank().corr(pred.rank())) if obs.nunique()>1 and pred.nunique()>1 and len(rows)>1 else np.nan
    return {'n':len(rows),'MAE_days':float(errors.abs().mean()),
            'RMSE_days':float(np.sqrt(np.mean(errors**2))),
            'mean_bias_days':float(errors.mean()),'Spearman_r':r,
            'prediction_interval_coverage':np.nan,
            'interval_note':'not_estimated_insufficient_independent_calibration_years'}


def cross_validate_baselines(transitions,cohort='main'):
    eligible='main_complete_date_pair' if cohort=='main' else 'sensitivity_complete_date_pair'
    predictions=[]
    for task in ['P1','P2','P3']:
        frame=transitions[(transitions.task==task)&(transitions[eligible]==1)].reset_index(drop=True)
        if frame.harvest_year.nunique()<2: continue
        models=[task+'-B0']+(['P1-B1'] if task=='P1' else [])
        for model in models:
            for year,train_idx,test_idx in loyo_indices(frame.harvest_year):
                train,test=frame.iloc[train_idx],frame.iloc[test_idx]
                pred=baseline_predict(train,test,model)
                out=test.merge(pred,on='season_id',validate='one_to_one')
                for row in out.itertuples():
                    observed=pd.Timestamp(row.observed_end_date)
                    predicted=pd.Timestamp(row.predicted_event_date)
                    predictions.append({'task':task,'model_id':model,'cohort':cohort,
                        'holdout_year':int(year),'season_id':row.season_id,'orchard_id':row.orchard_id,
                        'harvest_year':int(row.harvest_year),'observed_start_date':row.observed_start_date,
                        'observed_event_date':observed,'predicted_event_date':predicted,
                        'observed_duration_days':row.observed_duration_days,
                        'predicted_duration_days':row.predicted_duration_days,'error_days':(predicted-observed).days,
                        'observed_season_day':day_offset(observed,row.harvest_year),
                        'predicted_season_day':day_offset(predicted,row.harvest_year),
                        'prediction_interval_lower':pd.NaT,'prediction_interval_upper':pd.NaT,
                        'interval_status':'not_estimated_only_four_training_year_groups',
                        'parameter_value':row.parameter_value,'parameter_kind':row.parameter_kind,
                        'fit_scope':row.fit_scope,'n_fit_samples':row.n_fit_samples,
                        'training_years':row.training_years,'fit_season_ids':row.fit_season_ids,
                        'all_training_season_ids':row.all_training_season_ids,
                        'forecast_context':'conditional_on_observed_stage_start; retrospective_LOYO_not_rolling_forecast'})
    return pd.DataFrame(predictions)


def run_baselines(root,transitions,gate,cfg):
    if not gate['dates_ready']:
        raise RuntimeError('Date gate forbids baseline execution')
    settings=yaml.safe_load((root/cfg['phenology_models_config']).read_text(encoding='utf-8'))['baseline']
    supported={'orchard_specific':True,'fallback':'pooled_training_median',
               'rounding':'half_up_to_integer_day','interval_nominal_coverage':0.90,
               'interval_method':'not_estimated_insufficient_independent_calibration_years',
               'spearman_scale':'day_offset_from_harvest_Jan01','split':'leave_entire_harvest_year_out'}
    if settings!=supported:
        raise ValueError('Unsupported baseline configuration; do not silently change the registered estimator')
    predictions=cross_validate_baselines(transitions,'main')
    sensitivity=cross_validate_baselines(transitions,'including_bannei_2025_early')
    comparison=[]
    for (task,model),group in predictions.groupby(['task','model_id'],sort=True):
        comparison.append({'task':task,'model_id':model,'cohort':'main',**metrics(group)})
    comparison=pd.DataFrame(comparison)
    for task in ['P1','P2','P3']:
        pred=predictions[predictions.task==task]
        write_csv(root/f'results/phenology/{task}_cv_predictions.csv',pred)
        write_csv(root/f'results/phenology/{task}_model_comparison.csv',comparison[comparison.task==task])
        folds=[{'model_id':m,'holdout_year':int(y),**metrics(g)} for (m,y),g in pred.groupby(['model_id','holdout_year'],sort=True)]
        write_csv(root/f'results/phenology/{task}_fold_metrics.csv',folds)
        parameters=pred[['model_id','holdout_year','orchard_id','parameter_kind','parameter_value','fit_scope','n_fit_samples','training_years','fit_season_ids']]
        write_csv(root/f'results/phenology/{task}_parameters.csv',parameters)
    write_csv(root/'results/phenology/typhoon_sensitivity_cv_predictions.csv',sensitivity)
    rows=[]
    for model in ['P1-B0','P1-B1']:
        main=predictions[predictions.model_id==model]
        alt=sensitivity[sensitivity.model_id==model]
        common=alt[alt.season_id.isin(main.season_id)]
        rows.append({'model_id':model,'main_n':len(main),'sensitivity_all_n':len(alt),
                     'main_MAE_days':metrics(main)['MAE_days'],
                     'sensitivity_common_normal_MAE_days':metrics(common)['MAE_days'],
                     'sensitivity_all_MAE_days':metrics(alt)['MAE_days'],
                     'scope':'calendar_baselines_only; not weather-model sensitivity or causal disaster analysis'})
    write_csv(root/'results/phenology/P1_typhoon_sensitivity.csv',rows)
    return predictions,comparison
