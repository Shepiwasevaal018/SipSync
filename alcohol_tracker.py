"""
╔══════════════════════════════════════════════════════════════════╗
║          🍹 SIPSYNC — Alcohol Tracker + Wrapped Analytics        ║
╠══════════════════════════════════════════════════════════════════╣
║  HOW TO RUN:                                                      ║
║    1. Install deps:  pip install streamlit plotly pandas         ║
║    2. Run:           streamlit run alcohol_tracker.py            ║
║    3. Open browser:  http://localhost:8501                       ║
║                                                                   ║
║  Data is stored locally in: sipsync.db (SQLite)                 ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import datetime
import random
from pathlib import Path

import pandas as pd

import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────────
#  CONSTANTS & THEME
# ─────────────────────────────────────────────
DB_PATH = "sipsync.db"

NEON_GREEN  = "#39FF14"
NEON_PINK   = "#FF2D78"
NEON_PURPLE = "#BF5FFF"
NEON_CYAN   = "#00F5FF"
NEON_ORANGE = "#FF6B00"
BG_DARK     = "#0D0D0D"
CARD_BG     = "#1A1A2E"
TEXT_LIGHT  = "#E0E0E0"

# Drink-type → vibe copy (Spotify Wrapped style)
VIBE_MAP = {
    "beer":    ("🍺", "The Classic Cruiser",   "You kept it chill — always reliable, never flashy. A true social butterfly."),
    "wine":    ("🍷", "The Sophisticated Sipper","You kept it classy. Candlelight, charcuterie boards, and quiet confidence."),
    "whiskey": ("🥃", "The Old Soul",           "You savoured every moment like a rare vintage. Depth and character — that's you."),
    "vodka":   ("🔮", "The Wild Card",          "Unpredictable, versatile, and always the life of the party. No rules apply."),
    "tequila": ("🌵", "The Risk-Taker",         "You lived on the edge. Every sip was a dare — and you never backed down."),
    "gin":     ("🌿", "The Artisan",            "Botanical and intentional. You make craft look effortless."),
    "rum":     ("🏴‍☠️", "The Adventurer",       "You chased good vibes and warmer waters. Life's a beach for you."),
    "cocktail":("🍹", "The Creative Director",  "Layered, complex, and always impressive. You never do anything halfway."),
    "cider":   ("🍎", "The Laid-Back Legend",   "Easy-going and always welcome. You're everyone's favourite person."),
    "shots":   ("💥", "The Chaos Agent",        "No half measures. You showed up, you went all in, and you have no regrets."),
    "other":   ("🌀", "The Free Spirit",        "You defy categorisation — and that's exactly your superpower."),
}

DRINK_CATEGORIES = ["Beer", "Wine", "Whiskey", "Vodka", "Tequila",
                    "Gin", "Rum", "Cocktail", "Cider", "Shots", "Other"]

PLOTLY_TEMPLATE = dict(
    layout=go.Layout(
        paper_bgcolor=BG_DARK,
        plot_bgcolor=CARD_BG,
        font=dict(color=TEXT_LIGHT, family="Inter, sans-serif"),
        xaxis=dict(gridcolor="#2a2a3e", zerolinecolor="#2a2a3e"),
        yaxis=dict(gridcolor="#2a2a3e", zerolinecolor="#2a2a3e"),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
    )
)

# ─────────────────────────────────────────────
#  DATABASE LAYER
# ─────────────────────────────────────────────
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS drinks (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_at TEXT    NOT NULL,
                name      TEXT    NOT NULL,
                category  TEXT    NOT NULL,
                volume_ml REAL    NOT NULL,
                abv       REAL
            )
        """)
        conn.commit()


def log_drink(name: str, category: str, volume_ml: float, abv: float | None):
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO drinks (logged_at, name, category, volume_ml, abv) VALUES (?,?,?,?,?)",
            (ts, name.strip(), category, volume_ml, abv),
        )
        conn.commit()


def fetch_all() -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query("SELECT * FROM drinks ORDER BY logged_at DESC", conn)
    if not df.empty:
        df["logged_at"] = pd.to_datetime(df["logged_at"])
    return df


def fetch_period(start: datetime.date, end: datetime.date) -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM drinks WHERE date(logged_at) BETWEEN ? AND ?",
            conn,
            params=(start.isoformat(), end.isoformat()),
        )
    if not df.empty:
        df["logged_at"] = pd.to_datetime(df["logged_at"])
    return df

# ─────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────
def ml_to_liters(ml: float) -> float:
    return round(ml / 1000, 2)


def dominant_category(df: pd.DataFrame) -> str:
    if df.empty:
        return "other"
    top = df["category"].value_counts().idxmax()
    return top.lower()


def vibe_for(category: str):
    key = category.lower()
    return VIBE_MAP.get(key, VIBE_MAP["other"])


def styled_card(content_fn, border_color=NEON_GREEN):
    """Wrap a content-rendering callable in a neon card."""
    st.markdown(
        f'<div style="border:2px solid {border_color};border-radius:16px;'
        f'padding:20px;margin-bottom:16px;background:{CARD_BG};">',
        unsafe_allow_html=True,
    )
    content_fn()
    st.markdown("</div>", unsafe_allow_html=True)


def metric_card(label: str, value: str, color: str = NEON_GREEN):
    st.markdown(
        f"""
        <div style="background:{CARD_BG};border:1.5px solid {color};border-radius:14px;
                    padding:18px 22px;text-align:center;margin-bottom:10px;">
            <div style="color:{color};font-size:0.78rem;font-weight:700;
                        letter-spacing:2px;text-transform:uppercase;">{label}</div>
            <div style="color:#fff;font-size:2rem;font-weight:800;margin-top:4px;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def neon_header(text: str, color: str = NEON_GREEN):
    st.markdown(
        f'<h2 style="color:{color};font-weight:900;letter-spacing:2px;margin:0;">{text}</h2>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
#  CHART BUILDERS
# ─────────────────────────────────────────────
def chart_7day(df: pd.DataFrame) -> go.Figure:
    today = datetime.date.today()
    days  = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]
    day_labels = [d.strftime("%a %d") for d in days]

    if df.empty:
        volumes = [0] * 7
    else:
        df["date"] = df["logged_at"].dt.date
        daily = df.groupby("date")["volume_ml"].sum().reset_index()
        daily_map = {row.date: row.volume_ml for row in daily.itertuples()}
        volumes = [daily_map.get(d, 0) / 1000 for d in days]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=day_labels, y=volumes,
        mode="lines+markers",
        line=dict(color=NEON_GREEN, width=3),
        marker=dict(color=NEON_PINK, size=9, line=dict(color=NEON_GREEN, width=2)),
        fill="tozeroy",
        fillcolor="rgba(57,255,20,0.08)",
        name="Volume (L)",
    ))
    fig.update_layout(
        **PLOTLY_TEMPLATE["layout"].to_plotly_json(),
        title=dict(text="Last 7 Days (Litres)", font=dict(color=NEON_GREEN, size=16)),
        xaxis_title="Day",
        yaxis_title="Volume (L)",
        margin=dict(l=40, r=20, t=50, b=40),
        height=300,
    )
    return fig


def chart_category_donut(df: pd.DataFrame) -> go.Figure:
    counts = df["category"].value_counts()
    colors = [NEON_GREEN, NEON_PINK, NEON_PURPLE, NEON_CYAN, NEON_ORANGE,
              "#FFE600", "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"]
    fig = go.Figure(go.Pie(
        labels=counts.index,
        values=counts.values,
        hole=0.55,
        marker=dict(colors=colors[:len(counts)], line=dict(color=BG_DARK, width=2)),
        textinfo="label+percent",
        textfont=dict(color="#fff", size=12),
    ))
    fig.update_layout(
        **PLOTLY_TEMPLATE["layout"].to_plotly_json(),
        title=dict(text="Category Breakdown", font=dict(color=NEON_PINK, size=16)),
        showlegend=False,
        margin=dict(l=0, r=0, t=50, b=0),
        height=320,
    )
    return fig


def chart_hourly_heatmap(df: pd.DataFrame) -> go.Figure:
    df = df.copy()
    df["hour"] = df["logged_at"].dt.hour
    df["dow"]  = df["logged_at"].dt.day_name()

    DOW_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = (
        df.groupby(["dow", "hour"])["volume_ml"]
        .sum()
        .unstack(fill_value=0)
        .reindex(DOW_ORDER)
    )
    # Ensure all 24 hours present
    for h in range(24):
        if h not in pivot.columns:
            pivot[h] = 0
    pivot = pivot[sorted(pivot.columns)]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"{h:02d}:00" for h in pivot.columns],
        y=pivot.index.tolist(),
        colorscale=[[0, BG_DARK], [0.5, NEON_PURPLE], [1, NEON_PINK]],
        showscale=True,
        hovertemplate="Day: %{y}<br>Hour: %{x}<br>Volume: %{z:.0f}ml<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_TEMPLATE["layout"].to_plotly_json(),
        title=dict(text="Peak Drinking Hours Heatmap", font=dict(color=NEON_CYAN, size=16)),
        xaxis_title="Hour of Day",
        yaxis_title="",
        margin=dict(l=100, r=20, t=50, b=60),
        height=320,
    )
    return fig


def chart_top_drinks(df: pd.DataFrame) -> go.Figure:
    top = df["name"].value_counts().head(8).reset_index()
    top.columns = ["Drink", "Count"]
    colors = [NEON_PINK, NEON_GREEN, NEON_PURPLE, NEON_CYAN,
              NEON_ORANGE, "#FFE600", "#FF6B6B", "#4ECDC4"]

    fig = go.Figure(go.Bar(
        x=top["Count"],
        y=top["Drink"],
        orientation="h",
        marker=dict(color=colors[:len(top)], line=dict(color=BG_DARK, width=1)),
        text=top["Count"],
        textposition="inside",
        textfont=dict(color="#fff", size=13, family="Inter Bold"),
    ))
    fig.update_layout(
        **PLOTLY_TEMPLATE["layout"].to_plotly_json(),
        title=dict(text="Top Drinks Logged", font=dict(color=NEON_PINK, size=16)),
        xaxis_title="Times Logged",
        yaxis_title="",
        margin=dict(l=20, r=20, t=50, b=40),
        height=320,
    )
    return fig

# ─────────────────────────────────────────────
#  WRAPPED GENERATOR
# ─────────────────────────────────────────────
def render_wrapped(df: pd.DataFrame, period_label: str):
    if df.empty:
        st.warning("🍂 No data found for this period. Start logging drinks first!")
        return

    top_cat   = dominant_category(df)
    top_drink = df["name"].value_counts().idxmax()
    total_vol = ml_to_liters(df["volume_ml"].sum())
    total_sessions = len(df)
    avg_abv   = df["abv"].dropna().mean()
    peak_hour = df["logged_at"].dt.hour.value_counts().idxmax() if not df.empty else 0

    emoji, title, copy = vibe_for(top_cat)

    # ── WRAPPED HEADER ──────────────────────────────
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#1A1A2E,#16213E,#0F3460);
                    border-radius:24px;padding:40px 30px;text-align:center;
                    border:2px solid {NEON_PINK};margin-bottom:28px;">
            <div style="font-size:4rem;margin-bottom:8px;">{emoji}</div>
            <div style="color:{NEON_PINK};font-size:0.8rem;font-weight:700;
                        letter-spacing:4px;text-transform:uppercase;">
                SipSync {period_label.upper()} WRAPPED
            </div>
            <h1 style="color:#fff;font-size:2.6rem;font-weight:900;margin:10px 0;">
                {title}
            </h1>
            <p style="color:{TEXT_LIGHT};font-size:1.1rem;max-width:520px;
                      margin:0 auto;line-height:1.6;">{copy}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── BIG STATS GRID ──────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("🏆 Top Genre", top_cat.capitalize(), NEON_GREEN)
    with c2:
        metric_card("⭐ Top Drink", top_drink, NEON_PINK)
    with c3:
        metric_card("🍶 Total Volume", f"{total_vol}L", NEON_CYAN)
    with c4:
        metric_card("🕐 Peak Hour", f"{peak_hour:02d}:00", NEON_PURPLE)

    c5, c6 = st.columns(2)
    with c5:
        metric_card("📊 Total Logs", str(total_sessions), NEON_ORANGE)
    with c6:
        avg_text = f"{avg_abv:.1f}%" if not pd.isna(avg_abv) else "N/A"
        metric_card("🔥 Avg ABV", avg_text, "#FFE600")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── CHARTS ──────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(chart_category_donut(df), use_container_width=True)
    with col_b:
        st.plotly_chart(chart_top_drinks(df), use_container_width=True)

    st.plotly_chart(chart_hourly_heatmap(df), use_container_width=True)

    # ── FUN FACT FOOTER ──────────────────────────────
    fun_facts = [
        f"You drank the equivalent of {int(total_vol * 1.33)} standard wine glasses. 🍷",
        f"If laid end to end, your bottles would stretch {total_vol * 30:.0f}cm. 📏",
        f"Your most active drink hour: {peak_hour:02d}:00. Night owl or happy hour hero?",
        f"You tried {df['name'].nunique()} different drinks. Variety is the spice of life! 🌶️",
    ]
    st.markdown(
        f"""
        <div style="background:linear-gradient(90deg,{NEON_PURPLE}22,{NEON_PINK}22);
                    border-left:4px solid {NEON_PURPLE};border-radius:12px;
                    padding:16px 22px;margin-top:20px;">
            <div style="color:{NEON_PURPLE};font-weight:700;letter-spacing:2px;
                        font-size:0.75rem;text-transform:uppercase;">🎉 Fun Fact</div>
            <div style="color:#fff;font-size:1rem;margin-top:6px;">
                {random.choice(fun_facts)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
#  PAGE CONFIG & GLOBAL CSS
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="SipSync 🍹",
    page_icon="🍹",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
            background-color: {BG_DARK};
            color: {TEXT_LIGHT};
        }}
        .block-container {{ padding-top: 1.5rem; max-width: 1200px; }}
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background: {CARD_BG};
            border-radius: 12px;
            padding: 6px;
        }}
        .stTabs [data-baseweb="tab"] {{
            background: transparent;
            border-radius: 8px;
            color: {TEXT_LIGHT};
            font-weight: 700;
            letter-spacing: 1px;
            padding: 8px 22px;
        }}
        .stTabs [aria-selected="true"] {{
            background: {NEON_GREEN} !important;
            color: #000 !important;
        }}
        /* Buttons */
        .stButton > button {{
            background: linear-gradient(135deg, {NEON_GREEN}, {NEON_CYAN});
            color: #000;
            font-weight: 900;
            border: none;
            border-radius: 12px;
            padding: 10px 28px;
            font-size: 1rem;
            letter-spacing: 1px;
            transition: transform 0.15s;
            width: 100%;
        }}
        .stButton > button:hover {{
            transform: scale(1.03);
            box-shadow: 0 0 18px {NEON_GREEN}88;
        }}
        /* Inputs */
        .stTextInput input, .stNumberInput input, .stSelectbox div {{
            background: {CARD_BG} !important;
            border: 1.5px solid #2a2a3e !important;
            border-radius: 10px !important;
            color: #fff !important;
        }}
        /* Metric */
        [data-testid="metric-container"] {{
            background: {CARD_BG};
            border: 1.5px solid #2a2a3e;
            border-radius: 14px;
            padding: 14px;
        }}
        /* Divider */
        hr {{ border-color: #2a2a3e; }}
        /* Scrollbar */
        ::-webkit-scrollbar {{ width: 6px; }}
        ::-webkit-scrollbar-track {{ background: {BG_DARK}; }}
        ::-webkit-scrollbar-thumb {{ background: {NEON_GREEN}66; border-radius: 3px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
#  BOOTSTRAP
# ─────────────────────────────────────────────
init_db()

# ─────────────────────────────────────────────
#  APP HEADER
# ─────────────────────────────────────────────
st.markdown(
    f"""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:8px;">
        <div style="font-size:2.8rem;">🍹</div>
        <div>
            <h1 style="color:{NEON_GREEN};font-size:2.4rem;font-weight:900;
                        letter-spacing:4px;margin:0;line-height:1.1;">SIPSYNC</h1>
            <div style="color:{TEXT_LIGHT};font-size:0.85rem;
                        letter-spacing:3px;opacity:0.7;">DRINK TRACKER + WRAPPED ANALYTICS</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("---")

# ─────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────
tab_log, tab_dash, tab_wrapped = st.tabs([
    "  🥃  LOG A DRINK  ",
    "  📊  DASHBOARD  ",
    "  🎁  WRAPPED  ",
])

# ══════════════════════════════════════════════
#  TAB 1 — LOGGER
# ══════════════════════════════════════════════
with tab_log:
    st.markdown(f"<h3 style='color:{NEON_GREEN};'>Add a Drink</h3>", unsafe_allow_html=True)

    with st.form("log_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            drink_name = st.text_input(
                "Drink Name *",
                placeholder="e.g. Corona, Pinot Noir, Jameson...",
            )
            category = st.selectbox("Category *", DRINK_CATEGORIES)
        with col2:
            volume = st.number_input(
                "Volume (ml) *",
                min_value=1.0,
                max_value=5000.0,
                value=330.0,
                step=10.0,
            )
            abv = st.number_input(
                "ABV % (optional)",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=0.1,
                help="Leave at 0 to skip",
            )

        notes_col, btn_col = st.columns([3, 1])
        with btn_col:
            submitted = st.form_submit_button("🍻  LOG DRINK")

    if submitted:
        if not drink_name.strip():
            st.error("⚠️  Please enter a drink name.")
        elif volume <= 0:
            st.error("⚠️  Volume must be greater than 0.")
        else:
            abv_val = abv if abv > 0 else None
            log_drink(drink_name, category, volume, abv_val)
            st.success(f"✅  **{drink_name}** ({volume}ml) logged successfully!")
            st.balloons()

    # Quick reference
    st.markdown("---")
    st.markdown(f"<h4 style='color:{NEON_CYAN};'>📋 Common Volumes</h4>", unsafe_allow_html=True)
    ref_data = {
        "Drink": ["Beer can", "Beer pint", "Wine glass", "Shot", "Spirit measure", "Cocktail"],
        "Volume": ["330 ml", "568 ml", "175 ml", "25–30 ml", "35 ml", "200–250 ml"],
        "Typical ABV": ["4–5%", "4–5%", "12–14%", "40%", "37–40%", "5–25%"],
    }
    st.dataframe(
        pd.DataFrame(ref_data),
        use_container_width=True,
        hide_index=True,
    )

# ══════════════════════════════════════════════
#  TAB 2 — DASHBOARD
# ══════════════════════════════════════════════
with tab_dash:
    df_all = fetch_all()
    today  = datetime.date.today()

    # Today's stats
    df_today = df_all[df_all["logged_at"].dt.date == today] if not df_all.empty else pd.DataFrame()

    neon_header("Today's Summary", NEON_GREEN)
    st.markdown("<br>", unsafe_allow_html=True)

    if df_today.empty:
        st.info("🌙 Nothing logged today yet. Stay hydrated!")
    else:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Drinks Logged", len(df_today))
        with c2:
            st.metric("Total Volume", f"{ml_to_liters(df_today['volume_ml'].sum())}L")
        with c3:
            st.metric("Top Category", df_today["category"].value_counts().idxmax())
        with c4:
            avg = df_today["abv"].dropna().mean()
            st.metric("Avg ABV", f"{avg:.1f}%" if not pd.isna(avg) else "N/A")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")

    # 7-day line chart
    neon_header("Last 7 Days", NEON_CYAN)
    week_start = today - datetime.timedelta(days=6)
    df_week = fetch_period(week_start, today)
    st.plotly_chart(chart_7day(df_week), use_container_width=True)

    st.markdown("---")

    # Recent history
    neon_header("Recent History", NEON_PINK)
    if df_all.empty:
        st.info("No drinks logged yet.")
    else:
        df_display = df_all.head(20).copy()
        df_display["logged_at"] = df_display["logged_at"].dt.strftime("%Y-%m-%d %H:%M")
        df_display["volume_ml"] = df_display["volume_ml"].apply(lambda v: f"{v:.0f}ml")
        df_display["abv"] = df_display["abv"].apply(
            lambda v: f"{v:.1f}%" if pd.notna(v) else "—"
        )
        df_display = df_display.rename(columns={
            "logged_at": "Timestamp",
            "name": "Drink",
            "category": "Category",
            "volume_ml": "Volume",
            "abv": "ABV",
        })
        st.dataframe(
            df_display[["Timestamp", "Drink", "Category", "Volume", "ABV"]],
            use_container_width=True,
            hide_index=True,
        )

# ══════════════════════════════════════════════
#  TAB 3 — WRAPPED
# ══════════════════════════════════════════════
with tab_wrapped:
    neon_header("🎁 SipSync Wrapped", NEON_PINK)
    st.markdown(
        f"<p style='color:{TEXT_LIGHT};opacity:0.8;margin-top:-4px;'>"
        "Your personalised drink analytics — Spotify Wrapped style.</p>",
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    col_m, col_y = st.columns(2)

    with col_m:
        st.markdown(
            f"<div style='text-align:center;color:{NEON_GREEN};font-weight:700;"
            f"letter-spacing:2px;margin-bottom:10px;'>MONTHLY WRAPPED</div>",
            unsafe_allow_html=True,
        )
        now = datetime.date.today()
        selected_month = st.selectbox(
            "Select Month",
            options=[
                (now - datetime.timedelta(days=30 * i)).replace(day=1)
                for i in range(12)
            ],
            format_func=lambda d: d.strftime("%B %Y"),
            key="month_sel",
        )
        gen_monthly = st.button("🚀  Generate Monthly Wrapped", key="btn_monthly")

    with col_y:
        st.markdown(
            f"<div style='text-align:center;color:{NEON_PINK};font-weight:700;"
            f"letter-spacing:2px;margin-bottom:10px;'>YEARLY WRAPPED</div>",
            unsafe_allow_html=True,
        )
        current_year = datetime.date.today().year
        selected_year = st.selectbox(
            "Select Year",
            options=list(range(current_year, current_year - 5, -1)),
            key="year_sel",
        )
        gen_yearly = st.button("🎆  Generate Yearly Wrapped", key="btn_yearly")

    st.markdown("---")

    if gen_monthly:
        import calendar
        month_start = selected_month
        last_day    = calendar.monthrange(month_start.year, month_start.month)[1]
        month_end   = month_start.replace(day=last_day)
        df_period   = fetch_period(month_start, month_end)
        label       = month_start.strftime("%B %Y")
        render_wrapped(df_period, label)

    elif gen_yearly:
        year_start = datetime.date(selected_year, 1, 1)
        year_end   = datetime.date(selected_year, 12, 31)
        df_period  = fetch_period(year_start, year_end)
        render_wrapped(df_period, str(selected_year))

    else:
        # Placeholder state
        st.markdown(
            f"""
            <div style="text-align:center;padding:60px 30px;
                        border:2px dashed #2a2a3e;border-radius:20px;">
                <div style="font-size:3.5rem;margin-bottom:12px;">🎁</div>
                <div style="color:{NEON_PINK};font-size:1.4rem;font-weight:800;
                            letter-spacing:2px;">YOUR WRAPPED IS WAITING</div>
                <p style="color:{TEXT_LIGHT};opacity:0.6;margin-top:8px;">
                    Select a period above and hit Generate to see your personalised report.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
#  FOOTER
# ─────────────────────────────────────────────
st.markdown(
    f"""
    <div style="text-align:center;padding:24px 0 8px;
                color:{TEXT_LIGHT};opacity:0.35;font-size:0.78rem;letter-spacing:1px;">
        SIPSYNC · Built with Streamlit & Plotly · Data stored locally in sipsync.db<br>
        🍹 Drink responsibly. Know your limits.
    </div>
    """,
    unsafe_allow_html=True,
)
