"""
charts.py — Reusable Plotly chart functions and color constants.
"""
import plotly.express as px
import plotly.graph_objects as go

# ── Party color map ──────────────────────────────────────────────────────────
PARTY_COLORS = {
    "Bharatiya Janata Party":                    "#E65100",
    "Indian National Congress":                  "#1565C0",
    "Samajwadi Party":                           "#B71C1C",
    "Trinamool Congress":                        "#00695C",
    "All India Trinamool Congress":              "#00695C",
    "Dravida Munnetra Kazhagam":                 "#F57F17",
    "Telugu Desam Party":                        "#558B2F",
    "Shiv Sena":                                 "#E65100",
    "Janasena Party":                            "#1565C0",
    "Jana Sena Party":                           "#1565C0",
    "Janata Dal (Secular)":                      "#6A1B9A",
    "Janata Dal (United)":                       "#BF360C",
    "Yuvajana Sramika Rythu Congress Party":     "#880E4F",
    "Yuvajana Sramika Rythu Congress":           "#880E4F",
    "Aam Aadmi Party":                           "#0277BD",
    "Communist Party of India (Marxist)":        "#8B0000",
    "Communist Party of India (M)":              "#8B0000",
    "Nationalist Congress Party":                "#006064",
    "Shiv Sena (Uddhav Balasaheb Thackeray)":   "#BF360C",
    "Shiv Sena (UBT)":                          "#BF360C",
    "Independent":                               "#546E7A",
    "Others":                                    "#546E7A",
}

FALLBACK_COLOR = "#546E7A"

# 26 distinct sector colors — rich, dark, visible on light backgrounds
SECTOR_COLORS = [
    "#1A6FA8", "#C0392B", "#1E8449", "#D4900A",
    "#6C3483", "#117A65", "#A04000", "#1F618D",
    "#7D6608", "#4A235A", "#1B4F72", "#0E6655",
    "#6E2F1A", "#212F3D", "#784212", "#1A5276",
    "#512E5F", "#0B5345", "#784212", "#4D5656",
    "#1C2833", "#641E16", "#0E4D6A", "#145A32",
    "#4A235A", "#7B241C",
]


def get_party_color(party: str) -> str:
    """Return hex color for a party name, with fuzzy matching."""
    if not party or str(party).strip() in ("", "nan", "—"):
        return FALLBACK_COLOR
    party_str = str(party).strip()
    if party_str in PARTY_COLORS:
        return PARTY_COLORS[party_str]
    for key, color in PARTY_COLORS.items():
        if key.lower() in party_str.lower() or party_str.lower() in key.lower():
            return color
    return FALLBACK_COLOR


# ── Shared light layout defaults ─────────────────────────────────────────────
_LIGHT_LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor="#ffffff",
    plot_bgcolor="#f7f8fa",
    font=dict(
        family="'Segoe UI', Arial, sans-serif",
        color="#1a1a2e",
        size=12,
    ),
    hoverlabel=dict(
        bgcolor="#1a1a2e",
        font_color="#ffffff",
        font_size=12,
        bordercolor="#1a1a2e",
    ),
    showlegend=False,
)

_LIGHT_XAXIS = dict(
    color="#1a1a2e",
    tickfont=dict(color="#555770", size=11),
    title_font=dict(color="#555770", size=11),
    gridcolor="#e2e5ed",
    linecolor="#ced2db",
    zerolinecolor="#ced2db",
)

_LIGHT_YAXIS = dict(
    color="#1a1a2e",
    tickfont=dict(color="#1a1a2e", size=12),
    title_font=dict(color="#555770", size=11),
    linecolor="#ced2db",
    gridcolor="rgba(0,0,0,0)",
)


def make_sector_bar_chart(df_sector, x_col: str, y_col: str, title: str, sector_name: str = None):
    """Horizontal bar chart for industry sector distribution — light theme."""
    n = len(df_sector)
    colors = [SECTOR_COLORS[i % len(SECTOR_COLORS)] for i in range(n)]

    max_val = df_sector[x_col].max() if len(df_sector) > 0 else 1

    # Choose text position per bar: inside (white) for large bars, outside (dark) for small
    threshold = max_val * 0.25
    text_positions = [
        "inside" if v >= threshold else "outside"
        for v in df_sector[x_col]
    ]
    text_colors = [
        "#ffffff" if v >= threshold else "#1a1a2e"
        for v in df_sector[x_col]
    ]

    bars = []
    for i, (_, row) in enumerate(df_sector.iterrows()):
        val = row[x_col]
        bars.append(go.Bar(
            x=[val],
            y=[row[y_col]],
            orientation="h",
            marker_color=colors[i],
            marker_line_color="rgba(0,0,0,0.2)",
            marker_line_width=1,
            text=[f"{int(val):,}"],
            textposition="inside" if val >= threshold else "outside",
            textfont=dict(
                color="#ffffff" if val >= threshold else "#1a1a2e",
                size=11,
                family="'Segoe UI', Arial, sans-serif",
            ),
            hovertemplate=f"<b>{row[y_col]}</b><br>Units: {int(val):,}<extra></extra>",
            showlegend=False,
        ))

    fig = go.Figure(data=bars)

    fig.update_layout(
        **_LIGHT_LAYOUT,
        title=dict(
            text=title,
            font=dict(size=14, color="#1a1a2e", family="'Segoe UI', Arial, sans-serif"),
            x=0.01,
        ),
        xaxis=dict(
            title="Unit Count",
            range=[0, max_val * 1.15],  # 15% padding so outside labels never clip
            **_LIGHT_XAXIS,
        ),
        yaxis=dict(title="", autorange="reversed", **_LIGHT_YAXIS),
        barmode="overlay",
        margin=dict(l=10, r=20, t=50, b=30),
        height=max(380, n * 28),
    )
    return fig


def make_party_units_chart(party_df):
    """Horizontal bar chart for party-wise unit count — light theme."""
    party_df = party_df.sort_values("Total Units", ascending=True).tail(12)
    colors = [get_party_color(p) for p in party_df["Winner Party"]]

    fig = go.Figure(go.Bar(
        x=party_df["Total Units"],
        y=party_df["Winner Party"],
        orientation="h",
        marker_color=colors,
        marker_line_color="rgba(0,0,0,0.2)",
        marker_line_width=1,
        text=party_df["Total Units"].apply(lambda v: f"{int(v):,}"),
        textposition="outside",
        textfont=dict(color="#1a1a2e", size=11, family="'Segoe UI', Arial, sans-serif"),
        hovertemplate="<b>%{y}</b><br>Units: %{x:,}<extra></extra>",
    ))

    fig.update_layout(
        **_LIGHT_LAYOUT,
        xaxis=dict(title="Total Units", **_LIGHT_XAXIS),
        yaxis=dict(title="", **_LIGHT_YAXIS),
        margin=dict(l=10, r=70, t=20, b=30),
        height=380,
    )
    return fig
