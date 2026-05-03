"""Home / landing page for the Forex Analysis Dashboard.

The actual analytical workflow lives in the `pages/` folder — Streamlit
auto-discovers them and renders the sidebar navigation.
"""
from datetime import datetime, timezone
import streamlit as st

from src import config, db, feeds

st.set_page_config(
    page_title="Forex Analysis Dashboard",
    page_icon="📊",
    layout="wide",
)

db.init_db()
TABS = config.load_checklists()
TOTAL_ITEMS = config.total_items(TABS)


# ---------- sidebar ----------
with st.sidebar:
    st.title("📊 Forex Dashboard")
    st.caption("EURUSD · GER40")
    st.divider()
    st.markdown(
        "Folosește meniul de mai sus pentru a naviga între:\n\n"
        "- 📋 **Pre-Session** — checklist de analiză\n"
        "- 📅 **Economic Calendar** — știri ForexFactory\n"
        "- 📰 **News EURUSD** — FXStreet\n"
        "- 📰 **News GER40** — FXStreet + macro EU"
    )

# ---------- main ----------
st.title("📊 Forex Analysis Dashboard")
st.caption(f"Astăzi: {datetime.now().strftime('%A, %d %B %Y · %H:%M')}")
st.divider()

col1, col2 = st.columns(2)

# --- Pre-Session preview ---
with col1:
    with st.container(border=True):
        st.subheader("📋 Pre-Session Analysis")
        sessions = db.list_sessions(limit=5)
        if not sessions:
            st.caption("Nicio sesiune încă. Deschide pagina **Pre-Session** ca să începi.")
        else:
            latest = sessions[0]
            done = latest["done"]
            pct = int((done / TOTAL_ITEMS) * 100) if TOTAL_ITEMS else 0
            st.metric(
                f"Ultima sesiune · {latest['pair']}",
                f"{done}/{TOTAL_ITEMS}",
                f"{pct}% complet",
            )
            st.caption(f"Data: {latest['date']}")
            st.markdown("**Sesiuni recente:**")
            for s in sessions[:5]:
                d = s["done"]
                p = int((d / TOTAL_ITEMS) * 100) if TOTAL_ITEMS else 0
                st.caption(f"• {s['date']} · {s['pair']} — {d}/{TOTAL_ITEMS} ({p}%)")
        st.page_link("pages/1_Pre_Session.py", label="Deschide Pre-Session →")

# --- Calendar preview ---
with col2:
    with st.container(border=True):
        st.subheader("📅 Economic Calendar")
        try:
            events = feeds.fetch_forexfactory_calendar()
            high = feeds.filter_calendar(
                events, currencies={"EUR", "USD"}, impacts={"high"}
            )
            if not high:
                st.caption("Niciun eveniment High-impact (EUR/USD) în săptămâna curentă.")
            else:
                st.caption(f"**Top {min(5, len(high))} evenimente High-impact (EUR/USD):**")
                for ev in high[:5]:
                    st.markdown(
                        f"{ev['impact_icon']} **{ev['currency']}** · "
                        f"{ev['date']} {ev['time']} — {ev['title']}"
                    )
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Calendarul nu a putut fi încărcat: {exc}")
        st.page_link("pages/2_Economic_Calendar.py", label="Vezi tot calendarul →")

st.divider()

col3, col4 = st.columns(2)

# --- EURUSD news preview ---
with col3:
    with st.container(border=True):
        st.subheader("📰 News EURUSD")
        try:
            news = feeds.fetch_fxstreet_news()
            eur = feeds.filter_news_by_keywords(
                news, ["EURUSD", "EUR/USD", "EUR-USD", "Euro"]
            )[:3]
            if not eur:
                st.caption("Niciun articol EURUSD în feed-ul curent.")
            else:
                for art in eur:
                    st.markdown(f"**[{art['title']}]({art['link']})**")
                    st.caption(f"_{art['published_human']}_")
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Feed-ul de știri nu a putut fi încărcat: {exc}")
        st.page_link("pages/3_News_EURUSD.py", label="Toate știrile EURUSD →")

# --- GER40 news preview ---
with col4:
    with st.container(border=True):
        st.subheader("📰 News GER40")
        try:
            news = feeds.fetch_fxstreet_news()
            dax = feeds.filter_news_by_keywords(
                news, ["DAX", "GER40", "DE40", "German"]
            )[:3]
            if not dax:
                st.caption("Niciun articol DAX/GER40 în feed-ul curent.")
            else:
                for art in dax:
                    st.markdown(f"**[{art['title']}]({art['link']})**")
                    st.caption(f"_{art['published_human']}_")
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Feed-ul de știri nu a putut fi încărcat: {exc}")
        st.page_link("pages/4_News_GER40.py", label="Toate știrile GER40 →")

st.divider()
st.caption(
    "💾 Date local-only (SQLite) · 📡 Surse externe: ForexFactory RSS, FXStreet RSS, "
    "Investing.com RSS · Cache 5 min"
)
