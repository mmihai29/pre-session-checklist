"""RSS feed fetchers for the dashboard.

All fetchers are wrapped with Streamlit caching (5 min TTL) so the app
does not spam external feeds. Fetchers return plain dicts so they remain
easy to test outside Streamlit.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import unescape
from typing import Iterable

import feedparser
import streamlit as st

FF_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
FXSTREET_NEWS_URL = "https://www.fxstreet.com/rss/news"
INVESTING_EUROPE_URL = "https://www.investing.com/rss/news_25.rss"  # Forex / Europe news

USER_AGENT = "Mozilla/5.0 (compatible; PreSessionChecklist/1.0)"

# Disk cache for the FF calendar (helps when remote rate-limits us with 429).
from pathlib import Path  # noqa: E402

_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
FF_CACHE_PATH = _CACHE_DIR / "ff_calendar.json"


class FeedError(RuntimeError):
    """Raised when a remote feed cannot be fetched. Carries a short user-facing reason."""


def _http_get(url: str, timeout: int = 15) -> bytes:
    """Fetch a URL with a real User-Agent header. Raises FeedError on common failures."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise FeedError("rate limited (HTTP 429) — încearcă din nou în 1-2 minute") from e
        raise FeedError(f"HTTP {e.code} — {e.reason}") from e
    except urllib.error.URLError as e:
        raise FeedError(f"network error — {e.reason}") from e
    except TimeoutError as e:
        raise FeedError("timeout — feed-ul nu a răspuns în 15s") from e


# ---------- helpers ----------

def _entry_published(entry) -> datetime | None:
    """feedparser exposes parsed time tuples on common keys."""
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        t = entry.get(key)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _human_age(dt: datetime | None) -> str:
    if dt is None:
        return ""
    now = datetime.now(timezone.utc)
    delta = now - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return "acum câteva secunde"
    if secs < 3600:
        return f"acum {secs // 60} min"
    if secs < 86400:
        return f"acum {secs // 3600} h"
    days = secs // 86400
    if days == 1:
        return "ieri"
    if days < 7:
        return f"acum {days} zile"
    return dt.strftime("%d %b %Y")


# ---------- ForexFactory calendar ----------

# Impact label normalisation (FF uses "High", "Medium", "Low", "Holiday").
IMPACT_NORM = {
    "high": "high",
    "medium": "medium",
    "low": "low",
    "holiday": "holiday",
    "non-economic": "holiday",
}

IMPACT_ICON = {
    "high": "🔴",
    "medium": "🟠",
    "low": "🟡",
    "holiday": "⚪",
}


def _parse_ff_datetime(value: str) -> datetime | None:
    """ForexFactory ISO timestamps look like "2026-05-05T08:30:00-04:00"."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _read_ff_disk_cache() -> tuple[list, datetime] | None:
    if not FF_CACHE_PATH.exists():
        return None
    try:
        with open(FF_CACHE_PATH, "r", encoding="utf-8") as f:
            blob = json.load(f)
        ts = datetime.fromisoformat(blob["fetched_at"])
        return blob["data"], ts
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        return None


def _write_ff_disk_cache(data: list) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    blob = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    try:
        with open(FF_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(blob, f)
    except OSError:
        pass  # disk-cache is best-effort


@st.cache_data(ttl=300, show_spinner=False)
def fetch_forexfactory_calendar() -> list[dict]:
    """Return this-week ForexFactory events as a list of dicts.

    Source: official JSON feed at faireconomy.media. On remote failure (e.g. 429
    rate limit) falls back to the on-disk last-good snapshot if available.
    Each row carries a ``stale`` flag (True only when served from disk fallback).
    Raises FeedError only when both remote and disk snapshot are unavailable.
    """
    raw_data: list | None = None
    stale = False
    fetched_at: datetime | None = None
    try:
        raw = _http_get(FF_CALENDAR_URL)
        try:
            raw_data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise FeedError("response was not valid JSON") from e
        if not isinstance(raw_data, list):
            raise FeedError("unexpected response shape (not a list)")
        _write_ff_disk_cache(raw_data)
        fetched_at = datetime.now(timezone.utc)
    except FeedError:
        cached = _read_ff_disk_cache()
        if cached is None:
            raise
        raw_data, fetched_at = cached
        stale = True

    data = raw_data

    rows: list[dict] = []
    for ev in data:
        impact_raw = (ev.get("impact") or "").lower()
        impact = IMPACT_NORM.get(impact_raw, impact_raw or "low")
        dt = _parse_ff_datetime(ev.get("date", ""))
        rows.append({
            "title": (ev.get("title") or "").strip(),
            "currency": (ev.get("country") or "").upper(),
            "date": dt.strftime("%a, %d %b %Y") if dt else "",
            "time": dt.strftime("%H:%M") if dt else "",
            "weekday": dt.strftime("%A") if dt else "",
            "sort_key": dt or datetime.min.replace(tzinfo=timezone.utc),
            "impact": impact,
            "impact_icon": IMPACT_ICON.get(impact, "•"),
            "forecast": ev.get("forecast", "") or "",
            "previous": ev.get("previous", "") or "",
            "link": "",
            "published": dt,
            "stale": stale,
            "fetched_at": fetched_at,
        })
    rows.sort(key=lambda r: r["sort_key"])
    return rows


def filter_calendar(
    entries: Iterable[dict],
    currencies: set[str] | None = None,
    impacts: set[str] | None = None,
) -> list[dict]:
    """Filter calendar rows by currency and impact level (in-memory)."""
    out = []
    for row in entries:
        if currencies and row["currency"] not in currencies:
            continue
        if impacts and row["impact"] not in impacts:
            continue
        out.append(row)
    return out


# ---------- News (FXStreet + fallback Europe feed) ----------

def _normalize_news_entry(entry) -> dict:
    summary = _strip_html(entry.get("summary", "") or entry.get("description", ""))
    if len(summary) > 280:
        summary = summary[:277] + "..."
    published = _entry_published(entry)
    tags = [t.term for t in entry.get("tags", []) if hasattr(t, "term")]
    return {
        "title": entry.get("title", "").strip(),
        "summary": summary,
        "link": entry.get("link", ""),
        "published": published,
        "published_human": _human_age(published),
        "tags": tags,
    }


def _matches_any(text: str, needles: Iterable[str]) -> bool:
    haystack = text.lower()
    return any(n.lower() in haystack for n in needles)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_fxstreet_news() -> list[dict]:
    """Fetch the main FXStreet news feed; returns normalised dicts."""
    parsed = feedparser.parse(FXSTREET_NEWS_URL)
    if parsed.bozo and not parsed.entries:
        return []
    return [_normalize_news_entry(e) for e in parsed.entries]


@st.cache_data(ttl=300, show_spinner=False)
def fetch_european_markets_news() -> list[dict]:
    """Fallback feed (Investing.com forex/Europe) for GER40 macro context."""
    parsed = feedparser.parse(INVESTING_EUROPE_URL)
    if parsed.bozo and not parsed.entries:
        return []
    return [_normalize_news_entry(e) for e in parsed.entries]


def filter_news_by_keywords(entries: Iterable[dict], keywords: Iterable[str]) -> list[dict]:
    """Keep entries whose title/summary/tags match any of the given keywords."""
    needles = list(keywords)
    out = []
    for e in entries:
        blob = " ".join([e.get("title", ""), e.get("summary", ""), " ".join(e.get("tags", []))])
        if _matches_any(blob, needles):
            out.append(e)
    return out
