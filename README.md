# Fluggastrechte-RAG

Ein RAG-gestützter (Retrieval-Augmented Generation) Q&A-Assistent zu Fluggastrechten
nach der EU-Verordnung 261/2004. Beantwortet Fragen zu Verspätung, Annullierung,
Nichtbeförderung und Ausgleichsansprüchen — jede Antwort mit nachvollziehbarem
Normen- bzw. Urteilsverweis, keine freihändigen Behauptungen.

> ⚠️ Dieses Tool dient der technischen Demonstration und ersetzt keine Rechtsberatung.

## Warum dieses Projekt

Fluggastrechte sind ein eng abgegrenzter, aber praktisch hoch relevanter
Rechtsbereich mit klarer Normstruktur (VO 261/2004) und einer überschaubaren
Zahl prägender EuGH-Urteile. Das macht ihn gut geeignet, um zu zeigen, wie sich
ein RAG-System so bauen lässt, dass es **nicht halluziniert** — eine der
zentralen Anforderungen an Legal-Tech-Anwendungen.

## Architektur

```
Nutzerfrage
    │
    ▼
[Retrieval]  ──►  Chroma Vector Store  ──►  Top-k relevante Chunks
    │                                       (VO-Artikel / Urteile / FAQ)
    ▼
[Generation]  ──►  Claude API (mit Chunks als Kontext)
    │
    ▼
Antwort + Quellenangabe(n)
```

**Wissensbasis** (`data/raw/`):
- VO (EG) Nr. 261/2004 — Volltext, pro Artikel gechunkt
- Zentrale EuGH-Urteile: Sturgeon (C-402/07), Wallentin-Hermann (C-549/07),
  van der Lans (C-257/14)
- FAQ-Fallbeispiele aus typischen Praxisanfragen (Verspätung, außergewöhnliche
  Umstände, Nichtbeförderung)

**Warum Chroma statt FAISS:** Chroma bringt Metadaten-Filterung (Dokumenttyp,
Quelle, Artikelnummer) und Persistenz direkt mit — dadurch lässt sich das
Retrieval gezielt auf Normtext vs. Rechtsprechung vs. FAQ einschränken, und
jede Antwort bleibt bis zur Quelle zurückverfolgbar.

## Setup

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env  # ANTHROPIC_API_KEY eintragen

# Wissensbasis einmalig indexieren
python src/ingest.py

# App starten
streamlit run src/app.py
```

## Features

- **Quellenangaben unter jeder Antwort** — welcher Artikel / welches Urteil /
  welcher FAQ-Eintrag tatsächlich zur Antwort beigetragen hat
- **Retrieval-Ansicht** — Umschalten zwischen finaler Antwort und den rohen
  retrievten Chunks, zur Nachvollziehbarkeit
- **Eval-Set** (`eval/testset.jsonl`) — vordefinierte Testfragen mit
  Erwartungswert, per Klick in der App durchlaufbar

## Projektstruktur

```
flightright-rag/
├── data/
│   ├── raw/            # Quelldokumente (VO-Text, Urteile, FAQ)
│   └── processed/       # gechunkte + indexierte Daten
├── src/
│   ├── ingest.py         # Chunking + Embedding + Indexierung
│   ├── retrieve.py       # Retrieval-Logik
│   ├── generate.py       # Claude-API-Aufruf mit Kontext
│   └── app.py             # Streamlit-Frontend
├── eval/
│   └── testset.jsonl     # Testfragen mit erwarteter Antwort/Quelle
├── requirements.txt
└── .env.example
```

## Nächste Schritte / Roadmap

- [x] VO 261/2004 Volltext einpflegen und pro Artikel chunken (Art. 5/7/8/9 zusätzlich pro Absatz, siehe data/raw/vo_261_2004.json)
- [x] EuGH-Urteile aufbereiten (Leitsätze extrahieren) – Sturgeon, Wallentin-Hermann, van der Lans (data/raw/eugh_urteile.json)
- [x] FAQ-Fallbeispiele aus Praxiserfahrung ergänzen (data/raw/faq.json)
- [x] Eval-Set mit 10–15 Testfragen aufbauen (eval/testset.jsonl, 15 Fragen)
- [x] Confidence-Anzeige, wenn Retrieval keine passenden Chunks findet (Distanz-Schwellenwert in retrieve.py, fester Fallback-Text in generate.py statt API-Call)
- [ ] Embedding-Modell gegen ein für Deutsch optimiertes Modell tauschen (aktuell all-MiniLM-L6-v2, englisch trainiert – TODO in ingest.py)

## Tech Stack

Python · Chroma · Claude API · Streamlit
