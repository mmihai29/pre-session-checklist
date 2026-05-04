# Forex Analysis Dashboard

Multi-page Streamlit dashboard pentru analiza Forex (EURUSD, GER40), cu:

- 📋 **Pre-Session Checklist** — analiză 1W → 1D → 4h, sesiuni per dată + pair, auto-save
- 📅 **Economic Calendar** — ForexFactory JSON feed cu filtre (currencies + impact)
- 📰 **News EURUSD** — FXStreet RSS, filtrat pe articole EUR/USD
- 📰 **News GER40** — FXStreet (DAX) + Investing.com Europa (context macro)

Backend de date **dual-mode**: SQLite local (default) sau Postgres remote (când `DATABASE_URL` e setat).

## Rulare locală

```bash
pip install -r requirements.txt
streamlit run app.py
```

Browserul se deschide la `http://localhost:8501`. Datele sunt în `data/sessions.db`.

Există și un shortcut: dublu-click pe **"Pre-Session Checklist"** de pe Desktop (sau pe `start_app.bat`).

## Deploy pe Streamlit Cloud (PWA pe telefon)

### Pas 1 — Bază de date persistentă

Pe Streamlit Cloud filesystem-ul e efemer; SQLite local s-ar reseta la fiecare restart. Foloseste un Postgres gratuit (Supabase sau Neon).

**Supabase (recomandat, mai simplu):**
1. Cont la https://supabase.com → New project (alege regiunea cea mai apropiată).
2. După ce e gata: Settings → Database → **Connection string** → copiază `URI` (form: `postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres`).
3. Înlocuiește `[YOUR-PASSWORD]` cu parola pe care ai pus-o la creare.

**Neon (alternativă):**
1. Cont la https://neon.tech → New project.
2. Copiază connection string-ul direct din dashboard.

### Pas 2 — Deploy pe Streamlit Cloud

1. Mergi la https://share.streamlit.io → Sign in with GitHub.
2. **New app** → repository: `mmihai29/pre-session-checklist`, branch: `main`, main file: `app.py`.
3. Click **Advanced settings** → **Secrets** → lipește:
   ```toml
   DATABASE_URL = "postgresql://...stringul-tau..."
   ```
4. Click **Deploy**. În 2-3 min ai un URL `https://<nume>.streamlit.app`.

### Pas 3 — Instalează ca PWA pe telefon

1. Deschide URL-ul app-ului în Chrome (Android) sau Safari (iOS).
2. Meniu (⋮ / share) → **Add to Home Screen** / **Install app**.
3. Apare ca aplicație nativă, fullscreen, fără bara browser.

### Limitarea accesului (opțional)

În Streamlit Cloud → app → **Settings** → **Sharing** → "Allow only specific emails" → adaugă emailul tău. Apoi doar tu te poți autentifica.

## Personalizare checklist

Editează [`checklists.yaml`](checklists.yaml). Structura:

```yaml
tabs:
  - id: tab1
    title: "..."
    sections:
      - id: section_id
        title: "..."
        items:
          - id: stable_id      # NU schimba după ce ai date — devine cheie în DB
            label: "..."
            hint: "..."
```

⚠ **Important**: dacă schimbi `id`-ul unui item, istoricul pentru acel item se pierde (cheia devine alta). Schimbă liber `label` și `hint`.

## Structură fișiere

```
.
├── app.py                          # Home (preview cards)
├── checklists.yaml                 # definiția checklist-urilor
├── requirements.txt
├── start_app.bat                   # Windows shortcut helper
├── .streamlit/
│   └── secrets.toml.example        # template pentru DATABASE_URL
├── pages/
│   ├── 1_Pre_Session.py
│   ├── 2_Economic_Calendar.py
│   ├── 3_News_EURUSD.py
│   └── 4_News_GER40.py
└── src/
    ├── config.py                   # YAML loader
    ├── db.py                       # SQLite / Postgres dual-mode
    └── feeds.py                    # ForexFactory + FXStreet + Investing fetchers
```

## Backend & date

- Toate fetcher-ele cache 5 min (`@st.cache_data(ttl=300)`).
- ForexFactory are un disk-cache fallback — dacă feed-ul răspunde 429 (rate limit), pagina afișează ultimul snapshot bun cu o notă "stale".
- DB local: `data/sessions.db`. Pentru backup, copiază acel fișier. Reset complet: șterge folder-ul `data/`.
