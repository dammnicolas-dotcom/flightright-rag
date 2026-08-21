# Fluggastrechte-RAG

Ein RAG-gestützter (Retrieval-Augmented Generation) Q&A-Assistent zu Fluggastrechten
nach der EU-Verordnung 261/2004. Beantwortet Fragen zu Verspätung, Annullierung,
Nichtbeförderung und Ausgleichsansprüchen — jede Antwort mit nachvollziehbarem
Normen- bzw. Urteilsverweis, keine freihändigen Behauptungen.

> ⚠️ Dieses Tool dient der technischen Demonstration und ersetzt keine Rechtsberatung.

**🔗 Live-Demo:** [flightright-rag-mdnjskkogjm2acvcaydpkm.streamlit.app](https://flightright-rag-mdnjskkogjm2acvcaydpkm.streamlit.app)
(passwortgeschützt, siehe [Deployment](#deployment-auf-streamlit-community-cloud))

## Warum dieses Projekt

Fluggastrechte sind ein eng abgegrenzter, aber praktisch hoch relevanter
Rechtsbereich mit klarer Normstruktur (VO 261/2004) und einer überschaubaren
Zahl prägender EuGH-Urteile. Das macht ihn gut geeignet, um zu zeigen, wie sich
ein RAG-System so bauen lässt, dass es **nicht halluziniert** — eine der
zentralen Anforderungen an Legal-Tech-Anwendungen.

## Architektur

Multi-Agenten-System: ein Orchestrator klassifiziert jede Anfrage und routet sie an
einen von zwei Spezialagenten. Welcher Agent gerade was tut, ist in der UI live als
Agent-Flow sichtbar (Streamlit `st.status`).

**📐 Interaktives Architekturdiagramm:** [claude.ai/code/artifact/c903f5a7-c46c-4928-926d-719965d6782a](https://claude.ai/code/artifact/c903f5a7-c46c-4928-926d-719965d6782a)

```
Fluggast ──► Chat-Agent ──► Orchestrator ──► Klassifikationsagent
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
             Retrieval-Agent               EU261-Agent
                    │                     │           │
             Chroma Vector Store    Chroma Vector   AviationStack
             (VO-Art. / Urteile /   Store (VO/EuGH) (echter Flugstatus:
              FAQ)                                   Verspätung/Annullierung)
```

- **Klassifikationsagent** entscheidet: allgemeine Fluggastrechte-Frage vs. konkrete
  Entschädigungsprüfung zu einem bestimmten Flug (und extrahiert dabei Flugnummer +
  Datum, falls vorhanden).
- **Retrieval-Agent** beantwortet allgemeine Fragen wie bisher rein aus der
  Wissensbasis.
- **EU261-Agent** holt zusätzlich den echten Flugstatus über die AviationStack-API ab
  und bewertet den Ausgleichsanspruch anhand von Flugfakten + einschlägigen
  Rechtsauszügen. Fehlen Flugnummer/Datum in der Frage, fragt der Orchestrator gezielt
  nach, statt zu raten.
- **Chat-Agent** übernimmt Dialogführung und finale Antwortaufbereitung in der UI.

Nicht Teil des aktuellen Umfangs: ein **Buchungsagent** mit echtem PNR-Zugriff (keine
erreichbare, nicht-proprietäre Datenquelle dafür vorhanden) und ein
**Eskalationsagent** für Human Handoff (kein Ticket-System angebunden) — siehe Roadmap.

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

cp .env.example .env  # ANTHROPIC_API_KEY + AVIATIONSTACK_API_KEY eintragen
cp .streamlit/secrets.toml.example .streamlit/secrets.toml  # APP_PASSWORD eintragen

# Wissensbasis einmalig indexieren
python src/ingest.py

# App starten
streamlit run src/app.py
```

Die App ist per Passwort geschützt (`APP_PASSWORD` in `.streamlit/secrets.toml`), damit nicht jeder mit dem Link unkontrolliert den hinterlegten `ANTHROPIC_API_KEY` verbraucht.

## Deployment auf Streamlit Community Cloud

**Status: bereits live** unter
[flightright-rag-mdnjskkogjm2acvcaydpkm.streamlit.app](https://flightright-rag-mdnjskkogjm2acvcaydpkm.streamlit.app)
— erreichbar auch ohne laufenden lokalen Rechner (z.B. für ein
Bewerbungsgespräch). Bei jedem Push auf `main` deployt Streamlit automatisch
neu.

So wurde es eingerichtet (relevant z.B. bei einem Fork oder Neuaufsetzen):

1. Repo zu GitHub pushen (bereits erledigt für dieses Repo).
2. Auf [share.streamlit.io](https://share.streamlit.io) mit GitHub einloggen.
3. **New app** → Repository `dammnicolas-dotcom/flightright-rag` auswählen
   (bei privatem Repo: Zugriff für die Streamlit-GitHub-App im Dialog
   erlauben) → Branch `main` → Main file path `src/app.py`.
4. Unter **Advanced settings → Secrets** im TOML-Format eintragen:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   AVIATIONSTACK_API_KEY = "..."
   APP_PASSWORD = "..."
   ```
   (Streamlit stellt diese Werte automatisch auch als Umgebungsvariablen
   bereit, `generate.py` liest `ANTHROPIC_API_KEY` daher unverändert über
   `os.environ`.)
5. **Deploy** klicken. Der Wissensbasis-Index wird beim ersten Start
   automatisch aufgebaut (`ensure_index_built()` in `app.py`), da
   `data/processed/chroma/` bewusst nicht im Repo liegt.

## Features

- **Agent-Flow live sichtbar** — die UI zeigt während jeder Anfrage schrittweise, welcher
  Agent gerade was tut (Klassifikation → Retrieval- oder EU261-Agent → Chat-Agent)
- **Echter Flugstatus für Entschädigungsfragen** — der EU261-Agent prüft bei Fragen zu
  einem konkreten Flug den tatsächlichen Verspätungs-/Annullierungsstatus über eine
  externe API, statt nur allgemein zu antworten
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
│   ├── agents/
│   │   ├── classifier.py       # Klassifikationsagent
│   │   ├── orchestrator.py     # Orchestrator (reine Routing-Logik)
│   │   ├── retrieval_agent.py  # allgemeine Fragen (RAG)
│   │   ├── eu261_agent.py      # Entschädigungsprüfung mit echtem Flugstatus
│   │   └── chat_agent.py       # Streamlit-Glue: Agent-Flow-UI + Antwortaufbereitung
│   ├── flight_status.py  # AviationStack-Client für den EU261-Agent
│   ├── ingest.py          # Chunking + Embedding + Indexierung
│   ├── retrieve.py        # Retrieval-Logik
│   ├── generate.py        # Claude-API-Aufruf mit Kontext (Retrieval-Agent-Pfad)
│   └── app.py              # Streamlit-Frontend (Layout/Tabs)
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
- [x] Multi-Agenten-Architektur: Orchestrator + Klassifikationsagent routen zwischen
      Retrieval-Agent (allgemeine Fragen) und EU261-Agent (Entschädigungsprüfung mit
      echtem Flugstatus über AviationStack); Agent-Flow live in der UI sichtbar
- [ ] Embedding-Modell gegen ein für Deutsch optimiertes Modell tauschen (aktuell all-MiniLM-L6-v2, englisch trainiert – TODO in ingest.py)
- [ ] Buchungsagent mit echtem PNR-Zugriff — zurückgestellt: es gibt keine öffentlich
      erreichbare, nicht-proprietäre Datenquelle für personenbezogene Buchungsdaten
      (Zugriff liefe nur über authentifizierte Airline-/GDS-Systeme wie Amadeus/Sabre)
- [ ] Eskalationsagent (Human Handoff) — zurückgestellt: kein Ticket-/Support-System
      vorhanden, an das übergeben werden könnte

## Tech Stack

Python · Chroma · Claude API · Streamlit · AviationStack
