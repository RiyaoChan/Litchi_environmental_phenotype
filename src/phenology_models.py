"""Finite, preregistered accumulation models; fitting never consumes test targets."""
from __future__ import annotations

from copy import deepcopy
import json
import math
import numpy as np
import pandas as pd


def spec_key(spec):
    return json.dumps(spec,sort_keys=True,separators=(',',':'))


def day_offset(date,year):
    return (pd.Timestamp(date)-pd.Timestamp(int(year),1,1)).days


def primary_candidates(task,config):
    candidates=[]
    def add(model,kind,**parameters):
        candidates.append({'model_id':model,'kind':kind,**parameters})
    add(task+'-B0','duration')
    if task=='P1':
        add('P1-B1','calendar')
        for variable in config['P1']['cold_count_daily_variables']:
            for threshold in config['P1']['cold_count_thresholds_c']:
                add('P1-D1','cold_count_day',variable=variable,temperature=threshold)
        for base in config['P1']['cold_degree_bases_c']: add('P1-D2','cold_degree_day',temperature=base)
        for threshold in config['P1']['cold_count_thresholds_c']: add('P1-H1','cold_count_hour',temperature=threshold)
        for base in config['P1']['cold_degree_bases_c']: add('P1-H2','cold_degree_hour',temperature=base)
        n=config['P1']['nonlinear']
        for optimum in n['optimum_candidates_c']:
            for upper in n['upper_candidates_c']:
                add('P1-H3','triangular_hour',lower=n['fixed_lower_c'],optimum=optimum,upper=upper)
    else:
        for base in config[task]['gdd_bases_c']: add(task+'-M1','gdd',temperature=base)
    return candidates


class WeatherStore:
    """Local-calendar arrays. Hourly cold metrics preserve all 24 temperatures/day.

    Summing an hourly response to daily increments is exact for the date of first
    threshold crossing; observations have no subdaily event-time precision.
    """
    def __init__(self,daily,hourly,config):
        self.config=config
        self.daily={o:g.sort_values('date').set_index('date') for o,g in daily.groupby('orchard_id')}
        self.hourly={o:g.sort_values('time').set_index('time') for o,g in hourly.groupby('orchard_id')}
        self.origin=daily.date.min()
        self.end=daily.date.max()
        self._increments={}; self._prefix={}

    def index(self,date):
        return (pd.Timestamp(date).normalize()-self.origin).days

    def increments(self,orchard,spec,temperature_shift=0.0):
        key=(orchard,spec_key(spec),float(temperature_shift))
        if key in self._increments: return self._increments[key]
        d=self.daily[orchard]
        h=self.hourly.get(orchard,pd.DataFrame())
        kind=spec['kind']
        if kind=='cold_count_day':
            value=(d[spec['variable']].to_numpy()+temperature_shift<spec['temperature']).astype(float)
        elif kind=='cold_degree_day':
            value=np.maximum(0,spec['temperature']-d.tmean_c.to_numpy()-temperature_shift)
        elif kind=='gdd':
            value=np.maximum(0,d.tmean_c.to_numpy()+temperature_shift-spec['temperature'])
        else:
            if h.empty: raise ValueError('Hourly model cannot use a daily-only source')
            temp=h.temperature_c.to_numpy()+temperature_shift
            if kind=='cold_count_hour': value=(temp<spec['temperature']).astype(float)
            elif kind=='cold_degree_hour': value=np.maximum(0,spec['temperature']-temp)
            elif kind=='triangular_hour':
                value=np.clip(np.minimum((temp-spec['lower'])/(spec['optimum']-spec['lower']),
                                         (spec['upper']-temp)/(spec['upper']-spec['optimum'])),0,1)
            else: raise ValueError('Unsupported accumulation kind: '+kind)
            value=value.reshape(len(d),24).sum(axis=1)
        if 'modifier' in spec:
            variable=spec['modifier']
            if variable=='water_balance': modifier=(d.precip_mm-d.et0_mm).to_numpy()
            elif variable=='dry_day': modifier=(d.precip_mm.to_numpy()<0.1).astype(float)
            elif variable=='vpd': modifier=h.vpd_kpa.to_numpy().reshape(len(d),24).mean(axis=1)
            elif variable=='root_zone_moisture': modifier=h.soil_moisture_7_28cm_m3_m3.to_numpy().reshape(len(d),24).mean(axis=1)
            elif variable=='radiation': modifier=d.shortwave_radiation_mj_m2.to_numpy()
            elif variable=='heat_day': modifier=(d.tmax_c.to_numpy()+temperature_shift>32).astype(float)
            elif variable=='heat_hour_fraction': modifier=(h.temperature_c.to_numpy().reshape(len(d),24)+temperature_shift>32).mean(axis=1)
            else: raise ValueError(variable)
            low,high=self.config['extensions']['response_multiplier_bounds']
            value=value*np.clip(1+spec['coefficient']*modifier/self.config['extensions']['scales'][variable],low,high)
        self._increments[key]=value
        return value

    def prefix(self,orchard,spec,temperature_shift=0.0):
        key=(orchard,spec_key(spec),float(temperature_shift))
        if key not in self._prefix:
            self._prefix[key]=np.r_[0,np.cumsum(self.increments(orchard,spec,temperature_shift))]
        return self._prefix[key]

    def accumulation(self,orchard,spec,start,end,temperature_shift=0.0):
        first,last=self.index(start),self.index(end)
        if first<0 or last>=len(self.daily[orchard]) or last<first: return np.nan
        p=self.prefix(orchard,spec,temperature_shift)
        return float(p[last+1]-p[first])

    def crossing(self,orchard,spec,start,year,threshold,temperature_shift=0.0):
        if pd.isna(start): return pd.NaT,'missing_start'
        first=self.index(start)
        horizon=pd.Timestamp(self.config['prediction_horizon'].replace('{Y}',str(int(year))))
        last=self.index(horizon)
        if first<0 or first>=last or last>=len(self.daily[orchard]): return pd.NaT,'outside_weather_horizon'
        if not np.isfinite(threshold) or threshold<=self.config['zero_accumulation_epsilon']:
            return pd.NaT,'invalid_zero_or_nonfinite_threshold'
        p=self.prefix(orchard,spec,temperature_shift)
        segment=p[first+1:last+2]-p[first]
        offset=int(np.searchsorted(segment,threshold,side='left'))
        if offset>=len(segment): return pd.NaT,'threshold_not_reached'
        offset=max(offset,self.config['min_duration_days'])
        prediction=pd.Timestamp(start).normalize()+pd.Timedelta(days=offset)
        return prediction,'predicted'


def fit_candidate(train,spec,weather,config):
    if train.empty: raise ValueError('No training endpoints')
    values=[]
    for r in train.itertuples():
        if spec['kind']=='duration': value=float(r.duration_days)
        elif spec['kind']=='calendar': value=float(day_offset(r.end_date,r.harvest_year))
        else: value=weather.accumulation(r.orchard_id,spec,r.start_date,r.end_date)
        values.append(value)
    calibration=train[['season_id','orchard_id','harvest_year']].copy()
    calibration['threshold']=values
    if not np.isfinite(calibration.threshold).all(): raise ValueError('Incomplete training accumulation')
    pooled=float(calibration.threshold.median())
    parameters={}; scopes={}; used={}
    for orchard in weather.daily:
        local=calibration[calibration.orchard_id==orchard]
        selected=local if len(local)>=config['min_orchard_training_samples'] else calibration
        parameters[orchard]=float(selected.threshold.median())
        scopes[orchard]='orchard' if selected is local else 'pooled_training_fallback'
        used[orchard]=sorted(selected.season_id.tolist())
    return {'spec':deepcopy(spec),'parameters':parameters,'pooled_parameter':pooled,
            'fit_scope':scopes,'fit_season_ids':used,
            'training_years':sorted(map(int,train.harvest_year.unique())),
            'training_season_ids':sorted(train.season_id.tolist()),
            'training_calibration':calibration.to_dict('records')}


def predict_fit(fit,test,weather,temperature_shift=0.0):
    """Test needs ID, orchard, harvest_year, start_date ONLY. Never read end_date."""
    rows=[]
    spec=fit['spec']
    for r in test.itertuples():
        parameter=fit['parameters'].get(r.orchard_id,fit['pooled_parameter'])
        if pd.isna(r.start_date): prediction,status=pd.NaT,'missing_start'
        elif spec['kind']=='duration':
            prediction=pd.Timestamp(r.start_date)+pd.Timedelta(days=math.floor(parameter+0.5)); status='predicted'
        elif spec['kind']=='calendar':
            prediction=pd.Timestamp(int(r.harvest_year),1,1)+pd.Timedelta(days=math.floor(parameter+0.5)); status='predicted'
            if prediction<=pd.Timestamp(r.start_date): prediction,status=pd.NaT,'calendar_prediction_not_after_start'
        else:
            prediction,status=weather.crossing(r.orchard_id,spec,r.start_date,r.harvest_year,parameter,temperature_shift)
        rows.append({'season_id':r.season_id,'predicted_event_date':prediction,'prediction_status':status,
                     'fitted_threshold':parameter,'fit_scope':fit['fit_scope'].get(r.orchard_id,'pooled_training_fallback')})
    return pd.DataFrame(rows)


def score_predictions(test,prediction,config):
    rows=test.merge(prediction,on='season_id',validate='one_to_one')
    rows['predicted_event_date']=pd.to_datetime(rows.predicted_event_date)
    rows['error_days']=(rows.predicted_event_date-rows.end_date).dt.days.astype(float)
    rows['absolute_error_score_days']=rows.error_days.abs().fillna(config['unreached_score_penalty_days'])
    return rows


class PhenologyEngine:
    def __init__(self,weather,config):
        self.weather=weather; self.config=config; self._cache={}

    def _inner_score(self,train,spec):
        years=sorted(train.harvest_year.unique())
        if len(years)<2: return np.nan
        errors=[]
        for year in years:
            tr=train[train.harvest_year!=year]; va=train[train.harvest_year==year]
            fitted=fit_candidate(tr,spec,self.weather,self.config)
            scored=score_predictions(va,predict_fit(fitted,va,self.weather),self.config)
            errors.extend(scored.absolute_error_score_days.tolist())
        return float(np.mean(errors))

    def fit(self,train,task,model_id=None,weather_only=False,daily_only=False):
        fingerprint=tuple((r.season_id,str(r.start_date),str(r.end_date),r.duration_days) for r in train.sort_values('season_id').itertuples())
        key=(task,model_id,weather_only,daily_only,fingerprint)
        if key in self._cache: return deepcopy(self._cache[key])
        extension=model_id in ['P1-W1','P2-M2','P3-M2']
        if extension:
            base=self.fit(train,task,weather_only=True)
            specs=[]
            for modifier in self.config['extensions'][model_id]:
                for coefficient in self.config['extensions']['coefficient_candidates']:
                    specs.append({**base['spec'],'model_id':model_id,'modifier':modifier,'coefficient':coefficient})
        else:
            specs=primary_candidates(task,self.config)
            if model_id: specs=[s for s in specs if s['model_id']==model_id]
            if weather_only: specs=[s for s in specs if s['kind'] not in ['duration','calendar']]
            if daily_only: specs=[s for s in specs if s['model_id'] in ['P1-D1','P1-D2']]
        if not specs: raise ValueError(f'No candidates for {task}/{model_id}')
        if train.harvest_year.nunique()<2 and model_id is None and not weather_only:
            specs=[{'model_id':task+'-B0','kind':'duration'}]
        scores=[self._inner_score(train,spec) for spec in specs]
        selected=int(np.argmin(np.where(np.isfinite(scores),scores,np.inf)))
        fitted=fit_candidate(train,specs[selected],self.weather,self.config)
        fitted['inner_mae_days']=scores[selected] if np.isfinite(scores[selected]) else None
        fitted['candidate_scores']=[{'candidate_index':i,'spec':s,'inner_mae_days':v if np.isfinite(v) else None}
                                    for i,(s,v) in enumerate(zip(specs,scores))]
        fitted['selection_mode']='nested_training_year_cv' if train.harvest_year.nunique()>=2 else 'fixed_first_candidate_insufficient_inner_years'
        self._cache[key]=deepcopy(fitted)
        return fitted
