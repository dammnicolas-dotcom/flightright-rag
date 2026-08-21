"""
Klassifikationsagent: bestimmt anhand der Nutzerfrage, ob es sich um eine
allgemeine Fluggastrechte-Frage handelt oder um eine konkrete
Entschädigungsprüfung zu einem bestimmten Flug - und extrahiert in letzterem
Fall Flugnummer und Datum in einem einzigen Claude-Aufruf (statt zwei
getrennten LLM-Calls für Klassifikation und Extraktion).
"""

import json
import os
from dataclasses import dataclass
from typing import Literal

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

Category = Literal["allgemein", "flugstatus_entschaedigung"]

SYSTEM_PROMPT = """Du klassifizierst Nutzeranfragen an einen Fluggastrechte-Assistenten \
und extrahierst dabei ggf. Flugnummer und Flugdatum.

Kategorien:
- "allgemein": Frage zu Fluggastrechten ohne Bezug auf einen konkreten, identifizierbaren \
Flug (z.B. "Was zählt als außergewöhnlicher Umstand?").
- "flugstatus_entschaedigung": Die Frage bezieht sich auf einen konkreten Flug, dessen \
tatsächlicher Status (Verspätung/Annullierung) für die Antwort relevant ist.

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt, keine Erklärung, kein Fließtext:
{"category": "allgemein" | "flugstatus_entschaedigung", "flight_number": string | null, \
"flight_date": string | null}

flight_number im IATA-Format (z.B. "LH441"), flight_date als ISO-Datum (YYYY-MM-DD). \
Setze beide auf null, wenn nicht in der Frage enthalten oder nicht eindeutig ableitbar - \
rate nichts hinzu."""


@dataclass
class ClassificationResult:
    category: Category
    flight_number: str | None
    flight_date: str | None


def classify(question: str) -> ClassificationResult:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    raw = response.content[0].text.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Im Zweifel als allgemeine Frage behandeln, damit der bewährte
        # Retrieval-Pfad greift, statt die Anfrage an einer kaputten
        # JSON-Antwort scheitern zu lassen.
        return ClassificationResult(category="allgemein", flight_number=None, flight_date=None)

    category = data.get("category")
    if category not in ("allgemein", "flugstatus_entschaedigung"):
        category = "allgemein"

    return ClassificationResult(
        category=category,
        flight_number=data.get("flight_number"),
        flight_date=data.get("flight_date"),
    )
