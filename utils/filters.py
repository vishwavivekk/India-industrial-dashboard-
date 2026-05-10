"""
filters.py — Sidebar filter logic for India Industrial Dashboard.
"""
import numpy as np
import pandas as pd
import streamlit as st
from utils.data_loader import haversine_vectorized


def render_sidebar(units_df: pd.DataFrame, annexure_df: pd.DataFrame):
    """
    Render sidebar filters and return:
      (state_filter, district_filter, radius_enabled, radius_km, district_centroid)
    where district_centroid = (lat, lon) or None.
    """
    st.sidebar.markdown("## 🏭 India Industrial Explorer")
    st.sidebar.markdown("---")

    # ── State selector ───────────────────────────────────────────────────────
    states = sorted(units_df["State name"].dropna().unique().tolist())
    state_options = ["India"] + states
    state_filter = st.sidebar.selectbox("🗺️ Select State", state_options, index=0)

    # ── District selector ────────────────────────────────────────────────────
    if state_filter == "India":
        districts = sorted(units_df["District Name"].dropna().unique().tolist())
    else:
        districts = sorted(
            units_df.loc[units_df["State name"] == state_filter, "District Name"]
            .dropna().unique().tolist()
        )
    district_options = ["All Districts"] + districts
    district_filter = st.sidebar.selectbox("📍 Select District", district_options, index=0)

    # ── District centroid from Annexure ──────────────────────────────────────
    district_centroid = None
    if district_filter != "All Districts":
        mask = annexure_df["_district_key"] == district_filter.upper().strip()
        matched = annexure_df[mask]
        if not matched.empty:
            lat = matched["Latitude"].iloc[0]
            lon = matched["Longitude"].iloc[0]
            if pd.notna(lat) and pd.notna(lon):
                district_centroid = (float(lat), float(lon))

    # ── Radius filter ────────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📡 Radius Filter")
    radius_enabled = st.sidebar.checkbox("Enable Distance-Based Filter", value=False)
    radius_km = 100

    if radius_enabled:
        if district_filter == "All Districts" or state_filter == "India":
            st.sidebar.info("ℹ️ Please select a specific district to use the radius filter.")
        elif district_centroid is None:
            st.sidebar.warning("⚠️ No centroid data found for selected district.")
        else:
            radius_km = st.sidebar.slider(
                "Radius (km)", min_value=0, max_value=500,
                step=10, value=100,
            )
            st.sidebar.caption(
                f"Centre: {district_centroid[0]:.3f}°N, {district_centroid[1]:.3f}°E"
            )

    return state_filter, district_filter, radius_enabled, radius_km, district_centroid


def apply_filters(units_df: pd.DataFrame,
                  state_filter: str,
                  district_filter: str,
                  radius_enabled: bool,
                  radius_km: int,
                  district_centroid) -> pd.DataFrame:
    """Apply all active filters to the units DataFrame and return filtered copy."""
    df = units_df.copy()

    # State filter
    if state_filter != "India":
        df = df[df["State name"] == state_filter]

    # District filter
    if district_filter != "All Districts":
        df = df[df["District Name"] == district_filter]

    # Radius filter
    if (radius_enabled and district_centroid is not None
            and district_filter != "All Districts"):
        lat_arr = df["latitude"].to_numpy(dtype=float)
        lon_arr = df["longitude"].to_numpy(dtype=float)
        valid_mask = ~(np.isnan(lat_arr) | np.isnan(lon_arr))
        distances = np.full(len(df), np.inf)
        if valid_mask.any():
            distances[valid_mask] = haversine_vectorized(
                district_centroid[0], district_centroid[1],
                lat_arr[valid_mask], lon_arr[valid_mask],
            )
        df = df[distances <= radius_km]

    return df.reset_index(drop=True)
