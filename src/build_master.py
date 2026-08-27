from __future__ import annotations

import json
import numpy as np
import pandas as pd


def weighted_average(values, weights):
    """Require every positive-count class; missing classes are not zero yield."""
    v, w = np.asarray(values,dtype=float), np.asarray(weights,dtype=float)
    positive = np.isfinite(w) & (w > 0)
    if not positive.any() or (~np.isfinite(v[positive])).any():
        return np.nan
    return float(np.sum(v[positive]*w[positive])/np.sum(w[positive]))


def normal_yield_subset(master):
    return master[(master.normal_production_year == 1) &
                  (master.typhoon_damage == 0) &
                  (master.yield_main_eligible == 1)].copy()


def build_master(yields, phenology, cfg):
    blocks = []
    reviews = {(x['orchard_id'],x['harvest_year']):x['reason'] for x in cfg.get('damage_review',[])}
    for block_id, g in yields.groupby('source_block_id',sort=True):
        first = g.iloc[0]
        orchard, year = first.orchard_id, int(first.harvest_year)
        typhoon = orchard == cfg['constraints']['typhoon_orchard'] and year == cfg['constraints']['typhoon_harvest_year']
        weights = g.tree_count
        mean_y = weighted_average(g.reported_class_mean_yield_kg,weights)
        mean_w = weighted_average(g.single_fruit_weight_g,weights)
        raw_final = g.reported_yield_kg_per_mu.dropna().unique()
        final_y = raw_final[0] if len(raw_final)==1 else np.nan
        reason = []
        if typhoon:
            final_y, mean_y, mean_w = 0.0,np.nan,np.nan
            reason.append('bannei_2025_structural_disaster_excluded')
        if first.year_protocol_conflict:
            reason.append('A39_protocol_conflict_unresolved')
        if (orchard,year) in reviews:
            reason.append('damage_normal_status_requires_review')
        if pd.isna(final_y):
            reason.append('missing_or_conflicting_final_yield')
        n_known = float(weights.dropna().sum())
        n_measured = float(weights[g.reported_class_mean_yield_kg.notna()].dropna().sum())
        rec = {key:first[key] for key in ['orchard_id','region_id','station_id','cultivar','source_file','source_sheet']}
        rec.update({
            'season_id':f'{orchard}_{year}','harvest_year':year,'source_block_id':block_id,
            'source_row_start':int(g.source_row.min()),'source_row_end':int(g.source_row.max()),
            'year_source_cell':first.year_source_cell,
            'raw_final_yield_kg_per_mu':raw_final[0] if len(raw_final)==1 else np.nan,
            'final_yield_kg_per_mu':float(final_y),'mean_yield_per_tree_kg':mean_y,
            'mean_single_fruit_weight_g':mean_w,
            'fruit_number_proxy':1000*mean_y/mean_w if np.isfinite(mean_w) and mean_w>0 else np.nan,
            'observed_fruit_number':np.nan,'known_tree_count':n_known,
            'weighted_mean_tree_coverage_ratio':n_measured/n_known if n_known>0 else np.nan,
            'class_mean_mismatch_count':int(g.class_mean_mismatch.sum()),
            'normal_production_year':0 if typhoon else (np.nan if (orchard,year) in reviews else 1),
            'typhoon_damage':1 if typhoon else (np.nan if (orchard,year) in reviews else 0),
            'typhoon_event_date':cfg['constraints']['typhoon_event_date'] if typhoon else None,
            'structural_damage_stage':'vegetative_recovery_and_floral_induction_affected_exact_event_date_unknown' if typhoon else None,
            'abandon_production_decision_date':'2025-03-01' if typhoon else None,
            'phenology_main_eligible':0,  # assigned after accepted-date QC
            'phenology_sensitivity_eligible':int(typhoon),
            'yield_main_eligible':int(not reason),
            'year_protocol_conflict':int(first.year_protocol_conflict),
            'damage_review_reason':reviews.get((orchard,year),''),
            'exclusion_reason':';'.join(reason),
            'yield_value_origin':'protocol_confirmed_zero' if typhoon else 'source_reported_K',
        })
        blocks.append(rec)
    block_df = pd.DataFrame(blocks)
    repeated = block_df.groupby('season_id').size()
    block_df['blocks_in_same_season'] = block_df.season_id.map(repeated)
    block_df['block_review_status'] = np.where(block_df.year_protocol_conflict.eq(1),'blocked_year_conflict',np.where(block_df.blocks_in_same_season.gt(1),'unresolved_multiple_blocks','single_block_as_labeled'))
    master = []
    for _, group in block_df.groupby('season_id',sort=True):
        rec = group.iloc[0].to_dict()
        rec['source_block_id'] = '|'.join(group.source_block_id)
        rec['n_source_blocks'] = len(group)
        if len(group)>1:
            rec['yield_main_eligible'] = 0
            rec['exclusion_reason'] += ';unresolved_multiple_blocks'
            for col in ['final_yield_kg_per_mu','mean_yield_per_tree_kg','mean_single_fruit_weight_g','fruit_number_proxy']:
                rec[col] = np.nan
        has_dates = phenology[(phenology.orchard_id == rec['orchard_id']) & (phenology.harvest_year == rec['harvest_year'])].event_date.notna().any()
        rec['phenology_main_eligible'] = int(has_dates and rec['typhoon_damage']==0 and not rec['damage_review_reason'])
        master.append(rec)
    return pd.DataFrame(master), block_df
