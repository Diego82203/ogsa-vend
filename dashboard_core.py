from __future__ import annotations

import calendar
import html
import json
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from plotly.subplots import make_subplots

from access_control import authenticate_access, render_logout

DB_PATH = Path(__file__).with_name("dashboard.db")
APP_MODE = os.environ.get("OGSA_APP_MODE", "Vendedor").strip()
if APP_MODE not in {"Vendedor", "Gerencial"}:
    raise RuntimeError("OGSA_APP_MODE debe ser Vendedor o Gerencial")
DEMO_MODE = os.environ.get("OGSA_DEMO", "0") == "1"
TZ = ZoneInfo("America/Guayaquil")
WEEKDAYS_ES = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
    4: "Viernes", 5: "Sábado", 6: "Domingo",
}
WEEKDAY_ORDER = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
MONTHS_ES = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
    7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic",
}
MONTHS_FULL_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

st.set_page_config(
    page_title=("OGSA · Vendedores" if APP_MODE == "Vendedor" else "OGSA · Gerencial"),
    page_icon="📊",
    layout="wide",
    initial_sidebar_state=("auto" if APP_MODE == "Vendedor" else "expanded"),
)

st.markdown(
    """
    <style>
      :root {
        --ogsa-dark:#101827;
        --ogsa-text:#172033;
        --ogsa-muted:#667085;
        --ogsa-line:#E7EAF0;
        --ogsa-bg:#F6F7F9;
        --ogsa-green:#14804A;
        --ogsa-green-soft:#DFF3E6;
        --ogsa-orange:#E46A1A;
        --ogsa-orange-soft:#FFF0E5;
        --ogsa-red:#C9372C;
        --ogsa-pill:#F2F4F7;
      }
      .stApp {background:var(--ogsa-bg);}
      .block-container {padding-top:1.05rem; padding-bottom:2rem; max-width:1600px;}
      [data-testid="stSidebar"] {background:#FFFFFF; border-right:1px solid var(--ogsa-line);}
      [data-testid="stSidebar"] .block-container {padding-top:1.25rem;}
      .ogsa-header {
        background:linear-gradient(110deg,#101827 0%,#192435 68%,#2A2020 100%);
        color:#fff; padding:24px 28px; border-radius:0 0 16px 16px;
        border-top:4px solid #159455; margin:-1.05rem -1rem 1.15rem -1rem;
        box-shadow:0 6px 18px rgba(16,24,39,.08);
      }
      .ogsa-title {font-size:2rem; font-weight:760; letter-spacing:-.03em; margin:0;}
      .ogsa-subtitle {font-size:.96rem; opacity:.82; margin-top:5px;}
      .ogsa-badge {display:inline-block; margin-top:10px; margin-right:8px; background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.16); padding:5px 10px; border-radius:999px; font-size:.78rem;}
      .kpi-card {
        min-height:122px; background:#fff; border:1px solid var(--ogsa-line); border-radius:16px;
        padding:17px 17px 15px; box-shadow:0 8px 24px rgba(16,24,39,.045); position:relative; overflow:hidden;
      }
      .kpi-card:after {content:""; position:absolute; width:70px; height:70px; border-radius:50%; top:-30px; right:-20px; background:#EDF7F1;}
      .kpi-card.warn:after {background:#FFF0E5;}
      .kpi-label {font-size:.76rem; text-transform:uppercase; letter-spacing:.035em; color:#70798C; font-weight:700;}
      .kpi-value {font-size:2rem; line-height:1.08; font-weight:760; color:var(--ogsa-text); margin:11px 0 4px; letter-spacing:-.035em;}
      .kpi-note {font-size:.79rem; color:#70798C;}
      .section-title {font-size:1.05rem; font-weight:760; color:var(--ogsa-text); margin:0 0 2px 0;}
      .section-subtitle {font-size:.82rem; color:var(--ogsa-muted); margin-bottom:10px;}
      .priority-card {background:#fff; border:1px solid var(--ogsa-line); border-left:5px solid #98A2B3; border-radius:14px; padding:14px 15px; margin-bottom:9px;}
      .priority-card.red {border-left-color:var(--ogsa-red);}
      .priority-card.orange {border-left-color:var(--ogsa-orange);}
      .priority-card.green {border-left-color:var(--ogsa-green);}
      .priority-head {display:flex; justify-content:space-between; gap:12px; align-items:flex-start;}
      .priority-client {font-size:.98rem; font-weight:760; color:var(--ogsa-text);}
      .priority-action {font-size:.72rem; font-weight:760; padding:4px 8px; border-radius:999px; background:#F2F4F7; color:#344054; white-space:nowrap;}
      .priority-reason {font-size:.84rem; color:#475467; margin-top:5px;}
      .priority-meta {font-size:.75rem; color:#98A2B3; margin-top:7px;}
      .status-note {background:#fff; border:1px solid var(--ogsa-line); border-radius:12px; padding:10px 12px; font-size:.83rem; color:#475467;}
      div[data-testid="stDataFrame"] {border:1px solid var(--ogsa-line); border-radius:14px; overflow:hidden; background:#fff;}
      div[data-testid="stPlotlyChart"] {background:#fff; border:1px solid var(--ogsa-line); border-radius:16px; padding:3px 5px 0;}
      .summary-card {background:#fff; border:1px solid var(--ogsa-line); border-radius:16px; padding:18px; box-shadow:0 8px 24px rgba(16,24,39,.035);}
      .summary-mini {background:#fff; border:1px solid var(--ogsa-line); border-radius:12px; padding:12px 14px; min-height:88px;}
      .summary-mini .label {font-size:.76rem; font-weight:700; color:#70798C; text-transform:uppercase;}
      .summary-mini .value {font-size:1.65rem; font-weight:760; color:var(--ogsa-text); margin-top:4px;}
      .summary-mini .note {font-size:.78rem; color:var(--ogsa-muted);}
      .chip {display:inline-block; font-size:.75rem; font-weight:700; color:#3E4C66; background:var(--ogsa-pill); border-radius:999px; padding:5px 10px;}
      .small-muted {color:var(--ogsa-muted); font-size:.78rem;}
      .manager-strip {background:#07335B; color:#fff; border-radius:16px; padding:16px 18px; margin-bottom:14px; box-shadow:0 8px 24px rgba(7,51,91,.12);}
      .manager-strip b {color:#F8C900;}
      .manager-note {background:#FFF8E5; border:1px solid #F4D77B; color:#594A16; border-radius:12px; padding:10px 12px; font-size:.82rem;}
      /* --- Mobile / touch-first seller experience --- */
      html, body, [data-testid="stAppViewContainer"], .stApp {
        max-width:100%; overflow-x:hidden;
      }
      div[data-testid="stForm"] {
        max-width:440px; margin:1.25rem auto 0; background:#fff;
        border:1px solid var(--ogsa-line); border-radius:18px;
        padding:1rem 1rem .45rem; box-shadow:0 12px 32px rgba(16,24,39,.08);
      }
      div[data-testid="stForm"] input {min-height:46px;}
      div[data-testid="stFormSubmitButton"] button {min-height:48px; font-weight:760;}

      @media (max-width: 800px) {
        .block-container {
          padding-top:.45rem; padding-left:.65rem; padding-right:.65rem;
          padding-bottom:1.35rem; max-width:100%;
        }
        [data-testid="stSidebar"] {width:min(88vw,340px) !important;}
        [data-testid="stSidebar"] .block-container {padding:1rem .85rem 1.2rem;}
        [data-testid="stSidebar"] label, [data-testid="stSidebar"] button {font-size:.96rem;}
        [data-testid="stSidebar"] div[role="radiogroup"] label {
          min-height:44px; display:flex; align-items:center; padding:.18rem 0;
        }

        .ogsa-header {
          padding:16px 15px 15px; border-radius:0 0 14px 14px;
          margin:-.45rem -.65rem .8rem -.65rem;
        }
        .ogsa-title {font-size:1.35rem; line-height:1.18;}
        .ogsa-subtitle {font-size:.84rem; line-height:1.35;}
        .ogsa-badge {font-size:.69rem; padding:4px 8px; margin-top:7px; margin-right:4px;}

        /* Force desktop column groups to become a readable single-column feed. */
        [data-testid="stHorizontalBlock"] {
          display:flex !important; flex-direction:column !important;
          gap:.65rem !important; width:100% !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
          width:100% !important; min-width:100% !important; flex:1 1 100% !important;
        }

        .kpi-card {min-height:94px; padding:13px 14px 11px; border-radius:14px;}
        .kpi-label {font-size:.69rem;}
        .kpi-value {font-size:1.5rem; margin:7px 0 2px;}
        .kpi-note {font-size:.74rem; line-height:1.3;}
        .summary-card {padding:13px; border-radius:14px;}
        .summary-mini {min-height:76px; padding:10px 12px;}
        .summary-mini .value {font-size:1.4rem;}
        .section-title {font-size:1rem;}
        .section-subtitle {font-size:.78rem; line-height:1.35; margin-bottom:7px;}
        .priority-card {padding:12px; border-radius:12px;}
        .priority-head {gap:8px;}
        .priority-client {font-size:.92rem;}
        .priority-action {font-size:.66rem; white-space:normal; text-align:right;}
        .priority-reason {font-size:.79rem;}
        .priority-meta {font-size:.70rem; line-height:1.35;}

        /* Touch controls: 44px+ targets and 16px inputs prevent iOS zoom. */
        .stButton > button, .stDownloadButton > button,
        div[data-testid="stFormSubmitButton"] button {min-height:46px; border-radius:10px;}
        input, textarea, select {font-size:16px !important;}
        [data-baseweb="select"] > div {min-height:46px;}
        [data-testid="stDateInput"] input, [data-testid="stTextInput"] input {min-height:46px;}

        /* Charts and tables stay inside the phone viewport. */
        div[data-testid="stPlotlyChart"] {
          width:100% !important; max-width:100% !important; overflow:hidden;
          border-radius:13px; padding:1px 2px 0;
        }
        div[data-testid="stPlotlyChart"] .js-plotly-plot,
        div[data-testid="stPlotlyChart"] .plot-container,
        div[data-testid="stPlotlyChart"] .svg-container {max-width:100% !important;}
        div[data-testid="stDataFrame"] {
          width:100% !important; max-width:100% !important; border-radius:12px;
        }

        /* Login is deliberately narrow and thumb-friendly. */
        div[data-testid="stForm"] {
          width:100%; max-width:100%; margin:.75rem auto 0;
          padding:.8rem .8rem .35rem; border-radius:16px; box-shadow:none;
        }
        div[data-testid="stForm"] input {min-height:48px; font-size:16px !important;}

        h1 {font-size:1.65rem !important;}
        h2 {font-size:1.3rem !important;}
        h3 {font-size:1.05rem !important;}
        p, .stCaption {line-height:1.4;}
      }

      @media (max-width: 420px) {
        .block-container {padding-left:.5rem; padding-right:.5rem;}
        .ogsa-header {margin-left:-.5rem; margin-right:-.5rem;}
        .ogsa-title {font-size:1.24rem;}
        .kpi-value {font-size:1.4rem;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_conn() -> sqlite3.Connection:
    if not DB_PATH.exists():
        st.error("No se encontró dashboard.db. Ejecuta build_database.py primero.")
        st.stop()
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def rows(sql: str, params=()) -> list[dict]:
    cur = get_conn().execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def scalar(sql: str, params=(), default=0):
    r = get_conn().execute(sql, params).fetchone()
    if r is None or r[0] is None:
        return default
    return r[0]


def money(v: float | int | None, decimals: int = 2) -> str:
    v = float(v or 0)
    return f"${v:,.{decimals}f}"


def whole(v: float | int | None) -> str:
    return f"{float(v or 0):,.0f}"


def pct_abs(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:.2f}%"


def pct_delta(v: float | None) -> str:
    if v is None:
        return "sin base comparable"
    arrow = "▲" if v >= 0 else "▼"
    return f"{arrow} {abs(v):.1f}% vs período comparable"


def iso(d: date) -> str:
    return d.isoformat()


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def pretty_date(d: date) -> str:
    return f"{d.day:02d} {MONTHS_ES[d.month]} {d.year}"


def safe_ratio(a: float, b: float) -> float:
    return a / b if b else 0.0


def kpi(label: str, value: str, note: str, warn: bool = False):
    cls = "kpi-card warn" if warn else "kpi-card"
    st.markdown(
        f'<div class="{cls}"><div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="kpi-value">{html.escape(value)}</div>'
        f'<div class="kpi-note">{html.escape(note)}</div></div>',
        unsafe_allow_html=True,
    )


def section_heading(title: str, subtitle: str = "", chip: str | None = None):
    chip_html = f'<span class="chip">{html.escape(chip)}</span>' if chip else ""
    st.markdown(
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:12px;'>"
        f"<div><div class='section-title'>{html.escape(title)}</div>"
        f"<div class='section-subtitle'>{html.escape(subtitle)}</div></div>{chip_html}</div>",
        unsafe_allow_html=True,
    )


def priority_card(item: dict):
    score = int(item["score"])
    if score >= 65:
        tone = "red"
    elif score >= 35:
        tone = "orange"
    else:
        tone = "green"
    st.markdown(
        f"""
        <div class="priority-card {tone}">
          <div class="priority-head">
            <div class="priority-client">{html.escape(item['client'])}</div>
            <div class="priority-action">{html.escape(item['action'])}</div>
          </div>
          <div class="priority-reason">{html.escape(item['reason'])}</div>
          <div class="priority-meta">Última compra: {html.escape(item['last_buy'])} · Ticket ref.: {html.escape(money(item['avg_order']))} · Canal: {html.escape(item['channel'])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def bar_chart(items: list[dict], label_col: str, value_col: str, title: str, color: str, height: int = 380, value_type: str = "money"):
    if not items:
        st.info("No hay datos para el filtro actual.")
        return
    labels = [str(r[label_col]) for r in items][::-1]
    values = [float(r[value_col] or 0) for r in items][::-1]
    if value_type == "units":
        text_values = [whole(v) for v in values]
        hovertemplate = "%{y}<br>%{x:,.0f} unidades<extra></extra>"
    else:
        text_values = [money(v) for v in values]
        hovertemplate = "%{y}<br>$%{x:,.2f}<extra></extra>"
    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker=dict(color=color),
        text=text_values,
        textposition="outside",
        cliponaxis=False,
        hovertemplate=hovertemplate,
    ))
    fig.update_layout(
        title=None,
        height=height,
        margin=dict(l=18, r=18, t=10, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(title="", showgrid=True, gridcolor="#EDF0F4", zeroline=False),
        yaxis=dict(title="", showgrid=False),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def two_axis_daily_chart(series: list[dict]):
    if not series:
        st.info("No hay actividad diaria para el filtro actual.")
        return
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    x = [r["invoice_date"] for r in series]
    sales = [float(r["sales"] or 0) for r in series]
    units = [float(r["units"] or 0) for r in series]
    ticket = [float(r["ticket"] or 0) for r in series]

    fig.add_trace(go.Scatter(
        x=x, y=sales, mode="lines+markers", name="Ventas netas",
        line=dict(color="#14804A", width=3), marker=dict(size=6),
        hovertemplate="%{x}<br>Ventas netas: $%{y:,.2f}<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=x, y=units, mode="lines+markers", name="Unidades",
        line=dict(color="#101827", width=2), marker=dict(size=6),
        hovertemplate="%{x}<br>Unidades: %{y:,.0f}<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=x, y=ticket, mode="lines+markers", name="Ticket promedio",
        line=dict(color="#E46A1A", width=3), marker=dict(size=6),
        hovertemplate="%{x}<br>Ticket promedio: $%{y:,.2f}<extra></extra>",
    ), secondary_y=True)

    fig.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=15, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis=dict(title="", showgrid=False),
    )
    fig.update_yaxes(title_text="Ventas / unidades", gridcolor="#EDF0F4", zeroline=False, secondary_y=False)
    fig.update_yaxes(title_text="Ticket promedio", showgrid=False, zeroline=False, secondary_y=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ---------- Contexto de datos ----------
data_min = datetime.fromisoformat(scalar("SELECT MIN(invoice_date) FROM sales WHERE invoice_date IS NOT NULL")).date()
data_cutoff = datetime.fromisoformat(scalar("SELECT MAX(invoice_date) FROM sales WHERE invoice_date IS NOT NULL")).date()
company_cutoffs = {r["company"]: r["cutoff"] for r in rows("SELECT company, MAX(invoice_date) cutoff FROM sales WHERE invoice_date IS NOT NULL GROUP BY company")}
app_today = datetime.now(TZ).date()
staleness_days = (app_today - data_cutoff).days

seller_rows = rows(
    """
    SELECT seller_code, MAX(seller_name) seller_name,
           SUM(CASE WHEN invoice_date >= date(?, '-89 day') THEN net_sales ELSE 0 END) sales90
    FROM sales
    WHERE seller_code <> ''
    GROUP BY seller_code
    HAVING sales90 > 0
    ORDER BY sales90 DESC
    """,
    (iso(data_cutoff),),
)

seller_labels = {f"{r['seller_name']} · {r['seller_code']}": r["seller_code"] for r in seller_rows}
provider_names = [r["provider_name"] for r in rows("SELECT DISTINCT provider_name FROM sales WHERE provider_name<>'' ORDER BY provider_name")]
category_names = [r["category_name"] for r in rows("SELECT DISTINCT category_name FROM sales WHERE category_name<>'' ORDER BY category_name")]

# Fechas de referencia y opciones de período
m_start_default = data_cutoff.replace(day=1)

def month_starts_between(start: date, end: date) -> list[date]:
    out = []
    cur = start.replace(day=1)
    end_m = end.replace(day=1)
    while cur <= end_m:
        out.append(cur)
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return out

def week_ranges_between(start: date, end: date) -> list[tuple[date, date]]:
    monday = start - timedelta(days=start.weekday())
    out = []
    cur = monday
    while cur <= end:
        week_end = cur + timedelta(days=6)
        clipped_start = max(cur, start)
        clipped_end = min(week_end, end)
        if clipped_start <= clipped_end:
            out.append((clipped_start, clipped_end))
        cur += timedelta(days=7)
    return out

month_options = month_starts_between(data_min, data_cutoff)
week_options = week_ranges_between(data_min, data_cutoff)

view_mode = APP_MODE
access = authenticate_access(view_mode)

with st.sidebar:
    st.markdown("## OGSA")
    st.caption("Gestión comercial · OGSA + DIGAR" if view_mode == "Vendedor" else "Inteligencia gerencial")

    if view_mode == "Vendedor":
        st.caption("PORTAL DE VENDEDORES")
        if DEMO_MODE:
            st.info("Modo demo local: el selector de vendedor está habilitado solo para pruebas.")
            selected_label = st.selectbox("Vendedor de prueba", list(seller_labels.keys()))
            seller = seller_labels[selected_label]
        else:
            seller = access.get("seller_code", "")
            valid_codes = {r["seller_code"] for r in seller_rows}
            if seller not in valid_codes:
                st.error("Tu usuario no tiene un vendedor válido asignado. Contacta al administrador.")
                st.stop()
        seller_name = next(r["seller_name"] for r in seller_rows if r["seller_code"] == seller)
        if not DEMO_MODE:
            st.caption(f"Sesión: {access.get('display_name') or access.get('username')} · {seller_name.title()}")
            render_logout()
        st.divider()
        page = st.radio("Navegación", ["Mi día", "Mis clientes", "Oportunidades", "Mi desempeño"])
        manager_provider = "Todos"
        manager_providers = []
        manager_sellers = []
        manager_month_keys = []
        manager_category = "Todas"
    else:
        st.caption("PORTAL GERENCIAL")
        if DEMO_MODE:
            st.info("Modo demo local gerencial.")
        else:
            st.caption(f"Sesión: {access.get('display_name') or access.get('username')}")
            render_logout()
        st.divider()
        page = st.radio("Navegación", ["Resumen gerencial", "Análisis de proveedores", "Mapa de clientes", "Fuerza de ventas"])
        manager_providers = st.multiselect(
            "Proveedores",
            provider_names,
            default=[],
            placeholder="Todos los proveedores",
            help="Deja vacío para analizar todos. Puedes seleccionar uno o varios proveedores al mismo tiempo.",
        )
        manager_provider = manager_providers[0] if len(manager_providers) == 1 else ("Todos" if not manager_providers else "Múltiples")
        if manager_providers:
            st.caption(f"{len(manager_providers)} proveedor(es) seleccionado(s)")
        else:
            st.caption("Todos los proveedores")
        manager_seller_labels = st.multiselect(
            "Vendedores",
            list(seller_labels.keys()),
            default=[],
            placeholder="Todos los vendedores",
            help="Deja vacío para analizar todos. Puedes seleccionar uno o varios vendedores al mismo tiempo.",
        )
        manager_sellers = [seller_labels[label] for label in manager_seller_labels]
        manager_category = st.selectbox("Categoría", ["Todas"] + category_names)
        seller = seller_rows[0]["seller_code"] if seller_rows else ""
        seller_name = "Todos los vendedores"

    st.divider()
    st.markdown("### Período")

    if view_mode == "Gerencial":
        manager_month_keys = []
        period_mode = st.radio("Filtrar por", ["Rango libre", "Mes", "Semana"], horizontal=False, index=0)
        if period_mode == "Rango libre":
            filter_start = st.date_input("Desde", value=m_start_default, min_value=data_min, max_value=data_cutoff)
            filter_end = st.date_input("Hasta", value=data_cutoff, min_value=data_min, max_value=data_cutoff)
            if filter_start > filter_end:
                filter_start, filter_end = filter_end, filter_start
        elif period_mode == "Mes":
            month_labels = {f"{MONTHS_FULL_ES[d.month]} {d.year}": d for d in reversed(month_options)}
            month_label_list = list(month_labels.keys())
            selected_month_labels = st.multiselect(
                "Meses",
                month_label_list,
                default=month_label_list[:1],
                placeholder="Selecciona uno o varios meses",
            )
            if selected_month_labels:
                selected_month_starts = sorted(month_labels[label] for label in selected_month_labels)
                manager_month_keys = [d.strftime("%Y-%m") for d in selected_month_starts]
                first_month = selected_month_starts[0]
                last_month = selected_month_starts[-1]
                last_month_end = date(last_month.year, last_month.month, calendar.monthrange(last_month.year, last_month.month)[1])
                filter_start = max(first_month, data_min)
                filter_end = min(last_month_end, data_cutoff)
            else:
                filter_start, filter_end = data_min, data_cutoff
        else:
            week_labels = {}
            for ws, we in reversed(week_options):
                iso_week = ws.isocalendar().week
                label = f"Semana {iso_week:02d} · {ws.strftime('%d/%m')}–{we.strftime('%d/%m/%Y')}"
                week_labels[label] = (ws, we)
            selected_week_label = st.selectbox("Semana", list(week_labels.keys()), index=0)
            filter_start, filter_end = week_labels[selected_week_label]
    else:
        period_mode = st.radio("Filtrar por", ["Mes", "Semana", "Rango personalizado"], horizontal=False)
        if period_mode == "Mes":
            month_labels = {f"{MONTHS_FULL_ES[d.month]} {d.year}": d for d in reversed(month_options)}
            selected_month_label = st.selectbox("Mes", list(month_labels.keys()), index=0)
            month_start = month_labels[selected_month_label]
            month_last_day = date(month_start.year, month_start.month, calendar.monthrange(month_start.year, month_start.month)[1])
            filter_start = max(month_start, data_min)
            filter_end = min(month_last_day, data_cutoff)
        elif period_mode == "Semana":
            week_labels = {}
            for ws, we in reversed(week_options):
                iso_week = ws.isocalendar().week
                label = f"Semana {iso_week:02d} · {ws.strftime('%d/%m')}–{we.strftime('%d/%m/%Y')}"
                week_labels[label] = (ws, we)
            selected_week_label = st.selectbox("Semana", list(week_labels.keys()), index=0)
            filter_start, filter_end = week_labels[selected_week_label]
        else:
            date_range = st.date_input("Rango de fechas", value=(m_start_default, data_cutoff), min_value=data_min, max_value=data_cutoff)
            if isinstance(date_range, tuple) and len(date_range) == 2:
                filter_start, filter_end = date_range
            else:
                filter_start, filter_end = m_start_default, data_cutoff
            if filter_start > filter_end:
                filter_start, filter_end = filter_end, filter_start

    st.caption(f"Período activo: {filter_start.strftime('%d/%m/%Y')} → {filter_end.strftime('%d/%m/%Y')}")
    
    if view_mode == "Vendedor" and company_cutoffs:
        cutoff_parts = [f"{c}: {datetime.fromisoformat(d).strftime('%d/%m/%Y')}" for c, d in sorted(company_cutoffs.items()) if d]
        st.caption("Cortes: " + " · ".join(cutoff_parts))
    else:
        st.caption(f"Base completa: {data_min.strftime('%d/%m/%Y')} → {data_cutoff.strftime('%d/%m/%Y')}")
    if staleness_days > 1:
        st.warning(f"La base tiene {staleness_days} días de rezago.")

# Periodos derivados del filtro
filter_days = (filter_end - filter_start).days + 1
prev_period_end = filter_start - timedelta(days=1)
prev_period_start = prev_period_end - timedelta(days=max(filter_days - 1, 0))
last30_start = filter_end - timedelta(days=29)
prev30_end = filter_end - timedelta(days=30)
prev30_start = filter_end - timedelta(days=59)
start90 = filter_end - timedelta(days=89)
start180 = filter_end - timedelta(days=179)

if view_mode == "Vendedor":
    header_title = f"{page} · {seller_name.title()}"
    header_subtitle = "Gestión comercial accionable · ventas, clientes, devoluciones, cobertura y oportunidades de portafolio."
    header_extra = ""
else:
    header_title = f"{page} · OGSA"
    header_subtitle = "Lectura ejecutiva de proveedores, margen bruto, devoluciones, penetración, portafolio y desempeño de la fuerza de ventas."
    filters = []
    if len(manager_providers) == 1:
        filters.append(f"Proveedor: {manager_providers[0]}")
    elif len(manager_providers) > 1:
        filters.append(f"Proveedores: {len(manager_providers)} seleccionados")
    if len(manager_sellers) == 1:
        filters.append("1 vendedor seleccionado")
    elif len(manager_sellers) > 1:
        filters.append(f"Vendedores: {len(manager_sellers)} seleccionados")
    if manager_category != "Todas": filters.append(f"Categoría: {manager_category}")
    header_extra = " · ".join(filters) if filters else "Todos los proveedores · todos los vendedores"

st.markdown(
    f"""
    <div class="ogsa-header">
      <div class="ogsa-title">{html.escape(header_title)}</div>
      <div class="ogsa-subtitle">{html.escape(header_subtitle)}</div>
      <div class="ogsa-badge">Corte de datos: {pretty_date(data_cutoff)}</div>
      <div class="ogsa-badge">Filtro activo: {pretty_date(filter_start)} → {pretty_date(filter_end)}</div>
      <div class="ogsa-badge">{html.escape(header_extra)}</div>
    </div>
    """,
    unsafe_allow_html=True,
)



def filtered_metrics() -> dict:
    return rows(
        """
        SELECT
          COUNT(*) records,
          COALESCE(SUM(net_sales),0) net_sales,
          COALESCE(SUM(CASE WHEN transaction_code='VT' AND net_sales > 0 THEN net_sales ELSE 0 END),0) gross_sales,
          COALESCE(SUM(CASE WHEN transaction_code='NC' OR net_sales < 0 THEN ABS(net_sales) ELSE 0 END),0) returns,
          COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN invoice_no END) invoices,
          COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN customer_code END) customers,
          COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN category_name END) categories,
          COALESCE(SUM(CASE WHEN transaction_code='VT' AND net_sales > 0 THEN quantity ELSE 0 END),0) units
        FROM sales
        WHERE seller_code=? AND invoice_date BETWEEN ? AND ?
        """,
        (seller, iso(filter_start), iso(filter_end)),
    )[0]


def prior_period_metrics() -> dict:
    return rows(
        """
        SELECT
          COALESCE(SUM(net_sales),0) net_sales,
          COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN customer_code END) customers,
          COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN invoice_no END) invoices,
          COALESCE(SUM(CASE WHEN transaction_code='VT' AND net_sales > 0 THEN quantity ELSE 0 END),0) units
        FROM sales
        WHERE seller_code=? AND invoice_date BETWEEN ? AND ?
        """,
        (seller, iso(prev_period_start), iso(prev_period_end)),
    )[0]


def customer_health() -> list[dict]:
    customer_stats = rows(
        """
        WITH purchase_days AS (
          SELECT customer_code, MAX(customer_name) customer_name,
                 MAX(customer_address) customer_address,
                 MAX(channel) channel, invoice_date, SUM(net_sales) sales_day
          FROM sales
          WHERE seller_code=? AND transaction_code='VT' AND net_sales > 0
          GROUP BY customer_code, invoice_date
        ), stats AS (
          SELECT customer_code, MAX(customer_name) customer_name,
                 MAX(customer_address) customer_address,
                 MAX(channel) channel,
                 MIN(invoice_date) first_buy, MAX(invoice_date) last_buy,
                 COUNT(*) purchase_days, AVG(sales_day) avg_order,
                 SUM(CASE WHEN invoice_date BETWEEN ? AND ? THEN sales_day ELSE 0 END) sales30,
                 SUM(CASE WHEN invoice_date BETWEEN ? AND ? THEN sales_day ELSE 0 END) prev30,
                 SUM(CASE WHEN invoice_date BETWEEN ? AND ? THEN sales_day ELSE 0 END) sales_filtered
          FROM purchase_days
          GROUP BY customer_code
        )
        SELECT * FROM stats
        """,
        (
            seller,
            iso(last30_start), iso(filter_end),
            iso(prev30_start), iso(prev30_end),
            iso(filter_start), iso(filter_end),
        ),
    )
    out = []
    for r in customer_stats:
        last_buy = datetime.fromisoformat(r["last_buy"]).date()
        first_buy = datetime.fromisoformat(r["first_buy"]).date()
        n_days = int(r["purchase_days"] or 0)
        avg_interval = ((last_buy - first_buy).days / (n_days - 1)) if n_days > 1 else 30.0
        avg_interval = clamp(avg_interval, 3, 60)
        days_since = (filter_end - last_buy).days
        overdue_ratio = days_since / avg_interval if avg_interval else 0
        current30 = float(r["sales30"] or 0)
        previous30 = float(r["prev30"] or 0)
        drop = 1 - (current30 / previous30) if previous30 > 0 else 0
        change30 = ((current30 / previous30) - 1) * 100 if previous30 > 0 else None

        if overdue_ratio >= 2.0 or days_since >= 60:
            status = "🔴 Dormido"
        elif overdue_ratio >= 1.2:
            status = "🟠 En riesgo"
        else:
            status = "🟢 Activo"

        out.append({
            **r,
            "last_buy_date": last_buy,
            "first_buy_date": first_buy,
            "days_since": days_since,
            "avg_interval": avg_interval,
            "overdue_ratio": overdue_ratio,
            "drop": drop,
            "change30": change30,
            "status": status,
        })
    return out


def daily_series() -> list[dict]:
    return rows(
        """
        SELECT invoice_date,
               COALESCE(SUM(net_sales),0) sales,
               COALESCE(SUM(CASE WHEN transaction_code='VT' AND net_sales > 0 THEN quantity ELSE 0 END),0) units,
               COALESCE(SUM(CASE WHEN transaction_code='VT' AND net_sales > 0 THEN net_sales ELSE 0 END),0)
                 / NULLIF(COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN invoice_no END),0) ticket
        FROM sales
        WHERE seller_code=? AND invoice_date BETWEEN ? AND ?
        GROUP BY invoice_date ORDER BY invoice_date
        """,
        (seller, iso(filter_start), iso(filter_end)),
    )


def category_sales(limit: int = 10) -> list[dict]:
    return rows(
        """
        SELECT category_name AS category, COUNT(DISTINCT product_code) sku_count,
               SUM(net_sales) value
        FROM sales
        WHERE seller_code=? AND invoice_date BETWEEN ? AND ? AND transaction_code='VT' AND net_sales > 0 AND category_name<>''
        GROUP BY category_name
        ORDER BY value DESC
        LIMIT ?
        """,
        (seller, iso(filter_start), iso(filter_end), limit),
    )


def category_returns(limit: int = 10) -> list[dict]:
    return rows(
        """
        SELECT COALESCE(NULLIF(category_name,''),'SIN CATEGORÍA') AS category, COUNT(*) docs,
               SUM(ABS(net_sales)) value
        FROM sales
        WHERE seller_code=? AND invoice_date BETWEEN ? AND ? AND (transaction_code='NC' OR net_sales < 0)
        GROUP BY COALESCE(NULLIF(category_name,''),'SIN CATEGORÍA')
        ORDER BY value DESC
        LIMIT ?
        """,
        (seller, iso(filter_start), iso(filter_end), limit),
    )


def line_scatter(limit: int = 1200) -> list[dict]:
    return rows(
        """
        SELECT product_name, category_name, quantity, unit_price, net_sales
        FROM sales
        WHERE seller_code=? AND invoice_date BETWEEN ? AND ?
              AND ABS(quantity) > 0 AND ABS(unit_price) > 0
        ORDER BY ABS(net_sales) DESC
        LIMIT ?
        """,
        (seller, iso(filter_start), iso(filter_end), limit),
    )


def ranking_clients(limit: int = 15) -> list[dict]:
    return rows(
        """
        SELECT MAX(customer_name) AS label, SUM(net_sales) AS value
        FROM sales
        WHERE seller_code=? AND invoice_date BETWEEN ? AND ?
        GROUP BY customer_code
        ORDER BY value DESC
        LIMIT ?
        """,
        (seller, iso(filter_start), iso(filter_end), limit),
    )


def ranking_products(limit: int = 15) -> list[dict]:
    return rows(
        """
        SELECT product_name AS label, SUM(net_sales) AS value
        FROM sales
        WHERE seller_code=? AND invoice_date BETWEEN ? AND ? AND product_name<>''
        GROUP BY product_code, product_name
        ORDER BY value DESC
        LIMIT ?
        """,
        (seller, iso(filter_start), iso(filter_end), limit),
    )


def ranking_categories(limit: int = 15) -> list[dict]:
    return rows(
        """
        SELECT category_name AS label, SUM(net_sales) AS value
        FROM sales
        WHERE seller_code=? AND invoice_date BETWEEN ? AND ? AND category_name<>''
        GROUP BY category_name
        ORDER BY value DESC
        LIMIT ?
        """,
        (seller, iso(filter_start), iso(filter_end), limit),
    )


def ranking_lines_units(limit: int = 20) -> list[dict]:
    """Top product lines/categories by positive sold units in the active period."""
    return rows(
        """
        SELECT category_name AS label, SUM(quantity) AS value
        FROM sales
        WHERE seller_code=? AND invoice_date BETWEEN ? AND ?
              AND category_name<>'' AND transaction_code='VT' AND net_sales > 0 AND quantity > 0
        GROUP BY category_name
        HAVING SUM(quantity) > 0
        ORDER BY value DESC
        LIMIT ?
        """,
        (seller, iso(filter_start), iso(filter_end), limit),
    )


def monthly_history() -> list[dict]:
    return rows(
        """
        SELECT substr(invoice_date,1,7) month,
               SUM(net_sales) sales,
               COALESCE(SUM(CASE WHEN transaction_code='NC' OR net_sales < 0 THEN ABS(net_sales) ELSE 0 END),0) returns,
               COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales>0 THEN customer_code END) customers,
               COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales>0 THEN invoice_no END) invoices
        FROM sales
        WHERE seller_code=? AND invoice_date >= date(?, '-11 months', 'start of month')
        GROUP BY substr(invoice_date,1,7)
        ORDER BY month
        """,
        (seller, iso(filter_end)),
    )


def provider_ranking_sales(desc: bool = True, limit: int = 10) -> list[dict]:
    order = "DESC" if desc else "ASC"
    return rows(
        f"""
        SELECT provider_name AS label, SUM(net_sales) AS value
        FROM sales
        WHERE seller_code=? AND invoice_date BETWEEN ? AND ? AND provider_name<>''
        GROUP BY provider_name
        HAVING SUM(net_sales) > 0
        ORDER BY value {order}
        LIMIT ?
        """,
        (seller, iso(filter_start), iso(filter_end), limit),
    )

def provider_ranking_units(desc: bool = True, limit: int = 10) -> list[dict]:
    order = "DESC" if desc else "ASC"
    return rows(
        f"""
        SELECT provider_name AS label, SUM(quantity) AS value
        FROM sales
        WHERE seller_code=? AND invoice_date BETWEEN ? AND ?
              AND provider_name<>'' AND transaction_code='VT' AND net_sales > 0
        GROUP BY provider_name
        HAVING SUM(quantity) > 0
        ORDER BY value {order}
        LIMIT ?
        """,
        (seller, iso(filter_start), iso(filter_end), limit),
    )

def company_breakdown() -> list[dict]:
    return rows(
        """
        SELECT company AS label,
               SUM(net_sales) AS net_sales,
               SUM(CASE WHEN transaction_code='VT' AND net_sales>0 THEN net_sales ELSE 0 END) AS gross_sales,
               COALESCE(SUM(CASE WHEN transaction_code='NC' OR net_sales<0 THEN ABS(net_sales) ELSE 0 END),0) AS returns,
               SUM(CASE WHEN transaction_code='VT' AND net_sales>0 THEN quantity ELSE 0 END) AS units,
               COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales>0 THEN invoice_no END) AS invoices
        FROM sales
        WHERE seller_code=? AND invoice_date BETWEEN ? AND ?
        GROUP BY company
        ORDER BY company
        """,
        (seller, iso(filter_start), iso(filter_end)),
    )


def team_coverage() -> list[dict]:
    return rows(
        """
        WITH universe AS (
          SELECT seller_code, MAX(seller_name) seller_name,
                 COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN customer_code END) universe
          FROM sales
          GROUP BY seller_code
        ), active AS (
          SELECT seller_code,
                 COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN customer_code END) effective
          FROM sales
          WHERE invoice_date BETWEEN ? AND ?
          GROUP BY seller_code
        )
        SELECT u.seller_code, u.seller_name, u.universe,
               COALESCE(a.effective,0) effective,
               ROUND(COALESCE(a.effective,0) * 100.0 / NULLIF(u.universe,0),1) coverage_pct
        FROM universe u
        LEFT JOIN active a ON a.seller_code = u.seller_code
        WHERE u.seller_code <> ''
        ORDER BY u.universe DESC, u.seller_name
        """,
        (iso(filter_start), iso(filter_end)),
    )


def weekday_heatmap() -> tuple[list[str], list[str], list[list[float]], dict[tuple[str, str], dict]]:
    raw = rows(
        """
        SELECT seller_name,
               CASE CAST(strftime('%w', invoice_date) AS INTEGER)
                   WHEN 1 THEN 'Lunes'
                   WHEN 2 THEN 'Martes'
                   WHEN 3 THEN 'Miércoles'
                   WHEN 4 THEN 'Jueves'
                   WHEN 5 THEN 'Viernes'
                   ELSE NULL
               END AS weekday,
               COUNT(*) records,
               SUM(net_sales) value
        FROM sales
        WHERE invoice_date BETWEEN ? AND ?
              AND seller_code <> ''
        GROUP BY seller_name, weekday
        HAVING weekday IS NOT NULL
        """,
        (iso(filter_start), iso(filter_end)),
    )
    sellers = sorted({r["seller_name"] for r in raw})
    values_by_key = {(r["seller_name"], r["weekday"]): {"value": float(r["value"] or 0), "records": int(r["records"] or 0)} for r in raw}
    z = []
    for s in sellers:
        row = []
        for d in WEEKDAY_ORDER:
            row.append(values_by_key.get((s, d), {"value": 0})["value"])
        z.append(row)
    return sellers, WEEKDAY_ORDER, z, values_by_key


def manager_where(start_date: date | None = None, end_date: date | None = None, include_provider: bool = True, alias: str = ""):
    """Build a parameterized WHERE clause for the executive view."""
    explicit_period = start_date is not None or end_date is not None
    start_date = start_date or filter_start
    end_date = end_date or filter_end
    prefix = f"{alias}." if alias else ""
    clauses = [f"{prefix}invoice_date BETWEEN ? AND ?"]
    params: list = [iso(start_date), iso(end_date)]
    if not explicit_period and manager_month_keys:
        placeholders = ",".join(["?"] * len(manager_month_keys))
        clauses.append(f"substr({prefix}invoice_date,1,7) IN ({placeholders})")
        params.extend(manager_month_keys)
    if include_provider and manager_providers:
        placeholders = ",".join(["?"] * len(manager_providers))
        clauses.append(f"{prefix}provider_name IN ({placeholders})")
        params.extend(manager_providers)
    if manager_sellers:
        placeholders = ",".join(["?"] * len(manager_sellers))
        clauses.append(f"{prefix}seller_code IN ({placeholders})")
        params.extend(manager_sellers)
    if manager_category != "Todas":
        clauses.append(f"{prefix}category_name = ?")
        params.append(manager_category)
    return " AND ".join(clauses), params


def manager_metrics(start_date: date | None = None, end_date: date | None = None, include_provider: bool = True) -> dict:
    where, params = manager_where(start_date, end_date, include_provider=include_provider)
    return rows(
        f"""
        SELECT
          COUNT(*) records,
          COALESCE(SUM(net_sales),0) net_sales,
          COALESCE(SUM(CASE WHEN transaction_code='VT' AND net_sales > 0 THEN net_sales ELSE 0 END),0) gross_sales,