"""EURUSD news page — pulls FXStreet RSS and filters EUR/USD-relevant articles."""
import streamlit as st

from src import feeds

st.set_page_config(
    page_title="News EURUSD | Forex",
    page_icon="📰",
    layout="wide",
)

EURUSD_KEYWORDS = ["EURUSD", "EUR/USD", "EUR-USD", "Euro Dollar", "EUR USD"]
PAGE_SIZE = 10

with st.sidebar:
    st.title("📰 EURUSD Filters")
    extra_search = st.text_input("🔍 Caută în titlu / sumar", "")
    if st.button("🔄 Refresh feed", use_container_width=True):
        feeds.fetch_fxstreet_news.clear()
        st.rerun()

st.title("📰 News EURUSD — FXStreet")
st.caption("Sursă: fxstreet.com/rss/news · refresh la 5 min · click pe titlu deschide articolul")

try:
    all_news = feeds.fetch_fxstreet_news()
except Exception as exc:  # noqa: BLE001
    st.error(f"Nu s-a putut încărca feed-ul FXStreet: {exc}")
    st.stop()

if not all_news:
    st.warning("Feed-ul FXStreet este gol sau indisponibil. Reîncearcă mai târziu.")
    st.stop()

filtered = feeds.filter_news_by_keywords(all_news, EURUSD_KEYWORDS)
if extra_search.strip():
    filtered = feeds.filter_news_by_keywords(filtered, [extra_search.strip()])

st.metric("Articole găsite", f"{len(filtered)}")
st.divider()

if not filtered:
    st.info("Niciun articol nu corespunde filtrelor curente.")
    st.stop()

# pagination
total_pages = (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE
page_num = st.number_input(
    "Pagina", min_value=1, max_value=max(total_pages, 1), value=1, step=1
)
start = (page_num - 1) * PAGE_SIZE
end = start + PAGE_SIZE

for art in filtered[start:end]:
    with st.container(border=True):
        st.markdown(f"### [{art['title']}]({art['link']})")
        if art["published_human"]:
            st.caption(f"🕒 {art['published_human']}")
        if art["summary"]:
            st.write(art["summary"])
        if art["tags"]:
            st.caption("Tags: " + " · ".join(art["tags"][:6]))

st.caption(f"Pagina {page_num} din {total_pages}")
