"""One fixed low-dimensional Ridge family with training-only scaling."""
from __future__ import annotations
import numpy as np
from sklearn.linear_model import Ridge


def orchard_design(orchards,categories):
    # Fixed reference coding is schema, not learned from held-out values.
    return np.column_stack([(orchards==c).astype(float) for c in categories[1:]])


def fit_ridge(features,targets,columns,alpha,categories):
    if len(columns)>6: raise ValueError('V3 continuous-feature limit exceeded')
    data=features.merge(targets[['season_id','final_yield_kg_per_mu']],on='season_id',validate='one_to_one')
    x=data[columns].to_numpy(dtype=float); y=data.final_yield_kg_per_mu.to_numpy(dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all(): raise ValueError('Missing training features/target; no silent imputation')
    mean=x.mean(axis=0); scale=x.std(axis=0); scale[scale==0]=1
    design=np.column_stack([(x-mean)/scale,orchard_design(data.orchard_id.to_numpy(),categories)])
    model=Ridge(alpha=float(alpha),fit_intercept=True).fit(design,y)
    return {'columns':list(columns),'alpha':float(alpha),'mean':mean.tolist(),'scale':scale.tolist(),
            'categories':list(categories),'coefficient':model.coef_.tolist(),'intercept':float(model.intercept_),
            'training_season_ids':sorted(data.season_id.tolist()),
            'training_years':sorted(map(int,data.harvest_year.unique()))}


def predict_ridge(fit,features):
    x=features[fit['columns']].to_numpy(dtype=float)
    if not np.isfinite(x).all(): raise ValueError('Missing prediction feature')
    design=np.column_stack([(x-np.array(fit['mean']))/np.array(fit['scale']),
                            orchard_design(features.orchard_id.to_numpy(),fit['categories'])])
    return design@np.array(fit['coefficient'])+fit['intercept']


def historical_yield_predict(training,testing):
    values=[]
    for row in testing.itertuples():
        local=training[training.orchard_id==row.orchard_id]
        use=local if len(local) else training
        values.append(float(use.final_yield_kg_per_mu.median()))
    return np.array(values)
