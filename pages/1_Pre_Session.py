from datetime import date, datetime
import streamlit as st

from src import config, db

st.set_page_config(
    page_title="Pre-Session Checklist | Trading",
    page_icon="📋",
    layout="wide",
)

# ---------- mobile-friendly CSS ----------
st.markdown(
    """
    <style>
    /* Tighter padding on small screens */
    @media (max-width: 768px) {
        .block-container { padding: 1rem 0.75rem 4rem 0.75rem !important; }
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3, h4, h5 { font-size: 1.05rem !important; }
        [data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    }
    /* Bigger touch target for checkboxes */
    [data-testid="stCheckbox"] label { min-height: 38px; }
    [data-testid="stCheckbox"] svg { width: 26px; height: 26px; }
    /* Radio buttons -> stacked, full-width pills on mobile */
    div[role="radiogroup"] { gap: 0.4rem; }
    div[role="radiogroup"] label {
        background: rgba(255,255,255,0.04);
        padding: 0.55rem 0.75rem;
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.08);
        width: 100%;
    }
    /* Progress bar a touch chunkier */
    [data-testid="stProgress"] > div > div > div { height: 10px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- init ----------
db.init_db()
TABS = config.load_checklists()
TOTAL = config.total_items(TABS)

ALLOWED_PAIRS = ["EURUSD", "GER40"]
for _p in ALLOWED_PAIRS:
    db.add_pair(_p)


def state_key(prefix: str, item_key: str) -> str:
    return f"{prefix}::{item_key}"


def on_change(session_id: int, item_key: str):
    checked = st.session_state.get(state_key("chk", item_key), False)
    db.upsert_item(session_id, item_key, checked, "")


# ---------- sidebar ----------
with st.sidebar:
    st.title("📋 Pre-Session")
    st.caption("Trading checklist · 1W → 1D → 4h")

    st.subheader("Sesiune curentă")
    selected_date = st.date_input("Data", value=date.today(), format="YYYY-MM-DD")
    pair = st.selectbox("Pair", ALLOWED_PAIRS, index=0)

    st.divider()

    st.subheader("📚 Istoric sesiuni")
    sessions = db.list_sessions(limit=30)
    sessions = [s for s in sessions if s["pair"] in ALLOWED_PAIRS]
    if not sessions:
        st.caption("Nicio sesiune salvată încă.")
    else:
        for s in sessions:
            done = s["done"]
            pct = int((done / TOTAL) * 100) if TOTAL else 0
            label = f"{s['date']} · {s['pair']} — {done}/{TOTAL} ({pct}%)"
            if s["date"] == selected_date.isoformat() and s["pair"] == pair:
                st.markdown(f"**▶ {label}**")
            else:
                st.caption(label)

# ---------- main ----------
session_id = db.get_or_create_session(selected_date, pair)
state = db.load_state(session_id)

# Prime session state from DB on first load per session
prime_marker = f"primed::{session_id}"
if not st.session_state.get(prime_marker):
    for key in config.iter_item_keys(TABS):
        s = state.get(key, {"checked": False})
        st.session_state[state_key("chk", key)] = s["checked"]
    st.session_state[prime_marker] = True

# Header
total_done = sum(
    1 for k in config.iter_item_keys(TABS) if st.session_state.get(state_key("chk", k))
)
pct_total = int((total_done / TOTAL) * 100) if TOTAL else 0

st.title("Pre-Session Checklist")
st.caption(
    f"📅 {selected_date.strftime('%A, %d %B %Y')} · 💱 **{pair}** · "
    f"Sesiunea #{session_id}"
)

# Single global progress bar (covers all tabs)
st.progress(total_done / TOTAL if TOTAL else 0, text=f"Progres total: {total_done}/{TOTAL} ({pct_total}%)")

# Action buttons
col_a, col_b = st.columns(2)
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

st.divider()

# ---------- Tab selector (vertical-friendly on mobile) ----------
tab_titles = [t["title"] for t in TABS]
# annotate each title with its progress
annotated = []
for t in TABS:
    keys = config.tab_item_keys(t)
    done = sum(1 for k in keys if st.session_state.get(state_key("chk", k)))
    mark = "✅" if done == len(keys) and len(keys) > 0 else f"{done}/{len(keys)}"
    annotated.append(f"{mark}  ·  {t['title']}")

selected_label = st.radio(
    "Alege secțiunea:",
    annotated,
    index=0,
    label_visibility="collapsed",
)
selected_idx = annotated.index(selected_label)
tab_def = TABS[selected_idx]

# ---------- selected tab content ----------
if tab_def.get("description"):
    st.markdown(f"_{tab_def['description']}_")
if tab_def.get("warning"):
    st.warning(f"⚠ {tab_def['warning']}")

st.markdown("##### Actions to do on Chart")

for section in tab_def.get("sections", []):
    with st.container(border=True):
        st.markdown(f"**{section.get('icon', '•')} {section['title']}**")
        for idx, item in enumerate(section["items"], start=1):
            item_key = f"{tab_def['id']}.{section['id']}.{item['id']}"
            chk_k = state_key("chk", item_key)

            cols = st.columns([0.12, 0.88])
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

st.divider()

# ---------- finalize ----------
if total_done == TOTAL and TOTAL > 0:
    st.success(f"🎉 **Toate cele {TOTAL} verificări sunt bifate!** Sesiunea este completă.")
    st.balloons() if not st.session_state.get(f"celebrated::{session_id}") else None
    st.session_state[f"celebrated::{session_id}"] = True
    if st.button("✅ Marchează sesiune ca finalizată", type="primary", use_container_width=True):
        st.toast("Sesiune salvată — succes la trade! 🚀", icon="✅")
else:
    remaining = TOTAL - total_done
    st.info(f"📌 Mai sunt **{remaining}** verificări de bifat înainte de finalizare.")
    st.button(
        f"✅ Trimite ({total_done}/{TOTAL})",
        disabled=True,
        use_container_width=True,
        help="Bifează toate verificările pentru a putea finaliza.",
    )

st.caption(
    f"💾 Salvare automată ({db.backend_info()}) · Ultima actualizare: "
    f"{datetime.now().strftime('%H:%M:%S')}"
)
