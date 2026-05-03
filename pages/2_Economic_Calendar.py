"""Economic calendar page — pulls ForexFactory RSS feed for the current week."""
from collections import defaultdict
from datetime import datetime

import streamlit as st

from src import feeds

st.set_page_config(
    page_title="Economic Calendar | Forex",
    page_icon="📅",
    layout="wide",
)

ALL_CURRENCIES = ["AUD", "CAD", "CHF", "CNY", "EUR", "GBP", "JPY", "NZD", "USD"]
DEFAULT_CURRENCIES = {"EUR", "USD"}
ALL_IMPACTS = [("high", "🔴 High"), ("medium", "🟠 Medium"), ("low", "🟡 Low"), ("holiday", "⚪ Holiday")]
DEFAULT_IMPACTS = {"high", "medium"}


# ---------- sidebar filters ----------
with st.sidebar:
    st.title("📅 Calendar Filters")

    st.subheader("Currencies")
    cols = st.columns(2)
    selected_currencies: set[str] = set()
    for i, c in enumerate(ALL_CURRENCIES):
        with cols[i % 2]:
            if st.checkbox(c, value=(c in DEFAULT_CURRENCIES), key=f"cur_{c}"):
                selected_currencies.add(c)

    st.divider()
    st.subheader("Impact")
    selected_impacts: set[str] = set()
    for code, label in ALL_IMPACTS:
        if st.checkbox(label, value=(code in DEFAULT_IMPACTS), key=f"imp_{code}"):
            selected_impacts.add(code)

    st.divider()
    if st.button("🔄 Refresh feed", use_container_width=True):
        feeds.fetch_forexfactory_calendar.clear()
        st.rerun()

# ---------- main ----------
st.title("📅 Economic Calendar — ForexFactory")
st.caption("Sursă: nfs.faireconomy.media · refresh la 5 min")

try:
    events = feeds.fetch_forexfactory_calendar()
except Exception as exc:  # noqa: BLE001
    st.error(f"Nu s-a putut încărca feed-ul ForexFactory: {exc}")
    st.stop()

if not events:
    st.warning("Feed-ul ForexFactory este gol sau indisponibil. Reîncearcă mai târziu.")
    st.stop()

if events and events[0].get("stale"):
    fetched_at = events[0].get("fetched_at")
    age_str = ""
    if fetched_at:
        delta = datetime.now(fetched_at.tzinfo) - fetched_at
        mins = int(delta.total_seconds() // 60)
        age_str = f" (snapshot vechi de {mins} min)"
    st.warning(
        f"⚠ Sursa ForexFactory limitează cererile (HTTP 429); afișez ultimele date salvate"
        f"{age_str}. Folosește **Refresh** mai târziu."
    )

filtered = feeds.filter_calendar(events, currencies=selected_currencies, impacts=selected_impacts)

st.metric("Evenimente afișate", f"{len(filtered)} / {len(events)}")
st.divider()

if not filtered:
    st.info("Niciun eveniment nu corespunde filtrelor. Bifează mai multe currencies / impact levels.")
    st.stop()

# Group by weekday + date for cronological day headers.
by_day: dict[str, list[dict]] = defaultdict(list)
order: list[str] = []
for ev in filtered:
    label = (
        f"{ev['weekday']} · {ev['date']}" if ev["weekday"] and ev["date"]
        else (ev["date"] or "—")
    )
    if label not in by_day:
        order.append(label)
    by_day[label].append(ev)

for d in order:
    rows = by_day[d]
    st.subheader(d)
    for ev in rows:
        with st.container(border=True):
            cols = st.columns([0.10, 0.10, 0.10, 0.50, 0.20])
            cols[0].markdown(f"**{ev['time'] or '—'}**")
            cols[1].markdown(ev["impact_icon"])
            cols[2].markdown(f"**{ev['currency']}**")
            title_md = f"**{ev['title']}**"
            if ev.get("link"):
                title_md = f"**[{ev['title']}]({ev['link']})**"
            cols[3].markdown(title_md)
            stats = []
            if ev["forecast"]:
                stats.append(f"F: {ev['forecast']}")
            if ev["previous"]:
                stats.append(f"P: {ev['previous']}")
            cols[4].caption(" · ".join(stats) if stats else "—")

st.divider()
st.caption(f"Generat la {datetime.now().strftime('%H:%M:%S')}")
