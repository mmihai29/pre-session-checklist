from datetime import date, datetime
import streamlit as st

from src import config, db

st.set_page_config(
    page_title="Pre-Session Checklist | Trading",
    page_icon="📋",
    layout="wide",
)

# ---------- init ----------
db.init_db()
TABS = config.load_checklists()
TOTAL = config.total_items(TABS)


def state_key(prefix: str, item_key: str) -> str:
    return f"{prefix}::{item_key}"


def on_change(session_id: int, item_key: str):
    checked = st.session_state.get(state_key("chk", item_key), False)
    note = st.session_state.get(state_key("note", item_key), "")
    db.upsert_item(session_id, item_key, checked, note)


# ---------- sidebar ----------
with st.sidebar:
    st.title("📋 Pre-Session")
    st.caption("Trading checklist · 1W → 1D → 4h")

    st.subheader("Sesiune curentă")
    selected_date = st.date_input("Data", value=date.today(), format="YYYY-MM-DD")

    pairs = db.list_pairs()
    pair = st.selectbox("Pair", pairs, index=0 if pairs else None)

    with st.expander("➕ Adaugă pair nou"):
        new_pair = st.text_input("Simbol (ex: NZDUSD)", key="new_pair_input")
        if st.button("Adaugă", use_container_width=True):
            if new_pair.strip():
                db.add_pair(new_pair)
                st.rerun()

    st.divider()

    st.subheader("📚 Istoric sesiuni")
    sessions = db.list_sessions(limit=30)
    if not sessions:
        st.caption("Nicio sesiune salvată încă.")
    else:
        for s in sessions:
            done = s["done"]
            total = TOTAL
            pct = int((done / total) * 100) if total else 0
            label = f"{s['date']} · {s['pair']} — {done}/{total} ({pct}%)"
            if s["date"] == selected_date.isoformat() and s["pair"] == pair:
                st.markdown(f"**▶ {label}**")
            else:
                st.caption(label)

# ---------- main ----------
session_id = db.get_or_create_session(selected_date, pair) if pair else None

if not session_id:
    st.warning("Adaugă cel puțin un pair în sidebar pentru a începe.")
    st.stop()

state = db.load_state(session_id)

# Prime session state from DB on first load per session
prime_marker = f"primed::{session_id}"
if not st.session_state.get(prime_marker):
    for key in config.iter_item_keys(TABS):
        s = state.get(key, {"checked": False, "note": ""})
        st.session_state[state_key("chk", key)] = s["checked"]
        st.session_state[state_key("note", key)] = s["note"]
    st.session_state[prime_marker] = True

# Header
total_done = sum(1 for k in config.iter_item_keys(TABS) if state.get(k, {}).get("checked"))
header_left, header_right = st.columns([3, 1])
with header_left:
    st.title("Pre-Session Checklist")
    st.caption(
        f"📅 {selected_date.strftime('%A, %d %B %Y')} · 💱 **{pair}** · "
        f"Sesiunea #{session_id}"
    )
with header_right:
    st.metric("Progres total", f"{total_done}/{TOTAL}")
    st.progress(total_done / TOTAL if TOTAL else 0)

st.divider()

# Action buttons
col_a, col_b, col_c = st.columns([1, 1, 4])
with col_a:
    if st.button("🔄 Reset sesiune", use_container_width=True):
        db.reset_session(session_id)
        st.session_state.pop(prime_marker, None)
        st.rerun()
with col_b:
    older = [s for s in db.list_sessions(50) if s["id"] != session_id]
    if older:
        with st.popover("📋 Duplică din...", use_container_width=True):
            options = {f"{s['date']} · {s['pair']}": s["id"] for s in older}
            choice = st.selectbox("Sursă", list(options.keys()), key="dup_source")
            if st.button("Copiază bifările", key="dup_btn"):
                db.duplicate_session(options[choice], session_id)
                st.session_state.pop(prime_marker, None)
                st.rerun()

# Tabs
tab_objects = st.tabs([t["title"] for t in TABS])

for tab_obj, tab_def in zip(tab_objects, TABS):
    with tab_obj:
        if tab_def.get("description"):
            st.markdown(f"_{tab_def['description']}_")
        if tab_def.get("warning"):
            st.warning(f"⚠ {tab_def['warning']}")

        # Per-tab progress
        tab_keys = config.tab_item_keys(tab_def)
        tab_done = sum(1 for k in tab_keys if st.session_state.get(state_key("chk", k)))
        tab_total = len(tab_keys)
        st.caption(f"**Progres tab:** {tab_done}/{tab_total}")
        st.progress(tab_done / tab_total if tab_total else 0)

        st.markdown("##### Actions to do on Chart")

        for section in tab_def.get("sections", []):
            with st.container(border=True):
                st.markdown(f"**{section.get('icon', '•')} {section['title']}**")
                for idx, item in enumerate(section["items"], start=1):
                    item_key = f"{tab_def['id']}.{section['id']}.{item['id']}"
                    chk_k = state_key("chk", item_key)
                    note_k = state_key("note", item_key)

                    cols = st.columns([0.05, 0.55, 0.40])
                    with cols[0]:
                        st.checkbox(
                            " ",
                            key=chk_k,
                            label_visibility="collapsed",
                            on_change=on_change,
                            args=(session_id, item_key),
                        )
                    with cols[1]:
                        st.markdown(f"**{idx}. {item['label']}**")
                        if item.get("hint"):
                            st.caption(f"💡 {item['hint']}")
                    with cols[2]:
                        st.text_input(
                            "Notă",
                            key=note_k,
                            label_visibility="collapsed",
                            placeholder="ex: 1.0850 — 1W SSL",
                            on_change=on_change,
                            args=(session_id, item_key),
                        )

st.divider()
st.caption(
    f"💾 Salvare automată în SQLite local · Ultima actualizare: "
    f"{datetime.now().strftime('%H:%M:%S')}"
)
