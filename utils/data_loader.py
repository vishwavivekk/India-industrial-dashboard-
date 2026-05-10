"""
data_loader.py — Cached data loading and preprocessing for India Industrial Dashboard.
"""
import os
import numpy as np
import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# ── NIC column → parent sector mapping ────────────────────────────────────────
# Built from the Annexure CSV column names: strip the ".N" suffix to get parent
def _derive_parent_sector(col_name: str) -> str:
    """Strip trailing '.N' suffix to recover parent industry sector name."""
    # pandas deduplication adds .1, .2, ... to repeated column names
    import re
    return re.sub(r"\.\d+$", "", col_name).strip()


@st.cache_data(show_spinner=False)
def load_units() -> pd.DataFrame:
    """Load and preprocess units_enriched.csv."""
    path = os.path.join(DATA_DIR, "units_enriched.csv")
    df = pd.read_csv(path, low_memory=False)

    # Normalise column names (strip whitespace)
    df.columns = [c.strip() for c in df.columns]

    # Ensure required columns exist
    for col in ["State name", "District Name", "PC name", "Winner Name",
                "Winner Party", "latitude", "longitude", "employees"]:
        if col not in df.columns:
            df[col] = np.nan

    # String normalisations
    df["State name"] = df["State name"].fillna("Unknown").str.strip()
    df["District Name"] = df["District Name"].fillna("Unknown").str.strip()
    df["PC name"] = df["PC name"].fillna("—").str.strip()
    df["Winner Name"] = df["Winner Name"].fillna("—").str.strip()
    df["Winner Party"] = df["Winner Party"].fillna("—").str.strip()
    df["District dominant party"] = df.get("District dominant party", pd.Series(["—"] * len(df))).fillna("—").str.strip()

    # Keys for joining
    df["_pc_key"] = df["PC name"].str.upper().str.strip()
    df["_district_key"] = df["District Name"].str.upper().str.strip()

    # Numeric
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["employees"] = pd.to_numeric(df["employees"], errors="coerce")

    return df


@st.cache_data(show_spinner=False)
def load_annexure() -> pd.DataFrame:
    """
    Load Annexure_with_3digit_Sheet1.csv.

    Row 0 = parent sector header (used as column names by pandas).
    Row 1 = sub-category labels (first data row is actually a sub-heading row — skip it).
    Row 2+ = actual district data.
    """
    path = os.path.join(DATA_DIR, "Annexure_with_3digit_Sheet1.csv")

    # Read with pandas — row 0 becomes header automatically; row 1 is the sub-header
    df = pd.read_csv(path, header=0, dtype=str)

    # Row 0 of the DataFrame is actually the sub-category row — drop it
    df = df.iloc[1:].reset_index(drop=True)

    # Normalise geo + identity cols
    df["State"] = df["State"].fillna("").str.strip()
    df["District"] = df["District"].fillna("").str.strip()
    df["Latitude"] = pd.to_numeric(df.get("Latitude", np.nan), errors="coerce")
    df["Longitude"] = pd.to_numeric(df.get("Longitude", np.nan), errors="coerce")

    # Keys for joining
    df["_state_key"] = df["State"].str.upper().str.strip()
    df["_district_key"] = df["District"].str.upper().str.strip()

    # Convert all industry columns to numeric
    id_cols = {"State", "District", "Latitude", "Longitude", "_state_key", "_district_key"}
    industry_cols = [c for c in df.columns if c not in id_cols]
    for col in industry_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


@st.cache_data(show_spinner=False)
def load_elections() -> pd.DataFrame:
    """
    Load Lok_Sabha_Elections_Winners_2024.xlsx.
    Combines NDA and BJP sheets, deduplicates on PC Name.
    """
    path = os.path.join(DATA_DIR, "Lok_Sabha_Elections_Winners_2024.xlsx")
    sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")

    frames = []
    for sheet_name, sdf in sheets.items():
        # Only process NDA and BJP sheets
        if sheet_name.strip() not in ("NDA", "BJP"):
            continue
        sdf = sdf.copy()
        sdf.columns = [str(c).strip() for c in sdf.columns]
        frames.append(sdf)

    if not frames:
        # Fallback: use all sheets
        frames = [sdf for sdf in sheets.values()]

    df = pd.concat(frames, ignore_index=True)

    # Standardise column names
    rename_map = {}
    for col in df.columns:
        col_lower = col.lower()
        if "state" in col_lower and "pc" not in col_lower:
            rename_map[col] = "State"
        elif "pc name" in col_lower or col_lower == "pc name":
            rename_map[col] = "PC Name"
        elif "winning candidate" in col_lower or "winning cand" in col_lower:
            rename_map[col] = "Winning Candidate"
        elif "winning party" in col_lower:
            rename_map[col] = "Winning Party"
        elif "runner" in col_lower and "party" not in col_lower:
            rename_map[col] = "Runner-up Candidate"
        elif "runner" in col_lower and "party" in col_lower:
            rename_map[col] = "Runner-up Party"
        elif "margin" in col_lower:
            rename_map[col] = "Margin Votes"
    df = df.rename(columns=rename_map)

    # Ensure required columns
    for col in ["State", "PC Name", "Winning Candidate", "Winning Party",
                "Runner-up Candidate", "Runner-up Party", "Margin Votes"]:
        if col not in df.columns:
            df[col] = np.nan

    df["PC Name"] = df["PC Name"].fillna("").str.strip()
    df["Winning Party"] = df["Winning Party"].fillna("—").str.strip()
    df["Winning Candidate"] = df["Winning Candidate"].fillna("—").str.strip()
    df["Margin Votes"] = pd.to_numeric(df["Margin Votes"], errors="coerce")

    # Dedup on PC Name
    df["_pc_key"] = df["PC Name"].str.upper().str.strip()
    df = df.drop_duplicates(subset="_pc_key", keep="first").reset_index(drop=True)

    return df


@st.cache_data(show_spinner=False)
def get_sector_mapping(annexure_df: pd.DataFrame) -> dict:
    """
    Return a dict of {parent_sector_name: [list_of_column_names]} for Annexure.
    Parent sector is derived by stripping '.N' suffixes from column names.
    """
    id_cols = {"State", "District", "Latitude", "Longitude", "_state_key", "_district_key"}
    industry_cols = [c for c in annexure_df.columns if c not in id_cols]

    mapping: dict[str, list] = {}
    for col in industry_cols:
        parent = _derive_parent_sector(col)
        mapping.setdefault(parent, []).append(col)
    return mapping


@st.cache_data(show_spinner=False)
def build_sector_totals(annexure_df: pd.DataFrame, state_filter: str = "India",
                        district_filter: str = "All Districts") -> pd.DataFrame:
    """
    Return a DataFrame of {Sector, Total} aggregated from Annexure, filtered to selection.
    """
    df = annexure_df.copy()

    if state_filter and state_filter != "India":
        # Match state loosely
        mask = df["State"].str.upper().str.strip() == state_filter.upper().strip()
        df = df[mask]

    if district_filter and district_filter != "All Districts":
        mask = df["District"].str.upper().str.strip() == district_filter.upper().strip()
        df = df[mask]

    sector_map = get_sector_mapping(annexure_df)
    rows = []
    for sector, cols in sector_map.items():
        valid_cols = [c for c in cols if c in df.columns]
        total = int(df[valid_cols].sum().sum()) if valid_cols else 0
        rows.append({"Sector": sector, "Total": total})

    result = pd.DataFrame(rows).sort_values("Total", ascending=False).reset_index(drop=True)
    grand_total = result["Total"].sum()
    result["Pct"] = (result["Total"] / grand_total * 100).round(1) if grand_total > 0 else 0.0
    return result


@st.cache_data(show_spinner=False)
def build_sector_breakdown(annexure_df: pd.DataFrame, sector: str,
                           state_filter: str = "India") -> pd.DataFrame:
    """
    For a given sector, return unit counts by state (or district if a state is selected).
    """
    sector_map = get_sector_mapping(annexure_df)
    cols = sector_map.get(sector, [])
    valid_cols = [c for c in cols if c in annexure_df.columns]

    df = annexure_df.copy()
    df["_sector_total"] = df[valid_cols].sum(axis=1) if valid_cols else 0

    if state_filter and state_filter != "India":
        mask = df["State"].str.upper().str.strip() == state_filter.upper().strip()
        df = df[mask]
        group_col = "District"
        label_col = "District"
    else:
        group_col = "State"
        label_col = "State"

    result = (
        df.groupby(group_col)["_sector_total"]
        .sum()
        .reset_index()
        .rename(columns={group_col: label_col, "_sector_total": "Total"})
        .sort_values("Total", ascending=False)
        .head(15)
        .reset_index(drop=True)
    )
    return result, label_col


def haversine_vectorized(lat1: float, lon1: float,
                         lat_arr: np.ndarray, lon_arr: np.ndarray) -> np.ndarray:
    """
    Vectorized Haversine distance (km) from a single point to an array of points.
    """
    R = 6371.0
    lat1_r = np.radians(lat1)
    lat2_r = np.radians(lat_arr)
    dlat = lat2_r - lat1_r
    dlon = np.radians(lon_arr) - np.radians(lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))
