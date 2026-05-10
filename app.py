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

# ── CSS Theme Token Injection ─────────────────────────────────────────────────
st.markdown("""
<style>
  :root {
    --bg-primary:        #f5f5f5;
    --bg-secondary:      #ffffff;
    --bg-card:           #eeeeee;
    --text-primary:      #1a1a2e;
    --text-secondary:    #444444;
    --text-muted:        #777777;
    --border-color:      rgba(0,0,0,0.12);
    --accent:            #0077b6;
    --accent-glow:       rgba(0, 119, 182, 0.2);
    --kpi-number:        #0077b6;
    --shadow:            0 2px 8px rgba(0,0,0,0.1);
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg-primary:      #0d1117;
      --bg-secondary:    #161b22;
      --bg-card:         #1c2230;
      --text-primary:    #e6edf3;
      --text-secondary:  #c9d1d9;
      --text-muted:      #8b949e;
      --border-color:    rgba(255,255,255,0.08);
      --accent:          #00b4d8;
      --accent-glow:     rgba(0, 180, 216, 0.15);
      --kpi-number:      #00b4d8;
      --shadow:          0 2px 8px rgba(0,0,0,0.5);
    }
  }

  /* Global overrides */
  .block-container { padding-top: 1rem !important; }

  /* KPI cards */
  .kpi-row { display: flex; gap: 16px; margin-bottom: 1.2rem; }
  .kpi-card {
    flex: 1;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 18px 24px;
    box-shadow: var(--shadow);
    text-align: center;
  }
  .kpi-label {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 6px;
  }
  .kpi-value {
    font-size: 32px;
    font-weight: 700;
    color: var(--kpi-number);
    line-height: 1;
  }

  /* Party card */
  .party-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    box-shadow: var(--shadow);
  }
  .party-name { font-size: 14px; font-weight: 700; margin-bottom: 4px; }
  .party-stats { font-size: 12px; color: var(--text-muted); }
  .party-bar-bg {
    background: var(--border-color);
    border-radius: 4px;
    height: 6px;
    margin-top: 6px;
    overflow: hidden;
  }
  .party-bar-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }

  /* PC card */
  .pc-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 10px 16px;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: var(--shadow);
  }
  .pc-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
  .pc-party { font-size: 12px; font-weight: 600; }
  .pc-count { font-size: 22px; font-weight: 700; color: var(--kpi-number); }

  /* Sector bar */
  .sector-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
  }
  .sector-label { font-size: 12px; color: var(--text-secondary); min-width: 200px; }
  .sector-bar-bg {
    flex: 1;
    background: var(--border-color);
    border-radius: 4px;
    height: 10px;
    overflow: hidden;
  }
  .sector-bar-fill { height: 100%; border-radius: 4px; }
  .sector-count { font-size: 12px; color: var(--text-muted); min-width: 80px; text-align: right; }
  .sector-pct { font-size: 11px; color: var(--text-muted); min-width: 45px; text-align: right; }

  /* Placeholder */
  .placeholder-box {
    background: var(--bg-card);
    border: 2px dashed var(--border-color);
    border-radius: 10px;
    padding: 60px 30px;
    text-align: center;
    color: var(--text-muted);
    font-size: 14px;
  }
</style>
""", unsafe_allow_html=True)


# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Loading data…"):
    units_df = load_units()
    annexure_df = load_annexure()
    elections_df = load_elections()


# ── Sidebar filters ───────────────────────────────────────────────────────────
state_filter, district_filter, radius_enabled, radius_km, district_centroid = render_sidebar(
    units_df, annexure_df
)

# Apply filters
filtered_df = apply_filters(
    units_df, state_filter, district_filter,
    radius_enabled, radius_km, district_centroid
)


# ── App Title ─────────────────────────────────────────────────────────────────
st.markdown("## 🏭 India Industrial Unit Explorer")
subtitle = f"**{state_filter}**"
if district_filter != "All Districts":
    subtitle += f" › {district_filter}"
if radius_enabled and district_centroid:
    subtitle += f" (within {radius_km} km)"
st.caption(subtitle)


# ── KPI Bar ───────────────────────────────────────────────────────────────────
n_districts = filtered_df["District Name"].nunique()
n_pcs = filtered_df["PC name"].nunique()
n_units = len(filtered_df)

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-label">Districts</div>
    <div class="kpi-value">{n_districts:,}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">PCs</div>
    <div class="kpi-value">{n_pcs:,}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Total Units</div>
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

    # Aggregate to district level
    if filtered_df.empty:
        st.info("No units match the current filters.")
    else:
        # Build district aggregation
        dist_agg = (
            filtered_df.groupby("District Name")
            .agg(
                count=("unit_id", "count") if "unit_id" in filtered_df.columns
                      else ("District Name", "count"),
                lat=("latitude", "mean"),
                lon=("longitude", "mean"),
                state=("State name", "first"),
                pc_name=("PC name", "first"),
                winner_name=("Winner Name", "first"),
                winner_party=("Winner Party", "first"),
            )
            .reset_index()
        )

        # Merge margin votes from elections
        elec_lookup = elections_df[["_pc_key", "Margin Votes"]].copy()
        dist_agg["_pc_key"] = dist_agg["pc_name"].str.upper().str.strip()
        dist_agg = dist_agg.merge(elec_lookup, on="_pc_key", how="left")
        dist_agg["Margin Votes"] = dist_agg["Margin Votes"].fillna(np.nan)

        # Map center
        if district_centroid:
            map_center = [district_centroid[0], district_centroid[1]]
            map_zoom = 9
        elif state_filter != "India":
            mask = units_df["State name"] == state_filter
            clat = units_df.loc[mask, "latitude"].median()
            clon = units_df.loc[mask, "longitude"].median()
            map_center = [clat if pd.notna(clat) else 20.5937,
                          clon if pd.notna(clon) else 78.9629]
            map_zoom = 7
        else:
            map_center = [20.5937, 78.9629]
            map_zoom = 5

        m = folium.Map(
            location=map_center,
            zoom_start=map_zoom,
            tiles=None,
        )

        # Dark tile layer (default)
        folium.TileLayer(
            tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
            attr='&copy; <a href="https://carto.com/">CARTO</a>',
            name="CartoDB dark_matter",
            show=True,
        ).add_to(m)

        # Light tile layer
        folium.TileLayer(
            tiles="OpenStreetMap",
            name="OpenStreetMap",
            show=False,
        ).add_to(m)

        # Plot circles
        for _, row in dist_agg.iterrows():
            if pd.isna(row["lat"]) or pd.isna(row["lon"]):
                continue
            count = int(row["count"])
            color = _get_map_color(count)
            radius = min(5 + count / 80, 40)

            margin_str = (
                f"{int(row['Margin Votes']):,}"
                if pd.notna(row.get("Margin Votes")) else "—"
            )
            popup_html = f"""
            <div style="min-width:200px;font-family:sans-serif;font-size:13px;">
              <b style="font-size:15px;">{row['District Name']}</b><br>
              <span style="color:#888;">State:</span> {row['state']}<br>
              <span style="color:#888;">Units:</span> <b>{count:,}</b><br>
              <span style="color:#888;">PC:</span> {row['pc_name']}<br>
              <span style="color:#888;">Winner:</span> {row['winner_name']}<br>
              <span style="color:#888;">Party:</span> {row['winner_party']}<br>
              <span style="color:#888;">Margin:</span> {margin_str}
            </div>
            """
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=radius,
                color="rgba(255,255,255,0.3)",
                weight=1,
                fill=True,
                fill_color=color,
                fill_opacity=0.75,
                opacity=0.9,
                popup=folium.Popup(popup_html, max_width=280),
                tooltip=f"{row['District Name']}: {count:,} units",
            ).add_to(m)

        folium.LayerControl(position="topright").add_to(m)

        # Legend
        legend_html = """
        {% macro html(this, kwargs) %}
        <div style="
          position: fixed; bottom: 30px; right: 10px; z-index: 1000;
          background: rgba(20,27,40,0.88);
          color: #e6edf3;
          border: 1px solid rgba(255,255,255,0.15);
          border-radius: 8px;
          padding: 12px 16px;
          font-size: 12px;
          font-family: sans-serif;
          min-width: 160px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.5);
        ">
          <b style="font-size:13px;letter-spacing:0.05em;">UNITS COUNT</b><br><br>
          <span style="color:#FF4500;font-size:18px;">●</span>&nbsp; 500+ units<br>
          <span style="color:#FFD700;font-size:18px;">●</span>&nbsp; 100–500 units<br>
          <span style="color:#39FF14;font-size:18px;">●</span>&nbsp; 20–100 units<br>
          <span style="color:#00BCD4;font-size:18px;">●</span>&nbsp; &lt;20 units
        </div>
        {% endmacro %}
        """
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
        # Merge margin votes
        elec_merge = elections_df[["_pc_key", "Margin Votes"]].copy()
        table_df = filtered_df.copy()
        table_df["_pc_key_lower"] = table_df["PC name"].str.upper().str.strip()
        table_df = table_df.merge(
            elec_merge.rename(columns={"_pc_key": "_pc_key_lower"}),
            on="_pc_key_lower", how="left"
        )

        grouped = (
            table_df.groupby("District Name")
            .agg(
                **{
                    "State name": ("State name", "first"),
                    "Total Units": ("District Name", "count"),
                    "PC name": ("PC name", "first"),
                    "Winner Name": ("Winner Name", "first"),
                    "Winner Party": ("Winner Party", "first"),
                    "Margin Votes": ("Margin Votes", "first"),
                }
            )
            .reset_index()
            .sort_values("Total Units", ascending=False)
        )

        grouped["Margin Votes"] = grouped["Margin Votes"].apply(
            lambda v: f"{int(v):,}" if pd.notna(v) else "—"
        )

        display_cols = ["State name", "District Name", "Total Units",
                        "PC name", "Winner Name", "Winner Party", "Margin Votes"]
        st.dataframe(
            grouped[display_cols].reset_index(drop=True),
            use_container_width=True,
            height=500,
        )

        # Download button
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

        # ── Left: Party-wise industrial strength ──────────────────────────────
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
                color = get_party_color(party)
                pct_width = int(row["total_units"] / max_units * 100)
                st.markdown(f"""
                <div class="party-card">
                  <div class="party-name" style="color:{color};">{party}</div>
                  <div class="party-stats">
                    {int(row['total_units']):,} units &nbsp;|&nbsp;
                    {int(row['constituencies'])} constituencies &nbsp;|&nbsp;
                    Avg: {row['avg_units']:.1f}
                  </div>
                  <div class="party-bar-bg">
                    <div class="party-bar-fill"
                         style="width:{pct_width}%;background:{color};"></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        # ── Right: Top 10 PC Constituencies ───────────────────────────────────
        with col_right:
            st.markdown("#### 🏆 Top PC Constituencies by Industrial Units")

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
    sector_totals = build_sector_totals(annexure_df, state_filter, district_filter)

    if sector_totals.empty or sector_totals["Total"].sum() == 0:
        st.info("No industry data available for the selected filters.")
    else:
        col_left, col_right = st.columns([1, 1], gap="large")

        with col_left:
            st.markdown("#### 🏭 All Industry Sectors (Ranked)")

            # Sector selectbox
            sector_names = sector_totals["Sector"].tolist()
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
                  <div class="sector-label" title="{row['Sector']}">{row['Sector'][:35]}{'…' if len(row['Sector'])>35 else ''}</div>
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
                st.markdown("""
                <div class="placeholder-box">
                  📌 Select a specific Industry Sector<br>to see state-wise distribution here
                </div>
                """, unsafe_allow_html=True)
            else:
                breakdown_df, label_col = build_sector_breakdown(
                    annexure_df, selected_sector, state_filter
                )
                if breakdown_df.empty or breakdown_df["Total"].sum() == 0:
                    st.info("No data available for this sector and selection.")
                else:
                    chart_title = (
                        f"Top {'Districts' if state_filter != 'India' else 'States'} — {selected_sector}"
                    )
                    fig = make_sector_bar_chart(
                        breakdown_df,
                        x_col="Total",
                        y_col=label_col,
                        title=chart_title,
                        sector_name=selected_sector,
                    )
                    st.plotly_chart(fig, use_container_width=True)
