"""GER40 news page — FXStreet for DAX/GER40 plus a wider European-markets feed."""
import streamlit as st

from src import feeds

st.set_page_config(
    page_title="News GER40 | Forex",
    page_icon="📰",
    layout="wide",
)

DAX_KEYWORDS = ["DAX", "GER40", "GER 40", "DE40", "German index", "Germany 40"]
EU_CONTEXT_KEYWORDS = ["German", "Germany", "ECB", "Eurozone", "Europe", "EU "]
PAGE_SIZE = 10

with st.sidebar:
    st.title("📰 GER40 Filters")
    extra_search = st.text_input("🔍 Caută în titlu / sumar", "")
    if st.button("🔄 Refresh feeds", use_container_width=True):
        feeds.fetch_fxstreet_news.clear()
        feeds.fetch_european_markets_news.clear()
        st.rerun()

st.title("📰 News GER40 / DAX")
st.caption("FXStreet (DAX-tagged) + Investing.com Europa (context macro) · cache 5 min")

tab_direct, tab_context = st.tabs(["DAX/GER40 Direct (FXStreet)", "European Markets Context"])


def _render_news(items: list[dict], page_key: str):
    if not items:
        st.info("Niciun articol nu corespunde filtrelor curente.")
        return
    total_pages = (len(items) + PAGE_SIZE - 1) // PAGE_SIZE
    page_num = st.number_input(
        "Pagina", min_value=1, max_value=max(total_pages, 1), value=1, step=1, key=page_key
    )
    start = (page_num - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    for art in items[start:end]:
        with st.container(border=True):
            st.markdown(f"### [{art['title']}]({art['link']})")
            if art["published_human"]:
                st.caption(f"🕒 {art['published_human']}")
            if art["summary"]:
                st.write(art["summary"])
            if art["tags"]:
                st.caption("Tags: " + " · ".join(art["tags"][:6]))
    st.caption(f"Pagina {page_num} din {total_pages}")


with tab_direct:
    try:
        all_news = feeds.fetch_fxstreet_news()
    except Exception as exc:  # noqa: BLE001
        st.error(f"FXStreet indisponibil: {exc}")
        all_news = []

    direct = feeds.filter_news_by_keywords(all_news, DAX_KEYWORDS)
    if extra_search.strip():
        direct = feeds.filter_news_by_keywords(direct, [extra_search.strip()])

    st.metric("Articole DAX/GER40 (FXStreet)", f"{len(direct)}")
    st.divider()
    _render_news(direct, page_key="ger40_direct_page")


with tab_context:
    try:
        eu_news = feeds.fetch_european_markets_news()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Feed european indisponibil: {exc}")
        eu_news = []

    ctx = feeds.filter_news_by_keywords(eu_news, EU_CONTEXT_KEYWORDS) if eu_news else []
    # If context filter eats too much (some feeds tag broadly), fall back to all entries.
    if eu_news and len(ctx) < 3:
        ctx = eu_news
    if extra_search.strip():
        ctx = feeds.filter_news_by_keywords(ctx, [extra_search.strip()])

    st.metric("Articole context (Europa)", f"{len(ctx)}")
    st.divider()
    _render_news(ctx, page_key="ger40_context_page")
