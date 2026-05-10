"""
charts.py — Reusable Plotly chart functions and color constants.
"""
import plotly.express as px
import plotly.graph_objects as go

# ── Party color map ──────────────────────────────────────────────────────────
PARTY_COLORS = {
    "Bharatiya Janata Party":                    "#FF6D00",
    "Indian National Congress":                  "#1565C0",
    "Samajwadi Party":                           "#D32F2F",
    "Trinamool Congress":                        "#00796B",
    "All India Trinamool Congress":              "#00796B",
    "Dravida Munnetra Kazhagam":                 "#F9A825",
    "Telugu Desam Party":                        "#7CB342",
    "Shiv Sena":                                 "#FFB300",
    "Janasena Party":                            "#1976D2",
    "Jana Sena Party":                           "#1976D2",
    "Janata Dal (Secular)":                      "#7B1FA2",
    "Janata Dal (United)":                       "#E64A19",
    "Yuvajana Sramika Rythu Congress Party":     "#AD1457",
    "Yuvajana Sramika Rythu Congress":           "#AD1457",
    "Aam Aadmi Party":                           "#0288D1",
    "Communist Party of India (Marxist)":        "#B71C1C",
    "Communist Party of India (M)":              "#B71C1C",
    "Nationalist Congress Party":                "#00838F",
    "Shiv Sena (Uddhav Balasaheb Thackeray)":   "#E65100",
    "Shiv Sena (UBT)":                          "#E65100",
    "Independent":                               "#78909C",
    "Others":                                    "#78909C",
}

FALLBACK_COLOR = "#78909C"

# 26 distinct sector colors for Industry Summary
SECTOR_COLORS = px.colors.qualitative.Alphabet


def get_party_color(party: str) -> str:
    """Return hex color for a party name, with fuzzy matching."""
    if not party or str(party).strip() in ("", "nan", "—"):
        return FALLBACK_COLOR
    party_str = str(party).strip()
    if party_str in PARTY_COLORS:
        return PARTY_COLORS[party_str]
    # fuzzy: check if any key is a substring
    for key, color in PARTY_COLORS.items():
        if key.lower() in party_str.lower() or party_str.lower() in key.lower():
            return color
    return FALLBACK_COLOR


def make_sector_bar_chart(df_sector, x_col: str, y_col: str, title: str, sector_name: str = None):
    """Horizontal bar chart for industry sector distribution."""
    color_map = {
        name: SECTOR_COLORS[i % len(SECTOR_COLORS)]
        for i, name in enumerate(sorted(df_sector[y_col].unique()))
    }
    colors = [color_map.get(name, FALLBACK_COLOR) for name in df_sector[y_col]]
    fig = go.Figure(go.Bar(
        x=df_sector[x_col],
        y=df_sector[y_col],
        orientation="h",
        marker_color=colors,
        text=df_sector[x_col].apply(lambda v: f"{int(v):,}"),
        textposition="outside",
        hovertemplate="%{y}: %{x:,}<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=title, font=dict(size=14, color="#e6edf3")),
        xaxis=dict(title="Unit Count", color="#8b949e", gridcolor="rgba(255,255,255,0.07)"),
        yaxis=dict(title="", color="#c9d1d9", autorange="reversed"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=60, t=50, b=30),
        height=420,
        showlegend=False,
    )
    return fig


def make_party_units_chart(party_df):
    """Horizontal bar chart for party-wise unit count."""
    party_df = party_df.sort_values("Total Units", ascending=True).tail(12)
    colors = [get_party_color(p) for p in party_df["Winner Party"]]
    fig = go.Figure(go.Bar(
        x=party_df["Total Units"],
        y=party_df["Winner Party"],
        orientation="h",
        marker_color=colors,
        text=party_df["Total Units"].apply(lambda v: f"{int(v):,}"),
        textposition="outside",
        hovertemplate="%{y}: %{x:,} units<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark",
        xaxis=dict(title="Total Units", color="#8b949e", gridcolor="rgba(255,255,255,0.07)"),
        yaxis=dict(title="", color="#c9d1d9"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=60, t=20, b=30),
        height=380,
        showlegend=False,
    )
    return fig
