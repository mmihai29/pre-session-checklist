# Pre-Session Checklist — Trading Forex

Dashboard local cu checklist pre-sesiune pentru analiză de trading (1W → 1D → 4h),
cu istoric per zi + pair, notițe scurte și auto-save în SQLite.

## Rulare

1. (Opțional) Creează un virtualenv:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   ```

2. Instalează dependențele:
   ```bash
   pip install -r requirements.txt
   ```

3. Pornește app-ul:
   ```bash
   streamlit run app.py
   ```

   Browserul se va deschide automat la `http://localhost:8501`.

## Cum se folosește

1. În sidebar alegi **data** și **pair-ul** → se creează automat o sesiune.
2. Bifezi fiecare item pe măsură ce îl marchezi pe chart-ul TradingView.
3. Adaugi opțional o notă scurtă (ex: `1.0850 — 1W SSL`).
4. Totul se salvează automat. Poți închide browserul oricând.
5. Schimbi data/pair-ul → încarci/creezi altă sesiune.
6. Istoricul ultimelor sesiuni e vizibil în sidebar cu progres %.
7. **Duplică din...** copiază bifările/notele dintr-o sesiune anterioară (util pentru același pair la zile diferite).

## Personalizare checklist

Edită `checklists.yaml`. Structura:

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

⚠ **Important**: dacă schimbi `id`-ul unui item, istoricul pentru acel item se pierde (cheia devine alta). Schimbă liber `label` și `hint` — acelea sunt doar prezentare.

## Structură fișiere

```
.
├── app.py              # UI Streamlit
├── checklists.yaml     # definiția tab-urilor & itemilor
├── requirements.txt
├── data/sessions.db    # creat automat la prima rulare
└── src/
    ├── config.py       # loader YAML
    └── db.py           # SQLite CRUD
```

## Date și backup

Toate datele sunt în `data/sessions.db`. Pentru backup, copiază acel fișier.
Pentru reset complet, șterge-l (sau șterge folder-ul `data/`).
