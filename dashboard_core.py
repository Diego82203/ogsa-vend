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
          COALESCE(SUM(CASE WHEN transaction_code='VT' AND net_sales > 0 THEN net_sales ELSE 0 END),0) gross_sales,          COALESCE(SUM(CASE WHEN transaction_code='NC' OR net_sales < 0 THEN ABS(net_sales) ELSE 0 END),0) returns,
          COALESCE(SUM(CASE WHEN net_sales <> 0 THEN net_sales - (COALESCE(unit_cost,0) * quantity) ELSE 0 END),0) gross_profit,
          COALESCE(SUM(CASE WHEN transaction_code='VT' AND net_sales > 0 THEN quantity ELSE 0 END),0) units,
          COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN invoice_no END) invoices,
          COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN customer_code END) customers,
          COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN seller_code END) sellers,
          COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN provider_name END) providers,
          COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN seller_code || '|' || customer_code || '|' || invoice_date END) impacts,
          COALESCE(SUM(CASE WHEN transaction_code='VT' AND net_sales > 0 AND unit_cost > 0 THEN net_sales ELSE 0 END),0) sales_with_cost
        FROM sales
        WHERE {where}
        """,
        tuple(params),
    )[0]


def manager_weekly_series() -> list[dict]:
    where, params = manager_where()
    return rows(
        f"""
        SELECT strftime('%Y', invoice_date) || '-W' || printf('%02d', CAST(strftime('%W', invoice_date) AS INTEGER)) AS week,
               MIN(invoice_date) week_start,
               COALESCE(SUM(net_sales),0) sales,
               COALESCE(SUM(CASE WHEN transaction_code='NC' OR net_sales < 0 THEN ABS(net_sales) ELSE 0 END),0) returns,
               COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN seller_code || '|' || customer_code || '|' || invoice_date END) impacts
        FROM sales
        WHERE {where}
        GROUP BY week
        ORDER BY week_start
        """,
        tuple(params),
    )


def manager_monthly_series(months_back: int = 12) -> list[dict]:
    where, params = manager_where(filter_end - timedelta(days=365), filter_end)
    return rows(
        f"""
        SELECT substr(invoice_date,1,7) month,
               COALESCE(SUM(net_sales),0) sales,
               COALESCE(SUM(CASE WHEN transaction_code='NC' OR net_sales < 0 THEN ABS(net_sales) ELSE 0 END),0) returns,
               COALESCE(SUM(CASE WHEN net_sales <> 0 THEN net_sales - (COALESCE(unit_cost,0) * quantity) ELSE 0 END),0) gross_profit
        FROM sales
        WHERE {where}
        GROUP BY month
        ORDER BY month
        LIMIT ?
        """,
        tuple(params + [months_back]),
    )


def manager_provider_table() -> list[dict]:
    where, params = manager_where(include_provider=True)
    prev_where, prev_params = manager_where(prev_period_start, prev_period_end, include_provider=True)
    current = rows(
        f"""
        SELECT provider_name,
               COALESCE(SUM(net_sales),0) net_sales,
               COALESCE(SUM(CASE WHEN transaction_code='VT' AND net_sales > 0 THEN net_sales ELSE 0 END),0) gross_sales,
               COALESCE(SUM(CASE WHEN transaction_code='NC' OR net_sales < 0 THEN ABS(net_sales) ELSE 0 END),0) returns,
               COALESCE(SUM(CASE WHEN net_sales <> 0 THEN net_sales - (COALESCE(unit_cost,0) * quantity) ELSE 0 END),0) gross_profit,
               COALESCE(SUM(CASE WHEN transaction_code='VT' AND net_sales > 0 THEN quantity ELSE 0 END),0) units,
               COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN customer_code END) customers,
               COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN invoice_no END) invoices,
               COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN seller_code END) sellers
        FROM sales
        WHERE {where} AND provider_name <> ''
        GROUP BY provider_name
        HAVING COALESCE(SUM(net_sales),0) <> 0
        ORDER BY net_sales DESC
        """,
        tuple(params),
    )
    previous_rows = rows(
        f"""
        SELECT provider_name, COALESCE(SUM(net_sales),0) prev_sales
        FROM sales
        WHERE {prev_where} AND provider_name <> ''
        GROUP BY provider_name
        """,
        tuple(prev_params),
    )
    prev_map = {r['provider_name']: float(r['prev_sales'] or 0) for r in previous_rows}
    # Share is always against the total company/filter base without restricting provider.
    total_base = float(manager_metrics(include_provider=False)['net_sales'] or 0)
    out = []
    for r in current:
        net = float(r['net_sales'] or 0)
        gross = float(r['gross_sales'] or 0)
        gp = float(r['gross_profit'] or 0)
        returns = float(r['returns'] or 0)
        prev = prev_map.get(r['provider_name'], 0)
        out.append({
            **r,
            'margin_pct': safe_ratio(gp, net) * 100,
            'return_pct': safe_ratio(returns, gross) * 100,
            'share_pct': safe_ratio(net, total_base) * 100,
            'growth_pct': ((net / prev) - 1) * 100 if prev else None,
            'prev_sales': prev,
        })
    return out


def manager_grouped(metric_group: str, limit: int = 10) -> list[dict]:
    where, params = manager_where()
    if metric_group == 'category':
        label_expr, group_expr = "category_name", "category_name"
    elif metric_group == 'sku':
        label_expr, group_expr = "product_name", "product_code, product_name"
    elif metric_group == 'seller':
        label_expr, group_expr = "MAX(seller_name)", "seller_code"
    elif metric_group == 'client':
        label_expr, group_expr = "MAX(customer_name)", "customer_code"
    else:
        raise ValueError(metric_group)
    return rows(
        f"""
        SELECT {label_expr} AS label,
               COALESCE(SUM(net_sales),0) value,
               COALESCE(SUM(CASE WHEN transaction_code='VT' AND net_sales > 0 THEN quantity ELSE 0 END),0) units,
               COALESCE(SUM(CASE WHEN net_sales <> 0 THEN net_sales - (COALESCE(unit_cost,0) * quantity) ELSE 0 END),0) gross_profit,
               COALESCE(SUM(CASE WHEN transaction_code='NC' OR net_sales < 0 THEN ABS(net_sales) ELSE 0 END),0) returns
        FROM sales
        WHERE {where}
        GROUP BY {group_expr}
        HAVING COALESCE(SUM(net_sales),0) > 0
        ORDER BY value DESC
        LIMIT ?
        """,
        tuple(params + [limit]),
    )


def manager_client_detail() -> list[dict]:
    """Aggregate executive/provider sales at customer level, never invoice-by-invoice.

    One impact is approximated as one customer + seller + calendar day with positive
    sales. Therefore several invoices issued to the same customer by the same seller
    on the same day still count as a single impact.
    """
    where, params = manager_where()
    return rows(
        f"""
        SELECT
          customer_code,
          MAX(customer_name) AS customer_name,
          COALESCE(SUM(net_sales),0) AS net_sales,
          COALESCE(SUM(CASE WHEN transaction_code='VT' AND net_sales > 0 THEN net_sales ELSE 0 END),0) AS gross_sales,
          COALESCE(SUM(CASE WHEN transaction_code='NC' OR net_sales < 0 THEN ABS(net_sales) ELSE 0 END),0) AS returns,
          COALESCE(SUM(CASE WHEN net_sales <> 0 THEN net_sales - (COALESCE(unit_cost,0) * quantity) ELSE 0 END),0) AS gross_profit,
          COALESCE(SUM(CASE WHEN transaction_code='VT' AND net_sales > 0 THEN quantity ELSE 0 END),0) AS units,
          COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN invoice_no END) AS invoices,
          COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN seller_code || '|' || customer_code || '|' || invoice_date END) AS impacts,
          COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN seller_code END) AS sellers,
          MAX(CASE WHEN transaction_code='VT' AND net_sales > 0 THEN invoice_date END) AS last_sale
        FROM sales
        WHERE {where} AND customer_code <> ''
        GROUP BY customer_code
        HAVING COALESCE(SUM(net_sales),0) <> 0
        ORDER BY net_sales DESC
        """,
        tuple(params),
    )


def manager_client_detail_table(title: str = "Detalle de clientes vendidos") -> None:
    detail = manager_client_detail()
    section_heading(
        title,
        "Una fila por cliente con la venta total acumulada del rango activo. No se divide por factura. Un impacto = cliente × vendedor × día, aunque existan varias facturas en ese mismo impacto.",
        chip="cliente acumulado",
    )
    if not detail:
        st.info("No hay clientes con actividad para el filtro actual.")
        return

    search_client = st.text_input(
        "Buscar cliente en el detalle",
        placeholder="Nombre o código de cliente",
        key=f"manager_client_search_{page}_{len(manager_providers)}",
    ).strip().lower()
    if search_client:
        detail = [
            r for r in detail
            if search_client in str(r['customer_code'] or '').lower()
            or search_client in str(r['customer_name'] or '').lower()
        ]

    table = []
    for r in detail:
        net = float(r['net_sales'] or 0)
        gp = float(r['gross_profit'] or 0)
        table.append({
            'Código cliente': r['customer_code'],
            'Cliente': r['customer_name'],
            'Venta neta total': round(net, 2),
            'Ganancia bruta': round(gp, 2),
            'Margen bruto': round(safe_ratio(gp, net) * 100, 2),
            'Devoluciones': round(float(r['returns'] or 0), 2),
            'Unidades': round(float(r['units'] or 0), 0),
            'Impactos': int(r['impacts'] or 0),
            'Facturas': int(r['invoices'] or 0),
            'Vendedores': int(r['sellers'] or 0),
            'Última venta': r['last_sale'],
        })

    st.dataframe(
        table,
        hide_index=True,
        use_container_width=True,
        height=min(120 + len(table) * 35, 620),
        column_config={
            'Venta neta total': st.column_config.NumberColumn(format='$%.2f'),
            'Ganancia bruta': st.column_config.NumberColumn(format='$%.2f'),
            'Margen bruto': st.column_config.NumberColumn(format='%.2f%%'),
            'Devoluciones': st.column_config.NumberColumn(format='$%.2f'),
            'Unidades': st.column_config.NumberColumn(format='%.0f'),
            'Impactos': st.column_config.NumberColumn(format='%d'),
            'Facturas': st.column_config.NumberColumn(format='%d'),
            'Vendedores': st.column_config.NumberColumn(format='%d'),
        },
    )
    st.caption(
        "Ejemplo: si un vendedor emite 3 facturas al mismo cliente el mismo día, aquí se muestran 3 facturas pero 1 impacto. La venta se presenta sumada a nivel cliente."
    )



def manager_geo_rows() -> list[dict]:
    """Customer-level sales joined to the georeferenced customer master.

    The current executive filters (period/months, sellers, providers and category)
    are applied before aggregating. One row is returned per customer, never per
    invoice, so the map remains light and the sales value is the accumulated total
    for the active filter.
    """
    where, params = manager_where(alias="s")
    return rows(
        f"""
        SELECT
          s.customer_code,
          MAX(s.customer_name) AS customer_name,
          g.geo_customer_name,
          g.business_type,
          g.latitude,
          g.longitude,
          MAX(s.city) AS city,
          MAX(s.province) AS province,
          COALESCE(SUM(s.net_sales),0) AS net_sales,
          COALESCE(SUM(CASE WHEN s.transaction_code='VT' AND s.net_sales > 0 THEN s.net_sales ELSE 0 END),0) AS gross_sales,
          COALESCE(SUM(CASE WHEN s.transaction_code='NC' OR s.net_sales < 0 THEN ABS(s.net_sales) ELSE 0 END),0) AS returns,
          COALESCE(SUM(CASE WHEN s.transaction_code='VT' AND s.net_sales > 0 THEN s.quantity ELSE 0 END),0) AS units,
          COUNT(DISTINCT CASE WHEN s.transaction_code='VT' AND s.net_sales > 0 THEN s.invoice_no END) AS invoices,
          COUNT(DISTINCT CASE WHEN s.transaction_code='VT' AND s.net_sales > 0 THEN s.seller_code || '|' || s.customer_code || '|' || s.invoice_date END) AS impacts,
          COUNT(DISTINCT CASE WHEN s.transaction_code='VT' AND s.net_sales > 0 THEN s.seller_code END) AS sellers_count,
          GROUP_CONCAT(DISTINCT CASE WHEN s.transaction_code='VT' AND s.net_sales > 0 THEN s.seller_name END) AS seller_names,
          COUNT(DISTINCT CASE WHEN s.transaction_code='VT' AND s.net_sales > 0 THEN s.provider_name END) AS providers_count,
          GROUP_CONCAT(DISTINCT CASE WHEN s.transaction_code='VT' AND s.net_sales > 0 THEN s.provider_name END) AS provider_names,
          MAX(CASE WHEN s.transaction_code='VT' AND s.net_sales > 0 THEN s.invoice_date END) AS last_sale
        FROM sales s
        LEFT JOIN customer_geo g ON g.customer_code = s.customer_code
        WHERE {where} AND s.customer_code <> ''
        GROUP BY s.customer_code, g.geo_customer_name, g.business_type, g.latitude, g.longitude
        HAVING COALESCE(SUM(CASE WHEN s.transaction_code='VT' AND s.net_sales > 0 THEN s.net_sales ELSE 0 END),0) > 0
        ORDER BY net_sales DESC
        """,
        tuple(params),
    )


def manager_geo_page() -> None:
    detail = manager_geo_rows()
    if not detail:
        st.info("No hay clientes con ventas para el filtro actual.")
        return

    geocoded = [r for r in detail if r.get('latitude') is not None and r.get('longitude') is not None]
    missing = [r for r in detail if r.get('latitude') is None or r.get('longitude') is None]
    current = manager_metrics()
    total_sales = float(current.get('net_sales') or 0)
    geo_sales = sum(float(r.get('net_sales') or 0) for r in geocoded)
    coverage_clients = safe_ratio(len(geocoded), len(detail)) * 100
    coverage_sales = safe_ratio(geo_sales, total_sales) * 100 if total_sales else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: kpi("Clientes con venta", whole(len(detail)), "clientes únicos del filtro")
    with c2: kpi("Georreferenciados", whole(len(geocoded)), "con coordenadas válidas")
    with c3: kpi("Cobertura clientes", pct_abs(coverage_clients), "clientes del filtro ubicados")
    with c4: kpi("Venta representada", pct_abs(coverage_sales), money(geo_sales))
    with c5: kpi("Sin georreferencia", whole(len(missing)), "para completar en maestro", warn=len(missing) > 0)

    section_heading(
        "Mapa de clientes",
        "Una burbuja por cliente. La venta se acumula para todo el período y filtros activos; no se dibuja una marca por factura. Los clusters se cargan solo al abrir esta página.",
        chip="georreferencia",
    )

    if not geocoded:
        st.warning("Ninguno de los clientes vendidos en este filtro tiene coordenadas válidas.")
        return

    payload = []
    denominator = total_sales if total_sales else geo_sales
    for r in geocoded:
        net = float(r.get('net_sales') or 0)
        payload.append({
            "customer_code": str(r.get('customer_code') or ''),
            "customer_name": str(r.get('customer_name') or r.get('geo_customer_name') or ''),
            "business_type": str(r.get('business_type') or ''),
            "lat": float(r['latitude']),
            "lon": float(r['longitude']),
            "city": str(r.get('city') or ''),
            "province": str(r.get('province') or ''),
            "net_sales": net,
            "gross_sales": float(r.get('gross_sales') or 0),
            "returns": float(r.get('returns') or 0),
            "units": float(r.get('units') or 0),
            "invoices": int(r.get('invoices') or 0),
            "impacts": int(r.get('impacts') or 0),
            "sellers_count": int(r.get('sellers_count') or 0),
            "seller_names": str(r.get('seller_names') or ''),
            "providers_count": int(r.get('providers_count') or 0),
            "provider_names": str(r.get('provider_names') or ''),
            "last_sale": str(r.get('last_sale') or ''),
            "share_pct": safe_ratio(net, denominator) * 100 if denominator else 0,
        })

    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    map_html = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
      <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
      <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
      <style>
        html,body,#map {{ height:100%; margin:0; font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif; }}
        #map {{ width:100%; height:660px; border-radius:14px; }}
        .leaflet-popup-content {{ min-width:270px; line-height:1.45; }}
        .og-title {{ font-weight:800; font-size:14px; color:#172033; margin-bottom:5px; }}
        .og-row {{ color:#475467; font-size:12px; margin:2px 0; }}
        .og-value {{ font-weight:700; color:#172033; }}
        .legend {{ background:white; padding:8px 10px; border-radius:10px; box-shadow:0 1px 8px rgba(0,0,0,.16); color:#475467; font-size:11px; }}
      </style>
    </head>
    <body>
      <div id="map"></div>
      <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
      <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
      <script>
        const data = {data_json};
        const esc = (s) => String(s ?? '').replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
        const money = (n) => '$' + Number(n || 0).toLocaleString('en-US', {{minimumFractionDigits:2, maximumFractionDigits:2}});
        const num = (n) => Number(n || 0).toLocaleString('en-US', {{maximumFractionDigits:0}});
        const pct = (n) => Number(n || 0).toFixed(2) + '%';

        const map = L.map('map', {{ preferCanvas:true }}).setView([-0.1807, -78.4678], 11);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
          maxZoom:19,
          attribution:'&copy; OpenStreetMap contributors'
        }}).addTo(map);

        const clusters = L.markerClusterGroup({{ chunkedLoading:true, maxClusterRadius:55, showCoverageOnHover:false }});
        data.forEach(p => {{
          const sale = Math.max(0, Number(p.net_sales || 0));
          const radius = Math.min(14, Math.max(5, 4 + Math.log10(sale + 1) * 1.8));
          const marker = L.circleMarker([p.lat, p.lon], {{
            radius:radius, color:'#0B6B42', weight:1.4, fillColor:'#159455', fillOpacity:.74
          }});
          marker.bindTooltip(`<b>${{esc(p.customer_name)}}</b><br>${{money(p.net_sales)}}`, {{direction:'top'}});
          marker.bindPopup(`
            <div class="og-title">${{esc(p.customer_name)}}</div>
            <div class="og-row">Código: <span class="og-value">${{esc(p.customer_code)}}</span></div>
            <div class="og-row">Venta neta acumulada: <span class="og-value">${{money(p.net_sales)}}</span></div>
            <div class="og-row">Participación del filtro: <span class="og-value">${{pct(p.share_pct)}}</span></div>
            <div class="og-row">Impactos: <span class="og-value">${{num(p.impacts)}}</span> · Facturas: <span class="og-value">${{num(p.invoices)}}</span></div>
            <div class="og-row">Unidades: <span class="og-value">${{num(p.units)}}</span> · Devoluciones: <span class="og-value">${{money(p.returns)}}</span></div>
            <div class="og-row">Vendedor(es): <span class="og-value">${{esc(p.seller_names)}}</span></div>
            <div class="og-row">Proveedor(es): <span class="og-value">${{num(p.providers_count)}}</span></div>
            <div class="og-row">Última venta: <span class="og-value">${{esc(p.last_sale)}}</span></div>
            ${{p.city ? `<div class="og-row">Ubicación comercial: <span class="og-value">${{esc(p.city)}}${{p.province ? ', ' + esc(p.province) : ''}}</span></div>` : ''}}
            ${{p.business_type ? `<div class="og-row">Tipo de negocio: <span class="og-value">${{esc(p.business_type)}}</span></div>` : ''}}
          `);
          clusters.addLayer(marker);
        }});
        map.addLayer(clusters);
        if (data.length) {{
          const b = clusters.getBounds();
          if (b && b.isValid()) map.fitBounds(b.pad(0.07), {{maxZoom:15}});
        }}
        const legend = L.control({{position:'bottomright'}});
        legend.onAdd = () => {{
          const div = L.DomUtil.create('div','legend');
          div.innerHTML = `<b>${{data.length.toLocaleString()}} clientes</b><br>El tamaño del punto aumenta con la venta neta.`;
          return div;
        }};
        legend.addTo(map);
      </script>
    </body>
    </html>
    """
    components.html(map_html, height=680, scrolling=False)

    st.caption(
        "El mapa usa el código de cliente para unir ventas y georreferenciación. Los filtros gerenciales de meses/rango, vendedores, proveedores y categoría se aplican antes de dibujar los puntos."
    )

    if missing:
        with st.expander(f"Clientes vendidos sin georreferencia ({len(missing)})"):
            missing_table = [{
                'Código cliente': r.get('customer_code'),
                'Cliente': r.get('customer_name'),
                'Venta neta': round(float(r.get('net_sales') or 0), 2),
                'Impactos': int(r.get('impacts') or 0),
                'Facturas': int(r.get('invoices') or 0),
                'Última venta': r.get('last_sale'),
            } for r in missing[:250]]
            st.dataframe(
                missing_table,
                hide_index=True,
                use_container_width=True,
                height=min(120 + len(missing_table) * 35, 520),
                column_config={
                    'Venta neta': st.column_config.NumberColumn(format='$%.2f'),
                    'Impactos': st.column_config.NumberColumn(format='%d'),
                    'Facturas': st.column_config.NumberColumn(format='%d'),
                },
            )

def manager_seller_table() -> list[dict]:
    where, params = manager_where()
    return rows(
        f"""
        SELECT seller_code, MAX(seller_name) seller_name,
               COALESCE(SUM(net_sales),0) net_sales,
               COALESCE(SUM(CASE WHEN transaction_code='VT' AND net_sales > 0 THEN net_sales ELSE 0 END),0) gross_sales,
               COALESCE(SUM(CASE WHEN transaction_code='NC' OR net_sales < 0 THEN ABS(net_sales) ELSE 0 END),0) returns,
               COALESCE(SUM(CASE WHEN net_sales <> 0 THEN net_sales - (COALESCE(unit_cost,0) * quantity) ELSE 0 END),0) gross_profit,
               COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN customer_code END) customers,
               COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN invoice_no END) invoices,
               COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales > 0 THEN customer_code || '|' || invoice_date END) impacts,
               COALESCE(SUM(CASE WHEN transaction_code='VT' AND net_sales > 0 THEN quantity ELSE 0 END),0) units
        FROM sales
        WHERE {where}
        GROUP BY seller_code
        HAVING COALESCE(SUM(net_sales),0) <> 0
        ORDER BY net_sales DESC
        """,
        tuple(params),
    )


def manager_penetration() -> tuple[str, float, str]:
    if manager_providers:
        num_where, num_params = manager_where(include_provider=True)
        den_where, den_params = manager_where(include_provider=False)
        numerator = scalar(
            f"SELECT COUNT(DISTINCT customer_code) FROM sales WHERE {num_where} AND transaction_code='VT' AND net_sales>0",
            tuple(num_params),
            0,
        )
        denominator = scalar(
            f"SELECT COUNT(DISTINCT customer_code) FROM sales WHERE {den_where} AND transaction_code='VT' AND net_sales>0",
            tuple(den_params),
            0,
        )
        value = safe_ratio(float(numerator), float(denominator)) * 100
        label = "Penetración de proveedor" if len(manager_providers) == 1 else "Penetración del grupo"
        return label, value, f"{int(numerator)} de {int(denominator)} clientes activos"
    providers = manager_provider_table()
    if providers:
        top = providers[0]
        return "Concentración Top proveedor", float(top['share_pct'] or 0), str(top['provider_name'])
    return "Concentración Top proveedor", 0.0, "Sin datos"


def manager_heatmap() -> tuple[list[str], list[str], list[list[float]], dict[tuple[str, str], dict]]:
    where, params = manager_where()
    raw = rows(
        f"""
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
        WHERE {where} AND seller_code <> ''
        GROUP BY seller_name, weekday
        HAVING weekday IS NOT NULL
        """,
        tuple(params),
    )
    sellers = sorted({r['seller_name'] for r in raw})
    lookup = {(r['seller_name'], r['weekday']): {'value': float(r['value'] or 0), 'records': int(r['records'] or 0)} for r in raw}
    z = [[lookup.get((s, d), {'value': 0})['value'] for d in WEEKDAY_ORDER] for s in sellers]
    return sellers, WEEKDAY_ORDER, z, lookup


def manager_provider_treemap():
    data = manager_provider_table()
    if not data:
        st.info("No hay ventas de proveedores para el filtro actual.")
        return
    labels = [r['provider_name'] for r in data if float(r['net_sales'] or 0) > 0]
    vals = [float(r['net_sales'] or 0) for r in data if float(r['net_sales'] or 0) > 0]
    if not vals:
        st.info("No hay ventas positivas para el filtro actual.")
        return
    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=[''] * len(labels),
        values=vals,
        texttemplate="%{label}<br>$%{value:,.0f}",
        hovertemplate="%{label}<br>Venta neta: $%{value:,.2f}<extra></extra>",
        marker=dict(colors=vals, colorscale=[[0, '#8CC8F8'], [0.45, '#188BF6'], [1, '#093C78']]),
    ))
    fig.update_layout(height=410, margin=dict(l=5, r=5, t=5, b=5), paper_bgcolor='white')
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


def manager_weekly_chart():
    data = manager_weekly_series()
    if not data:
        st.info("No hay actividad semanal para el filtro actual.")
        return
    fig = make_subplots(specs=[[{'secondary_y': True}]])
    x = [r['week'] for r in data]
    fig.add_trace(go.Bar(x=x, y=[r['sales'] for r in data], name='Ventas netas', marker_color='#188BF6'), secondary_y=False)
    fig.add_trace(go.Bar(x=x, y=[r['returns'] for r in data], name='Devoluciones', marker_color='#F4C000'), secondary_y=False)
    fig.add_trace(go.Scatter(x=x, y=[r['impacts'] for r in data], name='Impactos facturados', mode='lines+markers', line=dict(color='#101827', width=3)), secondary_y=True)
    fig.update_layout(
        barmode='group', height=390, margin=dict(l=20, r=20, t=10, b=20),
        paper_bgcolor='white', plot_bgcolor='white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0),
        xaxis=dict(showgrid=False),
    )
    fig.update_yaxes(title_text='USD', gridcolor='#EDF0F4', secondary_y=False)
    fig.update_yaxes(title_text='Impactos', showgrid=False, secondary_y=True)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


def manager_gauge():
    label, value, note = manager_penetration()
    fig = go.Figure(go.Indicator(
        mode='gauge+number',
        value=value,
        number={'suffix': '%', 'font': {'size': 36}},
        title={'text': f"{label}<br><span style='font-size:12px;color:#667085'>{html.escape(note)}</span>"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': '#188BF6'},
            'steps': [
                {'range': [0, 40], 'color': '#FFF0E5'},
                {'range': [40, 70], 'color': '#F2F4F7'},
                {'range': [70, 100], 'color': '#DFF3E6'},
            ],
        },
    ))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=55, b=20), paper_bgcolor='white')
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


def render_manager():
    current = manager_metrics()
    previous_m = manager_metrics(prev_period_start, prev_period_end)
    margin_pct = safe_ratio(float(current['gross_profit']), float(current['net_sales'])) * 100
    return_pct = safe_ratio(float(current['returns']), float(current['gross_sales'])) * 100
    ticket = safe_ratio(float(current['gross_sales']), float(current['invoices']))
    cost_coverage = safe_ratio(float(current['sales_with_cost']), float(current['gross_sales'])) * 100
    net_growth = ((float(current['net_sales']) / float(previous_m['net_sales'])) - 1) * 100 if previous_m['net_sales'] else None

    if page == "Resumen gerencial":
        c1, c2, c3, c4 = st.columns(4)
        with c1: kpi("Ventas netas", money(current['net_sales']), pct_delta(net_growth))
        with c2: kpi("Ganancia bruta", money(current['gross_profit']), f"Costo cubierto en {cost_coverage:.0f}% de ventas")
        with c3: kpi("Margen bruto", pct_abs(margin_pct), "ganancia bruta / venta neta", warn=margin_pct < 8)
        with c4: kpi("Devoluciones", money(current['returns']), f"{return_pct:.2f}% de ventas brutas", warn=return_pct >= 5)
        c5, c6, c7, c8 = st.columns(4)
        with c5: kpi("Impactos facturados", whole(current['impacts']), "cliente × vendedor × día; varias facturas = 1 impacto")
        with c6: kpi("Drop por factura", money(ticket), f"{whole(current['invoices'])} facturas")
        with c7: kpi("Clientes atendidos", whole(current['customers']), "clientes únicos con venta")
        with c8: kpi("Vendedores activos", whole(current['sellers']), f"{whole(current['providers'])} proveedores vendidos")

        st.markdown("<div class='manager-strip'><b>Lectura gerencial:</b> esta vista replica la lógica del Power BI histórico, pero separa ventas, margen, devoluciones, impactos facturados y penetración de proveedores en una sola capa ejecutiva.</div>", unsafe_allow_html=True)

        left, right = st.columns([1.8, 1])
        with left:
            section_heading("Ventas, devoluciones e impactos por semana", "Seguimiento semanal para detectar aceleración, caída y calidad de venta.", chip="semana")
            manager_weekly_chart()
        with right:
            manager_gauge()

        left, right = st.columns([1.45, 1])
        with left:
            section_heading("Ventas por proveedor", "Participación relativa de cada proveedor dentro del filtro actual.", chip="mix")
            manager_provider_treemap()
        with right:
            section_heading("Top categorías", "Categorías que explican mayor venta neta.", chip="top 8")
            bar_chart(manager_grouped('category', 8), 'label', 'value', '', '#188BF6', 410)

        left, right = st.columns([1, 1])
        with left:
            section_heading("Ventas por vendedor", "Lectura de ejecución comercial dentro del filtro seleccionado.", chip="FFVV")
            bar_chart(manager_grouped('seller', 10), 'label', 'value', '', '#188BF6', 410)
        with right:
            section_heading("Evolución 12 meses", "Venta neta, ganancia bruta y devoluciones.", chip="tendencia")
            hist = manager_monthly_series()
            fig = go.Figure()
            fig.add_trace(go.Bar(x=[r['month'] for r in hist], y=[r['sales'] for r in hist], name='Venta neta', marker_color='#188BF6'))
            fig.add_trace(go.Scatter(x=[r['month'] for r in hist], y=[r['gross_profit'] for r in hist], name='Ganancia bruta', line=dict(color='#14804A', width=3), mode='lines+markers'))
            fig.add_trace(go.Scatter(x=[r['month'] for r in hist], y=[r['returns'] for r in hist], name='Devoluciones', line=dict(color='#E46A1A', width=2), mode='lines+markers'))
            fig.update_layout(height=410, margin=dict(l=20, r=20, t=10, b=20), paper_bgcolor='white', plot_bgcolor='white', yaxis=dict(gridcolor='#EDF0F4'), xaxis=dict(showgrid=False), legend=dict(orientation='h', y=1.04))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        section_heading("Resumen de proveedores", "Venta, margen, devolución, volumen, clientes y crecimiento vs. período comparable.", chip="executive table")
        ptable = manager_provider_table()[:20]
        table = [{
            'Proveedor': r['provider_name'],
            'Venta neta': round(float(r['net_sales']),2),
            'Ganancia bruta': round(float(r['gross_profit']),2),
            'Margen bruto': round(float(r['margin_pct']),2),
            '% Devolución': round(float(r['return_pct']),2),
            'Unidades': round(float(r['units']),0),
            'Clientes': int(r['customers']),
            'Facturas': int(r['invoices']),
            'Participación': round(float(r['share_pct']),2),
            'Crecimiento': None if r['growth_pct'] is None else round(float(r['growth_pct']),2),
        } for r in ptable]
        st.dataframe(table, hide_index=True, use_container_width=True, height=560, column_config={
            'Venta neta': st.column_config.NumberColumn(format='$%.2f'),
            'Ganancia bruta': st.column_config.NumberColumn(format='$%.2f'),
            'Margen bruto': st.column_config.NumberColumn(format='%.2f%%'),
            '% Devolución': st.column_config.NumberColumn(format='%.2f%%'),
            'Participación': st.column_config.ProgressColumn(format='%.1f%%', min_value=0, max_value=100),
            'Crecimiento': st.column_config.NumberColumn(format='%.1f%%'),
        })
        st.markdown("<div class='manager-note'>CxC, términos de pago y visitas reales no se muestran todavía porque esos campos no forman parte de la base maestra actual. “Impactos facturados” representa actividad comercial observada por facturación, no una visita física.</div>", unsafe_allow_html=True)

    elif page == "Análisis de proveedores":
        provider_rows = manager_provider_table()
        if not provider_rows:
            st.info("No hay proveedores con actividad para el filtro actual.")
            return
        if not manager_providers:
            total = manager_metrics(include_provider=False)
            margin_total = safe_ratio(float(total['gross_profit']), float(total['net_sales'])) * 100
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: kpi("Proveedores activos", whole(total['providers']), "con venta en el período")
            with c2: kpi("Venta neta", money(total['net_sales']), "todos los proveedores")
            with c3: kpi("Ganancia bruta", money(total['gross_profit']), "venta - costo")
            with c4: kpi("Margen bruto", pct_abs(margin_total), "sobre venta neta")
            with c5: kpi("Devoluciones", money(total['returns']), f"{safe_ratio(float(total['returns']), float(total['gross_sales']))*100:.2f}%")

            section_heading("Comparativo de proveedores", "Ordena y filtra para identificar proveedores con volumen, margen, devolución o crecimiento que requieren atención.", chip="proveedores")
            table = [{
                'Proveedor': r['provider_name'],
                'Venta neta': round(float(r['net_sales']),2),
                'Ganancia bruta': round(float(r['gross_profit']),2),
                'Margen bruto': round(float(r['margin_pct']),2),
                '% Devolución': round(float(r['return_pct']),2),
                'Unidades': round(float(r['units']),0),
                'Clientes': int(r['customers']),
                'Vendedores': int(r['sellers']),
                'Participación': round(float(r['share_pct']),2),
                'Crecimiento': None if r['growth_pct'] is None else round(float(r['growth_pct']),2),
            } for r in provider_rows]
            st.dataframe(table, hide_index=True, use_container_width=True, height=650, column_config={
                'Venta neta': st.column_config.NumberColumn(format='$%.2f'),
                'Ganancia bruta': st.column_config.NumberColumn(format='$%.2f'),
                'Margen bruto': st.column_config.NumberColumn(format='%.2f%%'),
                '% Devolución': st.column_config.NumberColumn(format='%.2f%%'),
                'Participación': st.column_config.ProgressColumn(format='%.1f%%', min_value=0, max_value=100),
                'Crecimiento': st.column_config.NumberColumn(format='%.1f%%'),
            })
            left, right = st.columns(2)
            with left:
                section_heading("Top proveedores por venta neta", "Contribución comercial.")
                bar_chart([{'label':r['provider_name'],'value':r['net_sales']} for r in provider_rows[:12]], 'label','value','', '#188BF6', 470)
            with right:
                section_heading("Top proveedores por ganancia bruta", "Ganancia absoluta después de costo de producto.")
                gp_sorted = sorted(provider_rows, key=lambda r: float(r['gross_profit']), reverse=True)[:12]
                bar_chart([{'label':r['provider_name'],'value':r['gross_profit']} for r in gp_sorted], 'label','value','', '#14804A', 470)

            manager_client_detail_table("Detalle de clientes vendidos · todos los proveedores")
        elif len(manager_providers) == 1:
            r = provider_rows[0]
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: kpi("Venta neta", money(r['net_sales']), pct_delta(r['growth_pct']))
            with c2: kpi("Ganancia bruta", money(r['gross_profit']), "venta neta - costo neto")
            with c3: kpi("Margen bruto", pct_abs(r['margin_pct']), "margen del proveedor", warn=float(r['margin_pct']) < 8)
            with c4: kpi("Devoluciones", money(r['returns']), pct_abs(r['return_pct']), warn=float(r['return_pct']) >= 5)
            with c5: kpi("Participación", pct_abs(r['share_pct']), f"{int(r['customers'])} clientes")

            left, right = st.columns([1.7, 1])
            with left:
                section_heading(f"Evolución semanal · {manager_providers[0]}", "Ventas netas, devoluciones e impactos facturados.", chip="proveedor")
                manager_weekly_chart()
            with right:
                manager_gauge()

            a,b = st.columns(2)
            with a:
                section_heading("Top SKU del proveedor", "Productos que generan mayor venta neta.", chip="SKU")
                bar_chart(manager_grouped('sku', 12), 'label','value','', '#188BF6', 480)
            with b:
                section_heading("Top categorías del proveedor", "Mix de portafolio vendido.", chip="categorías")
                bar_chart(manager_grouped('category', 12), 'label','value','', '#188BF6', 480)
            a,b = st.columns(2)
            with a:
                section_heading("Vendedores que más colocan el proveedor", "Venta neta por ejecutivo comercial.", chip="FFVV")
                bar_chart(manager_grouped('seller', 12), 'label','value','', '#14804A', 480)
            with b:
                section_heading("Clientes principales", "Clientes con mayor compra del proveedor.", chip="clientes")
                bar_chart(manager_grouped('client', 12), 'label','value','', '#14804A', 480)

            manager_client_detail_table(f"Detalle de clientes vendidos · {manager_providers[0]}")

        else:  # Varios proveedores seleccionados
            group_now = manager_metrics(include_provider=True)
            group_prev = manager_metrics(prev_period_start, prev_period_end, include_provider=True)
            total_company = manager_metrics(include_provider=False)
            net = float(group_now['net_sales'] or 0)
            gp = float(group_now['gross_profit'] or 0)
            gross = float(group_now['gross_sales'] or 0)
            ret = float(group_now['returns'] or 0)
            prev_net = float(group_prev['net_sales'] or 0)
            growth = ((net / prev_net) - 1) * 100 if prev_net else None
            share = safe_ratio(net, float(total_company['net_sales'] or 0)) * 100

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1: kpi("Venta neta grupo", money(net), pct_delta(growth))
            with c2: kpi("Ganancia bruta", money(gp), "proveedores seleccionados")
            with c3: kpi("Margen bruto", pct_abs(safe_ratio(gp, net) * 100), "margen combinado")
            with c4: kpi("Devoluciones", money(ret), pct_abs(safe_ratio(ret, gross) * 100), warn=safe_ratio(ret, gross) * 100 >= 5)
            with c5: kpi("Participación", pct_abs(share), f"{len(manager_providers)} proveedores")

            section_heading("Comparativo de proveedores seleccionados", "Lectura lado a lado del grupo elegido dentro del rango de tiempo activo.", chip=f"{len(manager_providers)} proveedores")
            table = [{
                'Proveedor': r['provider_name'],
                'Venta neta': round(float(r['net_sales']),2),
                'Ganancia bruta': round(float(r['gross_profit']),2),
                'Margen bruto': round(float(r['margin_pct']),2),
                '% Devolución': round(float(r['return_pct']),2),
                'Unidades': round(float(r['units']),0),
                'Clientes': int(r['customers']),
                'Vendedores': int(r['sellers']),
                'Participación': round(float(r['share_pct']),2),
                'Crecimiento': None if r['growth_pct'] is None else round(float(r['growth_pct']),2),
            } for r in provider_rows]
            st.dataframe(table, hide_index=True, use_container_width=True, height=min(120 + len(table)*36, 520), column_config={
                'Venta neta': st.column_config.NumberColumn(format='$%.2f'),
                'Ganancia bruta': st.column_config.NumberColumn(format='$%.2f'),
                'Margen bruto': st.column_config.NumberColumn(format='%.2f%%'),
                '% Devolución': st.column_config.NumberColumn(format='%.2f%%'),
                'Participación': st.column_config.ProgressColumn(format='%.1f%%', min_value=0, max_value=100),
                'Crecimiento': st.column_config.NumberColumn(format='%.1f%%'),
            })

            left, right = st.columns([1.7, 1])
            with left:
                section_heading("Evolución semanal · grupo seleccionado", "Ventas netas, devoluciones e impactos facturados combinados.", chip="multi-proveedor")
                manager_weekly_chart()
            with right:
                manager_gauge()

            a,b = st.columns(2)
            with a:
                section_heading("Top SKU del grupo", "Productos que explican mayor venta entre los proveedores seleccionados.", chip="SKU")
                bar_chart(manager_grouped('sku', 12), 'label','value','', '#188BF6', 480)
            with b:
                section_heading("Top categorías del grupo", "Mix de categorías dentro de los proveedores seleccionados.", chip="categorías")
                bar_chart(manager_grouped('category', 12), 'label','value','', '#188BF6', 480)
            a,b = st.columns(2)
            with a:
                section_heading("Vendedores del grupo", "Ejecutivos con mayor venta de los proveedores seleccionados.", chip="FFVV")
                bar_chart(manager_grouped('seller', 12), 'label','value','', '#14804A', 480)
            with b:
                section_heading("Clientes principales del grupo", "Clientes con mayor compra combinada.", chip="clientes")
                bar_chart(manager_grouped('client', 12), 'label','value','', '#14804A', 480)

            manager_client_detail_table("Detalle de clientes vendidos · grupo seleccionado")

    elif page == "Mapa de clientes":
        manager_geo_page()

    else:  # Fuerza de ventas
        current = manager_metrics()
        sellers = manager_seller_table()
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi("Vendedores activos", whole(current['sellers']), "con facturación")
        with c2: kpi("Impactos facturados", whole(current['impacts']), "cliente × día; varias facturas = 1 impacto")
        with c3: kpi("Clientes atendidos", whole(current['customers']), "clientes únicos")
        with c4: kpi("Drop por factura", money(safe_ratio(float(current['gross_sales']), float(current['invoices']))), f"{whole(current['invoices'])} facturas")

        section_heading("Desempeño por vendedor", "Venta neta, ganancia bruta, margen, devoluciones, clientes e impactos.", chip="FFVV")
        seller_table = []
        for r in sellers:
            net=float(r['net_sales'] or 0); gross=float(r['gross_sales'] or 0); gp=float(r['gross_profit'] or 0); ret=float(r['returns'] or 0)
            seller_table.append({
                'Vendedor': r['seller_name'],
                'Venta neta': round(net,2),
                'Ganancia bruta': round(gp,2),
                'Margen bruto': round(safe_ratio(gp,net)*100,2),
                '% Devolución': round(safe_ratio(ret,gross)*100,2),
                'Clientes': int(r['customers']),
                'Impactos': int(r['impacts']),
                'Facturas': int(r['invoices']),
                'Unidades': round(float(r['units'] or 0),0),
            })
        st.dataframe(seller_table, hide_index=True, use_container_width=True, height=520, column_config={
            'Venta neta': st.column_config.NumberColumn(format='$%.2f'),
            'Ganancia bruta': st.column_config.NumberColumn(format='$%.2f'),
            'Margen bruto': st.column_config.NumberColumn(format='%.2f%%'),
            '% Devolución': st.column_config.NumberColumn(format='%.2f%%'),
        })

        left,right=st.columns([1.4,1])
        with left:
            section_heading("Mapa de calor vendedor × día", "Venta neta por día de semana para localizar concentración y huecos de actividad.", chip="heatmap")
            sellers_hm, days_hm, z, lookup = manager_heatmap()
            if z:
                hover=[]
                text=[]
                for ss in sellers_hm:
                    hrow=[]; trow=[]
                    for d in days_hm:
                        cell=lookup.get((ss,d),{'value':0,'records':0})
                        hrow.append(f"{ss}<br>{d}<br>{cell['records']} registros<br>{money(cell['value'])}")
                        trow.append(f"{cell['records']} reg.<br>{money(cell['value'],0)}")
                    hover.append(hrow); text.append(trow)
                fig=go.Figure(go.Heatmap(z=z,x=days_hm,y=sellers_hm,colorscale=[[0,'#FFF0E5'],[0.4,'#F4C000'],[1,'#14804A']],text=hover,hoverinfo='text',showscale=False))
                for yi, ss in enumerate(sellers_hm):
                    for xi, d in enumerate(days_hm):
                        fig.add_annotation(x=d,y=ss,text=text[yi][xi],showarrow=False,font=dict(size=10,color='#101827'))
                fig.update_layout(height=max(390,55*len(sellers_hm)),margin=dict(l=10,r=10,t=10,b=20),paper_bgcolor='white',plot_bgcolor='white')
                st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
            else:
                st.info("No hay datos suficientes para el mapa de calor.")
        with right:
            section_heading("Ventas por vendedor", "Ranking por venta neta del período.", chip="ranking")
            bar_chart(manager_grouped('seller', 12), 'label','value','', '#188BF6', max(390,55*min(len(sellers),12)))


if view_mode == "Gerencial":
    render_manager()
    st.divider()
    st.caption("OGSA · Dashboard gerencial V10. Ganancia bruta = venta neta − costo neto de producto. Impactos facturados son una aproximación basada en cliente × vendedor × día: varias facturas al mismo cliente en ese mismo impacto cuentan una sola vez; no son visitas físicas.")
    st.stop()


metrics = filtered_metrics()
previous = prior_period_metrics()
health = customer_health()
current_ticket = safe_ratio(metrics["gross_sales"], metrics["invoices"])
current_return_pct = safe_ratio(metrics["returns"], metrics["gross_sales"]) * 100
current_units_per_invoice = safe_ratio(metrics["units"], metrics["invoices"])
net_change = ((metrics["net_sales"] / previous["net_sales"]) - 1) * 100 if previous["net_sales"] else None
cust_change = ((metrics["customers"] / previous["customers"]) - 1) * 100 if previous["customers"] else None

# ---------- MI DÍA ----------
if page == "Mi día":
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi("Registros filtrados", whole(metrics["records"]), "observaciones activas")
    with c2:
        kpi("Ventas netas", money(metrics["net_sales"]), pct_delta(net_change))
    with c3:
        kpi("Unidades vendidas", whole(metrics["units"]), f"{current_units_per_invoice:.1f} unid/factura")
    with c4:
        kpi("N° de facturas", whole(metrics["invoices"]), "facturas emitidas")
    with c5:
        kpi("Ticket promedio", money(current_ticket), "ventas brutas / facturas")

    c6, c7, c8, c9 = st.columns(4)
    with c6:
        kpi("Clientes atendidos", whole(metrics["customers"]), pct_delta(cust_change))
    with c7:
        kpi("Devoluciones", money(metrics["returns"]), "notas de crédito", warn=metrics["returns"] > 0)
    with c8:
        kpi("% devolución", pct_abs(current_return_pct), "devoluciones / ventas brutas", warn=current_return_pct >= 5)
    with c9:
        kpi("Categorías vendidas", whole(metrics["categories"]), "catálogo activo")

    company_rows = company_breakdown()
    if company_rows:
        st.caption("Venta consolidada por empresa en el período seleccionado")
        company_cols = st.columns(max(1, len(company_rows)))
        for col, cr in zip(company_cols, company_rows):
            with col:
                kpi(cr["label"], money(cr["net_sales"]), f"{whole(cr['invoices'])} facturas · {whole(cr['units'])} unidades")

    if staleness_days > 1:
        st.markdown(
            f'<div class="status-note">⚠️ <b>Fecha de corte:</b> {data_cutoff.strftime("%d/%m/%Y")}. Los análisis se calculan con datos hasta esa fecha.</div>',
            unsafe_allow_html=True,
        )

    priorities = []
    for r in health:
        score = 0
        reasons = []
        action = "REVISAR"
        if r["overdue_ratio"] >= 1.7:
            score += 45
            reasons.append(f"{r['days_since']} días sin compra; suele recomprar cada ~{r['avg_interval']:.0f} días")
            action = "RECUPERAR"
        elif r["overdue_ratio"] >= 1.2:
            score += 28
            reasons.append(f"recompra atrasada: {r['days_since']} días sin comprar")
            action = "CONTACTAR"
        if r["drop"] >= 0.5 and float(r["prev30"] or 0) >= 20:
            score += 30
            reasons.append(f"venta últimos 30 días cayó {r['drop']*100:.0f}%")
            action = "RECUPERAR"
        elif r["drop"] >= 0.25 and float(r["prev30"] or 0) >= 20:
            score += 18
            reasons.append(f"venta últimos 30 días cayó {r['drop']*100:.0f}%")
        if score > 0:
            priorities.append({
                "score": score,
                "client": r["customer_name"],
                "action": action,
                "reason": " · ".join(reasons),
                "last_buy": r["last_buy_date"].strftime("%d/%m/%Y"),
                "avg_order": float(r["avg_order"] or 0),
                "channel": r["channel"] or "—",
            })
    priorities.sort(key=lambda x: (x["score"], x["avg_order"]), reverse=True)

    left, right = st.columns([1.55, 1])
    with left:
        section_heading("Comportamiento diario de ventas y unidades", "Ventas netas, unidades vendidas y ticket promedio por día sobre el filtro actual.", chip="serie diaria")
        two_axis_daily_chart(daily_series())
    with right:
        section_heading("Ficha del filtro actual", "Lectura compacta de ventas, devolución y cobertura comercial.", chip="síntesis")
        st.markdown("<div class='summary-card'>", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"<div class='summary-mini'><div class='label'>Ticket promedio</div><div class='value'>{money(current_ticket)}</div><div class='note'>{whole(metrics['invoices'])} facturas</div></div>", unsafe_allow_html=True)
        with m2:
            st.markdown(f"<div class='summary-mini'><div class='label'>% devolución</div><div class='value'>{pct_abs(current_return_pct)}</div><div class='note'>{money(metrics['returns'])} devueltos</div></div>", unsafe_allow_html=True)
        with m3:
            st.markdown(f"<div class='summary-mini'><div class='label'>Clientes atendidos</div><div class='value'>{whole(metrics['customers'])}</div><div class='note'>{whole(metrics['categories'])} categorías</div></div>", unsafe_allow_html=True)
        st.markdown(
            f"<p style='margin-top:14px; color:#475467; line-height:1.55;'>Con el filtro actual se analizan <b>{whole(metrics['records'])}</b> registros. "
            f"Las ventas netas alcanzan <b>{money(metrics['net_sales'])}</b>, con <b>{whole(metrics['units'])}</b> unidades vendidas en "
            f"<b>{whole(metrics['invoices'])}</b> facturas, un ticket promedio de <b>{money(current_ticket)}</b> y "
            f"<b>{whole(metrics['customers'])}</b> clientes atendidos. Las devoluciones acumulan <b>{money(metrics['returns'])}</b>.</p>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    p_left, p_right = st.columns([1, 1])
    with p_left:
        section_heading("Top 10 categorías por ventas netas", "Categorías con mayor contribución a la venta neta dentro del filtro actual.", chip="ranking")
        bar_chart(category_sales(10), "category", "value", "", "#14804A", 400)
    with p_right:
        section_heading("Categorías con mayor devolución", "Magnitud de notas de crédito por categoría, para priorizar seguimiento comercial y de calidad.", chip="devoluciones")
        bar_chart(category_returns(10), "category", "value", "", "#E46A1A", 400)

    st.write("")
    section_heading("Mapa de calor cualitativo", "Cruce entre vendedor y día de la semana según ventas netas del período filtrado. Naranja = menor desempeño; verde = mayor desempeño.", chip="vendedor × día")
    sellers_hm, days_hm, z, hm_lookup = weekday_heatmap()
    if z:
        hover = []
        annotations = []
        display_sellers = []
        for s_name in sellers_hm:
            display_sellers.append(("★ " if s_name.upper() == seller_name.upper() else "") + s_name)
            hover_row = []
            annotation_row = []
            for d in days_hm:
                cell = hm_lookup.get((s_name, d), {"value": 0, "records": 0})
                hover_row.append(f"{s_name}<br>{d}<br>Registros: {cell['records']}<br>Venta neta: {money(cell['value'])}")
                annotation_row.append(f"{cell['records']} reg.<br><b>{money(cell['value'], 0)}</b>")
            hover.append(hover_row)
            annotations.append(annotation_row)
        fig_hm = go.Figure(data=go.Heatmap(
            z=z, x=days_hm, y=display_sellers,
            colorscale=[[0, "#F97316"], [0.48, "#E5E7EB"], [1, "#14804A"]],
            text=annotations, customdata=hover, texttemplate="%{text}", textfont=dict(size=12),
            hovertemplate="%{customdata}<extra></extra>", showscale=False, xgap=5, ygap=5,
        ))
        fig_hm.update_layout(
            height=max(520, 78 * len(sellers_hm)),
            margin=dict(l=20, r=20, t=10, b=20),
            paper_bgcolor="white", plot_bgcolor="white",
            xaxis=dict(side="top", tickfont=dict(size=13), showgrid=False),
            yaxis=dict(autorange="reversed", tickfont=dict(size=12), showgrid=False),
        )        st.plotly_chart(fig_hm, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No hay datos suficientes para el mapa de calor.")

    st.write("")
    section_heading("Ranking de proveedores: ventas netas y volumen", "Comparación por ventas netas y por unidades vendidas. Incluye los proveedores con más y menos movimiento dentro del filtro actual.", chip="ventas + unidades")
    p1, p2 = st.columns(2)
    with p1:
        section_heading("Top 10 proveedores por venta neta")
        bar_chart(provider_ranking_sales(True, 10), "label", "value", "", "#14804A", 390)
    with p2:
        section_heading("Top 10 proveedores con menor venta neta")
        bar_chart(provider_ranking_sales(False, 10), "label", "value", "", "#14804A", 390)
    p3, p4 = st.columns(2)
    with p3:
        section_heading("Top 10 proveedores — mayor volumen (unidades)")
        bar_chart(provider_ranking_units(True, 10), "label", "value", "", "#14804A", 390, value_type="units")
    with p4:
        section_heading("Top 10 proveedores — menor volumen (unidades)")
        bar_chart(provider_ranking_units(False, 10), "label", "value", "", "#14804A", 390, value_type="units")

    st.write("")
    section_heading("Ranking comercial: clientes, SKU y líneas", "Clientes y SKU se ordenan por ventas netas. Las líneas se ordenan por volumen de unidades vendidas dentro del filtro actual.", chip="ventas + volumen")
    rr1, rr2 = st.columns(2)
    with rr1:
        section_heading("Top 20 clientes por ventas netas")
        bar_chart(ranking_clients(20), "label", "value", "", "#14804A", 620)
    with rr2:
        section_heading("Top 20 SKU por ventas netas")
        bar_chart(ranking_products(20), "label", "value", "", "#14804A", 620)
    section_heading("Top volumen líneas", "Líneas/categorías con mayor número de unidades vendidas en el período filtrado.")
    bar_chart(ranking_lines_units(20), "label", "value", "", "#14804A", 650, value_type="units")

    st.write("")
    section_heading("Dispersión precio–cantidad", "Cada punto representa una línea de factura: cantidad vs. precio unitario. El tamaño refleja el valor total de la línea.", chip="líneas")
    pts = line_scatter()
    if pts:
        fig_sc = go.Figure(go.Scatter(
            x=[abs(float(r["quantity"] or 0)) for r in pts],
            y=[abs(float(r["unit_price"] or 0)) for r in pts],
            mode="markers",
            marker=dict(
                size=[max(6, min(28, abs(float(r["net_sales"] or 0)) / 150)) for r in pts],
                color=["#14804A" if float(r["net_sales"] or 0) >= 0 else "#E46A1A" for r in pts],
                opacity=0.6,
            ),
            text=[f"{r['product_name']}<br>{r['category_name']}<br>Cantidad: {abs(float(r['quantity'] or 0)):.0f}<br>Precio unitario: {money(abs(float(r['unit_price'] or 0)))}<br>Valor: {money(r['net_sales'])}" for r in pts],
            hoverinfo="text",
        ))
        fig_sc.update_layout(
            height=470, margin=dict(l=20, r=20, t=10, b=20),
            paper_bgcolor="white", plot_bgcolor="white",
            xaxis=dict(title="Cantidad (unidades)", gridcolor="#EDF0F4", zeroline=False),
            yaxis=dict(title="Precio unitario (USD)", gridcolor="#EDF0F4", zeroline=False),
        )
        st.plotly_chart(fig_sc, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No hay líneas con cantidad y precio válidos para el filtro.")

    st.write("")
    section_heading("Prioridades comerciales", "Clientes que requieren acción inmediata por recompra atrasada o caída reciente.")
    if priorities:
        for item in priorities[:10]:
            priority_card(item)
    else:
        st.success("No se detectaron alertas con las reglas actuales.")


# ---------- MIS CLIENTES ----------
elif page == "Mis clientes":
    active = sum(r["status"] == "🟢 Activo" for r in health)
    risk = sum(r["status"] == "🟠 En riesgo" for r in health)
    dormant = sum(r["status"] == "🔴 Dormido" for r in health)
    with_purchase_filtered = sum(float(r["sales_filtered"] or 0) > 0 for r in health)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Cartera histórica", whole(len(health)), "clientes con compras")
    with c2:
        kpi("Activos", whole(active), "recompra dentro de patrón")
    with c3:
        kpi("En riesgo", whole(risk), "recompra atrasada", warn=risk > 0)
    with c4:
        kpi("Dormidos", whole(dormant), f"{whole(with_purchase_filtered)} compraron en el filtro", warn=dormant > 0)

    section_heading("Universo de clientes por ejecutivo: impactados y efectivos", '"Universo" es el total de clientes distintos facturados por cada ejecutivo dentro de todo el período cargado. “Impactados / efectivos” se aproxima con clientes que tuvieron al menos una venta dentro del rango filtrado.', chip="cobertura")
    cov = team_coverage()
    cov_table = []
    for r in cov:
        cov_table.append({
            "Ejecutivo": r["seller_name"],
            "Clientes efectivos": int(r["effective"] or 0),
            "Universo": int(r["universe"] or 0),
            "% Cobertura": float(r["coverage_pct"] or 0),
            "Seleccionado": "⭐" if r["seller_code"] == seller else "",
        })
    st.dataframe(
        cov_table,
        hide_index=True,
        use_container_width=True,
        height=380,
        column_config={
            "% Cobertura": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
        },
    )

    st.write("")
    f1, f2 = st.columns([1.35, 1])
    with f1:
        search = st.text_input("Buscar cliente", placeholder="Nombre o código")
    with f2:
        status_filter = st.multiselect("Estado", ["🟢 Activo", "🟠 En riesgo", "🔴 Dormido"], default=["🟢 Activo", "🟠 En riesgo", "🔴 Dormido"])

    display = []
    for r in health:
        if r["status"] not in status_filter:
            continue
        if search and search.lower() not in f"{r['customer_name']} {r['customer_code']}".lower():
            continue
        display.append({
            "Cliente": r["customer_name"],
            "Código": r["customer_code"],
            "Estado": r["status"],
            "Venta filtrada": round(float(r["sales_filtered"] or 0), 2),
            "Venta 30d": round(float(r["sales30"] or 0), 2),
            "Cambio 30d": r["change30"],
            "Días sin compra": r["days_since"],
            "Frecuencia ref.": round(r["avg_interval"]),
            "Ticket ref.": round(float(r["avg_order"] or 0), 2),
            "Canal": r["channel"] or "—",
        })
    display.sort(key=lambda x: ({"🔴 Dormido": 0, "🟠 En riesgo": 1, "🟢 Activo": 2}[x["Estado"]], -x["Días sin compra"]))
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        height=540,
        column_config={
            "Venta filtrada": st.column_config.NumberColumn(format="$%.2f"),
            "Venta 30d": st.column_config.NumberColumn(format="$%.2f"),
            "Cambio 30d": st.column_config.NumberColumn(format="%.1f%%"),
            "Ticket ref.": st.column_config.NumberColumn(format="$%.2f"),
        },
    )
    st.caption("Estado calculado con el patrón histórico de recompra de cada cliente. La frecuencia se limita a 3–60 días para evitar extremos.")


# ---------- OPORTUNIDADES ----------
elif page == "Oportunidades":
    section_heading("Siguiente mejor conversación", "Escoge un cliente y revisa qué categorías puede tener sentido explorar.")
    active_customers = rows(
        """
        SELECT customer_code, MAX(customer_name) customer_name,
               MAX(CASE WHEN transaction_code='VT' AND net_sales>0 THEN invoice_date END) last_buy
        FROM sales
        WHERE seller_code=?
        GROUP BY customer_code
        HAVING last_buy IS NOT NULL
        ORDER BY customer_name
        """,
        (seller,),
    )
    customer_map = {f"{r['customer_name']} · {r['customer_code']}": r["customer_code"] for r in active_customers}
    if not customer_map:
        st.info("No hay clientes con compras positivas para este vendedor.")
    else:
        cust_label = st.selectbox("Cliente", list(customer_map.keys()))
        customer = customer_map[cust_label]

        summary = rows(
            """
            SELECT MAX(customer_name) customer_name, MAX(channel) channel,
                   MAX(CASE WHEN transaction_code='VT' AND net_sales>0 THEN invoice_date END) last_buy,
                   COUNT(DISTINCT CASE WHEN transaction_code='VT' AND net_sales>0 AND invoice_date BETWEEN ? AND ? THEN invoice_no END) invoices90,
                   SUM(CASE WHEN invoice_date BETWEEN ? AND ? THEN net_sales ELSE 0 END) sales90,
                   COUNT(DISTINCT CASE WHEN invoice_date BETWEEN ? AND ? AND transaction_code='VT' AND net_sales>0 THEN category_name END) categories90
            FROM sales WHERE seller_code=? AND customer_code=?
            """,
            (iso(start90), iso(filter_end), iso(start90), iso(filter_end), iso(start90), iso(filter_end), seller, customer),
        )[0]
        lb = datetime.fromisoformat(summary["last_buy"]).date() if summary["last_buy"] else None
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            kpi("Venta 90 días", money(summary["sales90"]), "venta neta")
        with s2:
            kpi("Facturas 90 días", whole(summary["invoices90"]), "frecuencia reciente")
        with s3:
            kpi("Categorías 90 días", whole(summary["categories90"]), "amplitud de portafolio")
        with s4:
            note = f"{(filter_end-lb).days} días" if lb else "sin fecha"
            kpi("Última compra", lb.strftime("%d/%m/%Y") if lb else "—", note)

        opps = rows(
            """
            WITH base AS (
              SELECT DISTINCT customer_code
              FROM sales
              WHERE seller_code=? AND invoice_date BETWEEN ? AND ?
                    AND transaction_code='VT' AND net_sales>0
            ), cat AS (
              SELECT category_name,
                     COUNT(DISTINCT customer_code) customers,
                     SUM(net_sales) seller_sales
              FROM sales
              WHERE seller_code=? AND invoice_date BETWEEN ? AND ?
                    AND transaction_code='VT' AND net_sales>0 AND category_name<>''
              GROUP BY category_name
            ), mine AS (
              SELECT DISTINCT category_name
              FROM sales
              WHERE seller_code=? AND customer_code=? AND invoice_date BETWEEN ? AND ?
                    AND transaction_code='VT' AND net_sales>0
            )
            SELECT cat.category_name, cat.customers, cat.seller_sales,
                   ROUND(cat.customers * 100.0 / NULLIF((SELECT COUNT(*) FROM base),0),1) penetration,
                   (
                     SELECT brand_name FROM sales s2
                     WHERE s2.seller_code=? AND s2.category_name=cat.category_name
                           AND s2.invoice_date BETWEEN ? AND ? AND s2.transaction_code='VT' AND s2.net_sales>0
                     GROUP BY brand_name ORDER BY SUM(s2.net_sales) DESC LIMIT 1
                   ) top_brand,
                   (
                     SELECT product_name FROM sales s3
                     WHERE s3.seller_code=? AND s3.category_name=cat.category_name
                           AND s3.invoice_date BETWEEN ? AND ? AND s3.transaction_code='VT' AND s3.net_sales>0
                     GROUP BY product_name ORDER BY SUM(s3.net_sales) DESC LIMIT 1
                   ) top_product
            FROM cat
            LEFT JOIN mine ON mine.category_name=cat.category_name
            WHERE mine.category_name IS NULL
            ORDER BY penetration DESC, seller_sales DESC
            LIMIT 12
            """,
            (
                seller, iso(start180), iso(filter_end),
                seller, iso(start180), iso(filter_end),
                seller, customer, iso(start180), iso(filter_end),
                seller, iso(start180), iso(filter_end),
                seller, iso(start180), iso(filter_end),
            ),
        )
        table = [{
            "Categoría sugerida": r["category_name"],
            "Producto referencia": r["top_product"] or "—",
            "Marca referencia": r["top_brand"] or "—",
            "Penetración cartera": r["penetration"] or 0,
            "Clientes que compran": r["customers"],
        } for r in opps]

        left, right = st.columns([1.35, 1])
        with left:
            section_heading("Oportunidades de portafolio", "Categorías ausentes en 180 días que sí rotan en la cartera del vendedor.")
            if table:
                st.dataframe(
                    table,
                    use_container_width=True,
                    hide_index=True,
                    height=435,
                    column_config={
                        "Penetración cartera": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                    },
                )
            else:
                st.success("El cliente ya cubre las principales categorías de la cartera en los últimos 180 días.")
        with right:
            section_heading("Lo que ya compra", "Top categorías del cliente en los últimos 90 días.")
            bought = rows(
                """
                SELECT category_name Categoría, SUM(net_sales) Venta
                FROM sales
                WHERE seller_code=? AND customer_code=? AND invoice_date BETWEEN ? AND ?
                      AND transaction_code='VT' AND net_sales>0 AND category_name<>''
                GROUP BY category_name ORDER BY Venta DESC LIMIT 10
                """,
                (seller, customer, iso(start90), iso(filter_end)),
            )
            st.dataframe(
                bought,
                use_container_width=True,
                hide_index=True,
                height=435,
                column_config={"Venta": st.column_config.NumberColumn(format="$%.2f")},
            )
        st.caption("Estas sugerencias son reglas de cross-sell basadas en penetración histórica; no sustituyen criterio comercial, disponibilidad, canal ni restricciones de portafolio.")


# ---------- MI DESEMPEÑO ----------
elif page == "Mi desempeño":
    section_heading("Mapa de calor cualitativo", "Cruce entre vendedor y día de la semana según ventas netas del período filtrado.", chip="vendedor × día")
    sellers_hm, days_hm, z, hm_lookup = weekday_heatmap()
    if z:
        hover = []
        annotations = []
        display_sellers = []
        for s_name in sellers_hm:
            display_sellers.append(("★ " if s_name.upper() == seller_name.upper() else "") + s_name)
            hover_row = []
            annotation_row = []
            for d in days_hm:
                cell = hm_lookup.get((s_name, d), {"value": 0, "records": 0})
                hover_row.append(f"{s_name}<br>{d}<br>Registros: {cell['records']}<br>Venta neta: {money(cell['value'])}")
                annotation_row.append(f"{cell['records']} reg.<br><b>{money(cell['value'], 0)}</b>")
            hover.append(hover_row)
            annotations.append(annotation_row)
        fig_hm = go.Figure(data=go.Heatmap(
            z=z,
            x=days_hm,
            y=display_sellers,
            colorscale=[[0, "#F97316"], [0.48, "#E5E7EB"], [1, "#14804A"]],
            text=annotations,
            customdata=hover,
            texttemplate="%{text}",
            textfont=dict(size=11),
            hovertemplate="%{customdata}<extra></extra>",
            showscale=False,
            xgap=4, ygap=4,
        ))
        fig_hm.update_layout(
            height=max(480, 72 * len(sellers_hm)),
            margin=dict(l=20, r=20, t=10, b=20),
            paper_bgcolor="white", plot_bgcolor="white",
            xaxis=dict(side="top", tickfont=dict(size=12), showgrid=False),
            yaxis=dict(autorange="reversed", tickfont=dict(size=11), showgrid=False),
        )
        st.plotly_chart(fig_hm, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No hay datos suficientes para el mapa de calor.")

    h_left, h_right = st.columns([1, 1])
    with h_left:
        section_heading("Dispersión precio–cantidad", "Cada punto representa una línea de factura: cantidad vs. precio unitario. El tamaño refleja el valor total de la línea.", chip="líneas")
        pts = line_scatter()
        if pts:
            fig_sc = go.Figure(go.Scatter(
                x=[abs(float(r["quantity"] or 0)) for r in pts],
                y=[abs(float(r["unit_price"] or 0)) for r in pts],
                mode="markers",
                marker=dict(
                    size=[max(6, min(28, abs(float(r["net_sales"] or 0)) / 150)) for r in pts],
                    color=["#14804A" if float(r["net_sales"] or 0) >= 0 else "#E46A1A" for r in pts],
                    opacity=0.6,
                ),
                text=[f"{r['product_name']}<br>{r['category_name']}<br>Cantidad: {abs(float(r['quantity'] or 0)):.0f}<br>Precio unitario: {money(abs(float(r['unit_price'] or 0)))}<br>Valor: {money(r['net_sales'])}" for r in pts],
                hoverinfo="text",
            ))
            fig_sc.update_layout(
                height=420,
                margin=dict(l=20, r=20, t=10, b=20),
                paper_bgcolor="white",
                plot_bgcolor="white",
                xaxis=dict(title="Cantidad (unidades)", gridcolor="#EDF0F4", zeroline=False),
                yaxis=dict(title="Precio unitario (USD)", gridcolor="#EDF0F4", zeroline=False),
            )
            st.plotly_chart(fig_sc, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No hay líneas con cantidad y precio válidos para el filtro.")
    with h_right:
        section_heading("Evolución mensual", "Venta neta y devoluciones de los últimos 12 meses.", chip="tendencia")
        months = monthly_history()
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[r["month"] for r in months], y=[r["sales"] for r in months], name="Venta neta", marker_color="#14804A"
        ))
        fig.add_trace(go.Scatter(
            x=[r["month"] for r in months], y=[r["returns"] for r in months], name="Devoluciones", line=dict(color="#E46A1A", width=3), mode="lines+markers"
        ))
        fig.update_layout(height=420, margin=dict(l=20, r=20, t=10, b=20), paper_bgcolor="white", plot_bgcolor="white", yaxis=dict(gridcolor="#EDF0F4", zeroline=False), xaxis=dict(showgrid=False))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.write("")
    section_heading("Ranking de proveedores: ventas netas y volumen", "Comparación por ventas netas y por unidades vendidas. Se muestran los proveedores con más y con menos movimiento dentro del filtro actual.", chip="ventas + unidades")
    p1, p2 = st.columns(2)
    with p1:
        section_heading("Top 10 proveedores por venta neta")
        bar_chart(provider_ranking_sales(True, 10), "label", "value", "", "#14804A", 360)
    with p2:
        section_heading("Top 10 proveedores con menor venta neta")
        bar_chart(provider_ranking_sales(False, 10), "label", "value", "", "#14804A", 360)
    p3, p4 = st.columns(2)
    with p3:
        section_heading("Top 10 proveedores — mayor volumen (unidades)")
        bar_chart(provider_ranking_units(True, 10), "label", "value", "", "#14804A", 360, value_type="units")
    with p4:
        section_heading("Top 10 proveedores — menor volumen (unidades)")
        bar_chart(provider_ranking_units(False, 10), "label", "value", "", "#14804A", 360, value_type="units")

    st.write("")
    section_heading("Ranking comercial: clientes, SKU y líneas", "Clientes y SKU se ordenan por ventas netas. Las líneas se ordenan por volumen de unidades vendidas dentro del filtro actual.", chip="ventas + volumen")
    r1, r2 = st.columns(2)
    with r1:
        section_heading("Top 20 clientes por ventas netas")
        bar_chart(ranking_clients(20), "label", "value", "", "#14804A", 600)
    with r2:
        section_heading("Top 20 SKU por ventas netas")
        bar_chart(ranking_products(20), "label", "value", "", "#14804A", 600)

    st.write("")
    section_heading("Top volumen líneas", "Líneas/categorías con mayor número de unidades vendidas en el período filtrado.")
    bar_chart(ranking_lines_units(20), "label", "value", "", "#14804A", 620, value_type="units")

st.divider()
st.caption("OGSA · V5 de gestión comercial. Todos los módulos solicitados también se muestran en Mi día: filtros por mes/semana/rango, devoluciones, heatmap ampliado, dispersión y rankings de proveedores/clientes/SKU/categorías. Las alertas de recompra y cross-sell son reglas de apoyo y deben validarse con el equipo comercial.")