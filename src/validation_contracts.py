"""Grouping contract only; no phenology/yield model has been fitted."""
import numpy as np


def loyo_indices(harvest_years):
    years=np.asarray(harvest_years)
    for year in sorted(set(years.tolist())):
        yield year,np.flatnonzero(years!=year),np.flatnonzero(years==year)
