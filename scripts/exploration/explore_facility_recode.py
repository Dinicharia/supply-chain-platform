# explore_facility_recode.py
#
# One-off exploration script: inspects the raw DHS Kenya 2010 SPA
# Facility Recode file so we can understand its structure before
# deciding which columns map to our facilities / commodities /
# facility_commodity_readiness tables. Not part of the production
# pipeline - purely diagnostic.

import pandas as pd

# Path to the raw Facility Recode Stata file (downloaded from DHS).
FACILITY_RECODE_PATH = "data/raw/dhs_spa_2010/facility_recode/KEFC6AFLSR.DTA"

# pandas can read Stata (.dta) files directly - no separate library needed.
# convert_categoricals=False keeps raw numeric/coded values as-is for now;
# we'll decide how to handle value labels once we've seen the structure.
df = pd.read_stata(FACILITY_RECODE_PATH, convert_categoricals=False)

# Basic shape: how many facilities (rows), how many fields (columns)?
print(f"Shape: {df.shape[0]} rows, {df.shape[1]} columns")
print()

# List all column names - SPA files often have hundreds of columns,
# so this will be long, but it's exactly what we need to see.
print("Column names:")
for col in df.columns:
    print(f"  {col}")