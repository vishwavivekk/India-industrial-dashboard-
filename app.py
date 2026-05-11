"""
app.py — India Industrial Unit Explorer
Main Streamlit entry point.
"""
import io
import numpy as np
import pandas as pd
import streamlit as st
import folium
from folium import plugins
from streamlit_folium import st_folium
import branca

from utils.data_loader import (
    load_units, load_annexure, load_elections,
    build_sector_totals, build_sector_breakdown,
)
from utils.filters import render_sidebar, apply_filters
from utils.charts import (
    PARTY_COLORS, SECTOR_COLORS, get_party_color,
    make_sector_bar_chart,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="India Industrial Unit Explorer",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS — Light-mode only theme ───────────────────────────────────────────────
st.markdown("""
<style>
  /* Force light mode variables regardless of OS preference */
  :root {
    --bg-primary:        #f0f2f5;
    --bg-secondary:      #ffffff;
    --bg-card:           #ffffff;
    --bg-sidebar:        #f7f8fa;
    --text-primary:      #1a1a2e;
    --text-secondary:    #3d3d5c;
    --text-muted:        #888aa0;
    --border-color:      #e2e5ed;
    --accent:            #009688;
    --accent-light:      #e0f2f1;
    --kpi-number:        #009688;
    --shadow:            0 1px 6px rgba(0,0,0,0.08);
    --shadow-hover:      0 4px 16px rgba(0,150,136,0.15);
    --filter-label:      #555770;
    --btn-bg:            #009688;
    --btn-text:          #ffffff;
    --input-bg:          #ffffff;
    --input-border:      #ced2db;
  }

  /* Hide Streamlit top header bar (black bar with Share / git icons) */
  [data-testid="stHeader"],
  [data-testid="stToolbar"],
  #MainMenu,
  header[data-testid="stHeader"],
  .stDeployButton,
  footer { visibility: hidden !important; height: 0 !important; }

  /* Override Streamlit dark backgrounds */
  .stApp, .stApp > div, [data-testid="stAppViewContainer"] {
    background-color: #f0f2f5 !important;
  }
  [data-testid="stSidebar"] {
    background-color: #f7f8fa !important;
    border-right: 1px solid #e2e5ed !important;
  }
  [data-testid="stSidebar"] * {
    color: #1a1a2e !important;
  }
  .block-container {
    padding-top: 1.2rem !important;
    background-color: #f0f2f5 !important;
  }

  /* Sidebar filter headings */
  .filter-heading {
    font-size: 18px;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .filter-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--filter-label);
    margin-bottom: 4px;
    margin-top: 14px;
  }
  .filter-divider {
    height: 1px;
    background: #e2e5ed;
    margin: 20px 0;
  }

  /* Streamlit select boxes — light */
  [data-testid="stSelectbox"] > div > div {
    background: #ffffff !important;
    border: 1px solid #ced2db !important;
    border-radius: 8px !important;
    color: #1a1a2e !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
  }
  [data-testid="stSelectbox"] label {
    color: #555770 !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
  }

  /* Streamlit checkboxes & sliders */
  [data-testid="stCheckbox"] label { color: #1a1a2e !important; }
  [data-testid="stSlider"] label   { color: #1a1a2e !important; }

  /* Buttons */
  .stButton > button {
    background: var(--btn-bg) !important;
    color: var(--btn-text) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 8px 20px !important;
    transition: all 0.2s !important;
  }
  .stButton > button:hover {
    background: #00796b !important;
    box-shadow: 0 4px 12px rgba(0,150,136,0.3) !important;
    transform: translateY(-1px) !important;
  }

  /* Download button */
  [data-testid="stDownloadButton"] > button {
    background: #f0f2f5 !important;
    color: #009688 !important;
    border: 1.5px solid #009688 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
  }

  /* Tabs */
  [data-testid="stTabs"] [role="tab"] {
    color: #555770 !important;
    font-weight: 600 !important;
  }
  [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #009688 !important;
    border-bottom-color: #009688 !important;
  }

  /* ── KPI Cards ─────────────────────────────────────────────────── */
  .kpi-row {
    display: flex;
    gap: 14px;
    margin-bottom: 1.4rem;
  }
  .kpi-card {
    flex: 1;
    background: #ffffff;
    border: 1px solid #e2e5ed;
    border-radius: 12px;
    padding: 20px 24px 18px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.07);
    text-align: center;
    position: relative;
    overflow: hidden;
  }
  .kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: #009688;
    border-radius: 12px 12px 0 0;
  }
  .kpi-icon {
    font-size: 20px;
    margin-bottom: 4px;
    display: block;
  }
  .kpi-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #888aa0;
    margin-bottom: 6px;
  }
  .kpi-value {
    font-size: 34px;
    font-weight: 800;
    color: #009688;
    line-height: 1;
  }

  /* ── Party card ─────────────────────────────────────────────────── */
  .party-card {
    background: #ffffff;
    border: 1px solid #e2e5ed;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }
  .party-name  { font-size: 14px; font-weight: 700; margin-bottom: 4px; }
  .party-stats { font-size: 12px; color: #888aa0; }
  .party-bar-bg {
    background: #f0f2f5;
    border-radius: 4px;
    height: 6px;
    margin-top: 6px;
    overflow: hidden;
  }
  .party-bar-fill { height: 100%; border-radius: 4px; transition: width 0.4s; }

  /* ── PC card ────────────────────────────────────────────────────── */
  .pc-card {
    background: #ffffff;
    border: 1px solid #e2e5ed;
    border-radius: 10px;
    padding: 10px 16px;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
  }
  .pc-card:hover { box-shadow: 0 4px 12px rgba(0,150,136,0.12); }
  .pc-name  { font-size: 14px; font-weight: 600; color: #1a1a2e; }
  .pc-party { font-size: 12px; font-weight: 600; }
  .pc-count { font-size: 24px; font-weight: 800; color: #009688; }

  /* ── Sector rows ────────────────────────────────────────────────── */
  .sector-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 7px;
  }
  .sector-label  { font-size: 12px; color: #3d3d5c; min-width: 200px; }
  .sector-bar-bg {
    flex: 1;
    background: #f0f2f5;
    border-radius: 4px;
    height: 10px;
    overflow: hidden;
  }
  .sector-bar-fill { height: 100%; border-radius: 4px; }
  .sector-count { font-size: 12px; color: #888aa0; min-width: 80px; text-align: right; }
  .sector-pct   { font-size: 11px; color: #888aa0; min-width: 45px; text-align: right; }

  /* ── Placeholder ────────────────────────────────────────────────── */
  .placeholder-box {
    background: #f7f8fa;
    border: 2px dashed #e2e5ed;
    border-radius: 12px;
    padding: 60px 30px;
    text-align: center;
    color: #888aa0;
    font-size: 14px;
  }

  /* App title */
  .app-title {
    font-size: 26px;
    font-weight: 800;
    color: #1a1a2e;
    margin-bottom: 2px;
  }
  .app-subtitle {
    font-size: 13px;
    color: #888aa0;
    margin-bottom: 1.2rem;
  }
</style>
""", unsafe_allow_html=True)


# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Loading data…"):
    units_df    = load_units()
    annexure_df = load_annexure()
    elections_df = load_elections()


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — Filters
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="filter-heading">🔍 Filters</div>', unsafe_allow_html=True)

    # ── State ──────────────────────────────────────────────────────────────────
    st.markdown('<div class="filter-label">State</div>', unsafe_allow_html=True)
    state_options = ["All States"] + sorted(units_df["State name"].dropna().unique().tolist())
    state_filter = st.selectbox(
        "State",
        state_options,
        label_visibility="collapsed",
        key="sel_state",
    )

    # ── Principal Constituency ─────────────────────────────────────────────────
    st.markdown('<div class="filter-label">Principal Constituency</div>', unsafe_allow_html=True)
    _pc_mask = pd.Series([True] * len(units_df))
    if state_filter != "All States":
        _pc_mask &= units_df["State name"] == state_filter
    pc_options = ["All PCs"] + sorted(
        units_df.loc[_pc_mask, "PC name"].dropna().unique().tolist()
    )
    pc_filter = st.selectbox(
        "Principal Constituency",
        pc_options,
        label_visibility="collapsed",
        key="sel_pc",
    )

    # ── Winning Party ──────────────────────────────────────────────────────────
    st.markdown('<div class="filter-label">Winning Party</div>', unsafe_allow_html=True)
    _party_mask = pd.Series([True] * len(units_df))
    if state_filter != "All States":
        _party_mask &= units_df["State name"] == state_filter
    if pc_filter != "All PCs":
        _party_mask &= units_df["PC name"] == pc_filter
    party_options = ["All Parties"] + sorted(
        units_df.loc[_party_mask, "Winner Party"].dropna().unique().tolist()
    )
    party_filter = st.selectbox(
        "Winning Party",
        party_options,
        label_visibility="collapsed",
        key="sel_party",
    )

    st.markdown('<div class="filter-divider"></div>', unsafe_allow_html=True)
    st.caption("Data: Elections 2024")


# ── Apply filters ─────────────────────────────────────────────────────────────
def apply_all_filters(df, state_f, pc_f, party_f):
    out = df.copy()
    if state_f != "All States":
        out = out[out["State name"] == state_f]
    if pc_f != "All PCs":
        out = out[out["PC name"] == pc_f]
    if party_f != "All Parties":
        out = out[out["Winner Party"] == party_f]
    return out

filtered_df = apply_all_filters(units_df, state_filter, pc_filter, party_filter)


# ── App Title ─────────────────────────────────────────────────────────────────
st.markdown('<div class="app-title">🏭 India Industrial Unit Explorer</div>', unsafe_allow_html=True)

breadcrumb_parts = []
if state_filter != "All States":
    breadcrumb_parts.append(f"**{state_filter}**")
if pc_filter != "All PCs":
    breadcrumb_parts.append(pc_filter)
if party_filter != "All Parties":
    breadcrumb_parts.append(party_filter)

subtitle_text = " › ".join(breadcrumb_parts) if breadcrumb_parts else "All India"
st.markdown(f'<div class="app-subtitle">{subtitle_text}</div>', unsafe_allow_html=True)


# ── KPI Bar — order: States · Districts · Principal Constituencies · Units ────
n_states = filtered_df["State name"].nunique()
n_pcs   = filtered_df["PC name"].nunique()
n_units = len(filtered_df)

# Context-aware unit label
if pc_filter != "All PCs":
    unit_label = "Industrial Units (PC)"
elif state_filter != "All States":
    unit_label = "Industrial Units (State)"
else:
    unit_label = "Industrial Units"

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card">
    <span class="kpi-icon">🏛️</span>
    <div class="kpi-label">States</div>
    <div class="kpi-value">{n_states:,}</div>
  </div>
  <div class="kpi-card">
    <span class="kpi-icon">🗳️</span>
    <div class="kpi-label">Principal Constituencies</div>
    <div class="kpi-value">{n_pcs:,}</div>
  </div>
  <div class="kpi-card">
    <span class="kpi-icon">🏭</span>
    <div class="kpi-label">{unit_label}</div>
    <div class="kpi-value">{n_units:,}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_map, tab_table, tab_pc, tab_industry = st.tabs([
    "🗺️ Interactive Map",
    "📊 Data Table",
    "🏛️ PC Analysis",
    "🏭 Industry Summary",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Interactive Map
# ═══════════════════════════════════════════════════════════════════════════════
with tab_map:

    def _get_map_color(count: int) -> str:
        if count >= 500:
            return "#FF4500"
        elif count >= 100:
            return "#FFD700"
        elif count >= 20:
            return "#39FF14"
        else:
            return "#00BCD4"

    if filtered_df.empty:
        st.info("No units match the current filters.")
    else:
        # Determine aggregation level
        if pc_filter != "All PCs":
            group_col  = "PC name"
            agg_kwargs = dict(
                count=("PC name", "count"),
                lat=("latitude", "mean"),
                lon=("longitude", "mean"),
                state=("State name", "first"),
                district=("District Name", "first"),
                winner_name=("Winner Name", "first"),
                winner_party=("Winner Party", "first"),
            )
            label_col = "PC name"
        else:
            group_col  = "District Name"
            agg_kwargs = dict(
                count=("District Name", "count"),
                lat=("latitude", "mean"),
                lon=("longitude", "mean"),
                state=("State name", "first"),
                pc_name=("PC name", "first"),
                winner_name=("Winner Name", "first"),
                winner_party=("Winner Party", "first"),
            )
            label_col = "District Name"

        agg_df = (
            filtered_df.groupby(group_col)
            .agg(**agg_kwargs)
            .reset_index()
        )

        # Merge margin votes
        elec_lookup = elections_df[["_pc_key", "Margin Votes"]].copy()
        _pc_ref = "PC name" if "pc_name" not in agg_df.columns else "pc_name"
        if _pc_ref == "PC name" and "PC name" in agg_df.columns:
            agg_df["_pc_key"] = agg_df["PC name"].str.upper().str.strip()
        elif "pc_name" in agg_df.columns:
            agg_df["_pc_key"] = agg_df["pc_name"].str.upper().str.strip()
        agg_df = agg_df.merge(elec_lookup, on="_pc_key", how="left")
        agg_df["Margin Votes"] = agg_df["Margin Votes"].fillna(np.nan)

        # Map center
        if state_filter != "All States":
            mask = units_df["State name"] == state_filter
            clat = units_df.loc[mask, "latitude"].median()
            clon = units_df.loc[mask, "longitude"].median()
            map_center = [
                clat if pd.notna(clat) else 20.5937,
                clon if pd.notna(clon) else 78.9629,
            ]
            map_zoom = 7
        else:
            map_center = [20.5937, 78.9629]
            map_zoom   = 5

        # OpenStreetMap ONLY
        m = folium.Map(
            location=map_center,
            zoom_start=map_zoom,
            tiles="OpenStreetMap",
        )

        for _, row in agg_df.iterrows():
            if pd.isna(row["lat"]) or pd.isna(row["lon"]):
                continue
            count  = int(row["count"])
            color  = _get_map_color(count)
            radius = min(5 + count / 80, 40)

            margin_str = (
                f"{int(row['Margin Votes']):,}"
                if pd.notna(row.get("Margin Votes")) else "—"
            )
            name_val    = row.get("PC name") or row.get("District Name", "")
            pc_val      = row.get("pc_name", row.get("PC name", "—"))
            district_val = row.get("district", row.get("District Name", "—"))

            popup_html = f"""
            <div style="min-width:210px;font-family:'Segoe UI',sans-serif;font-size:13px;
                        color:#1a1a2e;line-height:1.6;">
              <b style="font-size:15px;color:#009688;">{name_val}</b><br>
              <span style="color:#888aa0;">State:</span> {row['state']}<br>
              <span style="color:#888aa0;">District:</span> {district_val}<br>
              <span style="color:#888aa0;">Units:</span> <b>{count:,}</b><br>
              <span style="color:#888aa0;">Principal Constituency:</span> {pc_val}<br>
              <span style="color:#888aa0;">Winner:</span> {row['winner_name']}<br>
              <span style="color:#888aa0;">Party:</span> {row['winner_party']}<br>
              <span style="color:#888aa0;">Margin:</span> {margin_str}
            </div>
            """
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=radius,
                color="rgba(0,0,0,0.2)",
                weight=1,
                fill=True,
                fill_color=color,
                fill_opacity=0.78,
                opacity=0.95,
                popup=folium.Popup(popup_html, max_width=290),
                tooltip=f"{name_val}: {count:,} units",
            ).add_to(m)

        # Context-aware legend label
        if pc_filter != "All PCs":
            legend_title = "UNITS COUNT (PC VIEW)"
        elif state_filter != "All States":
            legend_title = "UNITS COUNT (STATE VIEW)"
        else:
            legend_title = "INDUSTRIAL UNITS COUNT"

        legend_html = """
        {{% macro html(this, kwargs) %}}
        <div style="
          position: fixed; bottom: 30px; right: 10px; z-index: 1000;
          background: rgba(255,255,255,0.96);
          color: #1a1a2e;
          border: 1px solid #e2e5ed;
          border-radius: 10px;
          padding: 14px 18px;
          font-size: 12px;
          font-family: 'Segoe UI', sans-serif;
          min-width: 180px;
          box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        ">
          <b style="font-size:12px;letter-spacing:0.06em;color:#555770;">{legend_title}</b><br><br>
          <span style="color:#FF4500;font-size:18px;">●</span>&nbsp; 500+ units<br>
          <span style="color:#FFD700;font-size:18px;">●</span>&nbsp; 100–500 units<br>
          <span style="color:#39FF14;font-size:18px;">●</span>&nbsp; 20–100 units<br>
          <span style="color:#00BCD4;font-size:18px;">●</span>&nbsp; &lt;20 units
        </div>
        {{% endmacro %}}
        """.format(legend_title=legend_title)

        legend = branca.element.MacroElement()
        legend._template = branca.element.Template(legend_html)
        m.get_root().add_child(legend)

        st_folium(m, height=600, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Data Table
# ═══════════════════════════════════════════════════════════════════════════════
with tab_table:
    if filtered_df.empty:
        st.info("No data for current selection.")
    else:
        elec_merge = elections_df[["_pc_key", "Margin Votes"]].copy()
        table_df = filtered_df.copy()
        table_df["_pc_key_lower"] = table_df["PC name"].str.upper().str.strip()
        table_df = table_df.merge(
            elec_merge.rename(columns={"_pc_key": "_pc_key_lower"}),
            on="_pc_key_lower", how="left"
        )

        grouped = (
            table_df.groupby("District Name")
            .agg(**{
                "State name":    ("State name",    "first"),
                "Total Units":   ("District Name", "count"),
                "PC name":       ("PC name",        "first"),
                "Winner Name":   ("Winner Name",    "first"),
                "Winner Party":  ("Winner Party",   "first"),
                "Margin Votes":  ("Margin Votes",   "first"),
            })
            .reset_index()
            .sort_values("Total Units", ascending=False)
        )
        grouped["Margin Votes"] = grouped["Margin Votes"].apply(
            lambda v: f"{int(v):,}" if pd.notna(v) else "—"
        )
        # Rename PC name → Principal Constituency in display
        grouped = grouped.rename(columns={"PC name": "Principal Constituency"})

        display_cols = [
            "State name", "District Name", "Total Units",
            "Principal Constituency", "Winner Name", "Winner Party", "Margin Votes"
        ]
        st.dataframe(
            grouped[display_cols].reset_index(drop=True),
            use_container_width=True,
            height=500,
        )

        csv_buf = io.StringIO()
        grouped[display_cols].to_csv(csv_buf, index=False)
        st.download_button(
            label="⬇️ Download CSV",
            data=csv_buf.getvalue().encode("utf-8"),
            file_name="india_industrial_districts.csv",
            mime="text/csv",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PC Analysis
# ═══════════════════════════════════════════════════════════════════════════════
with tab_pc:
    if filtered_df.empty:
        st.info("No data for current selection.")
    else:
        col_left, col_right = st.columns([1, 1], gap="large")

        with col_left:
            st.markdown("#### 🎖️ Party-wise Industrial Strength")

            party_agg = (
                filtered_df.groupby("Winner Party")
                .agg(
                    total_units=("Winner Party", "count"),
                    constituencies=("PC name", "nunique"),
                )
                .reset_index()
                .sort_values("total_units", ascending=False)
            )
            party_agg["avg_units"] = (
                party_agg["total_units"] / party_agg["constituencies"]
            ).round(1)

            max_units = party_agg["total_units"].max() if not party_agg.empty else 1

            for _, row in party_agg.iterrows():
                party = str(row["Winner Party"])
                if party in ("—", "nan", ""):
                    continue
                color     = get_party_color(party)
                pct_width = int(row["total_units"] / max_units * 100)
                st.markdown(f"""
                <div class="party-card">
                  <div class="party-name" style="color:{color};">{party}</div>
                  <div class="party-stats">
                    {int(row['total_units']):,} units &nbsp;|&nbsp;
                    {int(row['constituencies'])} principal constituencies &nbsp;|&nbsp;
                    Avg: {row['avg_units']:.1f}
                  </div>
                  <div class="party-bar-bg">
                    <div class="party-bar-fill"
                         style="width:{pct_width}%;background:{color};"></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        with col_right:
            st.markdown("#### 🏆 Top Principal Constituencies by Industrial Units")

            pc_agg = (
                filtered_df.groupby("PC name")
                .agg(
                    unit_count=("PC name", "count"),
                    winner_party=("Winner Party", "first"),
                    winner_name=("Winner Name", "first"),
                )
                .reset_index()
                .sort_values("unit_count", ascending=False)
                .head(10)
            )

            for rank, (_, row) in enumerate(pc_agg.iterrows(), 1):
                party = str(row["winner_party"])
                color = get_party_color(party)
                st.markdown(f"""
                <div class="pc-card">
                  <div>
                    <div class="pc-name">#{rank} {row['PC name']}</div>
                    <div class="pc-party" style="color:{color};">{party}</div>
                  </div>
                  <div class="pc-count">{int(row['unit_count']):,}</div>
                </div>
                """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Industry Summary
# ═══════════════════════════════════════════════════════════════════════════════
with tab_industry:
    sector_totals = build_sector_totals(annexure_df, state_filter, None)

    if sector_totals.empty or sector_totals["Total"].sum() == 0:
        st.info("No industry data available for the selected filters.")
    else:
        col_left, col_right = st.columns([1, 1], gap="large")

        with col_left:
            st.markdown("#### 🏭 All Industry Sectors (Ranked)")

            sector_names    = sector_totals["Sector"].tolist()
            selected_sector = st.selectbox(
                "Select a sector for drill-down →",
                ["— Select a sector —"] + sector_names,
                index=0,
            )

            max_total = sector_totals["Total"].max() if not sector_totals.empty else 1

            for i, (_, row) in enumerate(sector_totals.iterrows()):
                if row["Total"] == 0:
                    continue
                bar_color = SECTOR_COLORS[i % len(SECTOR_COLORS)]
                pct_width = int(row["Total"] / max_total * 100)
                st.markdown(f"""
                <div class="sector-row">
                  <div class="sector-label"
                       title="{row['Sector']}">{row['Sector'][:35]}{'…' if len(row['Sector'])>35 else ''}</div>
                  <div class="sector-bar-bg">
                    <div class="sector-bar-fill"
                         style="width:{pct_width}%;background:{bar_color};"></div>
                  </div>
                  <div class="sector-count">{int(row['Total']):,}</div>
                  <div class="sector-pct">{row['Pct']:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)

        with col_right:
            st.markdown("#### 📊 Industry Distribution")

            if selected_sector == "— Select a sector —":
                st.info("Select a sector on the left to see its distribution.")
            else:
                breakdown_df, label_col = build_sector_breakdown(
                    annexure_df, selected_sector, state_filter
                )
                if breakdown_df.empty or breakdown_df["Total"].sum() == 0:
                    st.info("No data available for this sector and selection.")
                else:
                    chart_title = (
                        f"Top {'States' if state_filter == 'All States' else 'Districts'}"
                        f" — {selected_sector}"
                    )
                    fig = make_sector_bar_chart(
                        breakdown_df,
                        x_col="Total",
                        y_col=label_col,
                        title=chart_title,
                        sector_name=selected_sector,
                    )
                    st.plotly_chart(fig, use_container_width=True)
