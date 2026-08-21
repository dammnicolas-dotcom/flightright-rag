"""
EU261-Agent: prüft für einen konkreten Flug (Flugnummer + Datum), ob ein
Ausgleichsanspruch nach VO 261/2004 besteht - kombiniert dafür den
tatsächlichen Flugstatus (flight_status.py) mit den einschlägigen
Rechtsgrundlagen aus der Wissensbasis (retrieve.py).
"""

import os
from dataclasses import dataclass
from typing import Callable

from anthropic import Anthropic
from dotenv import load_dotenv

from flight_status import FlightStatus, FlightStatusUnavailable, get_flight_status
from retrieve import retrieve

load_dotenv()

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

OnStep = Callable[[str, str, str], None]
OnChunks = Callable[[list[dict]], None]

AGENT_NAME = "EU261-Agent"

SYSTEM_PROMPT = """Du bist ein Assistent für Fragen zu Fluggastrechten nach der \
EU-Verordnung 261/2004. Dir liegen der tatsächliche Status eines konkreten Fluges \
sowie einschlägige Rechtsauszüge vor. Beurteile auf dieser Basis, ob ein \
Ausgleichsanspruch besteht.

Regeln:
- Stütze dich NUR auf die mitgelieferten Flugfakten und Rechtsauszüge. Erfinde keine \
Artikel, Paragraphen oder Urteile.
- Prüfe insbesondere, ob die Verspätung die für einen Ausgleichsanspruch relevante \
Schwelle erreicht (vgl. EuGH Sturgeon: ab 3 Stunden Verspätung bei Ankunft) bzw. ob \
eine Annullierung vorliegt.
- Wenn die mitgelieferten Rechtsauszüge die Frage nicht abschließend beantworten \
(z.B. unklar, ob außergewöhnliche Umstände vorliegen), sag das explizit statt zu \
spekulieren.
- Nenne bei jeder inhaltlichen Aussage die konkrete Quelle (z.B. "Art. 7 VO 261/2004" \
oder "EuGH, Sturgeon, C-402/07").
- Antworte auf Deutsch, klar und ohne Floskeln.
- Weise am Ende kurz darauf hin, dass dies keine Rechtsberatung im rechtlichen Sinne \
ersetzt.
"""


@dataclass
class Eu261Result:
    answer: str
    flight_status: FlightStatus | None
    chunks: list[dict]


def _status_query(flight_status: FlightStatus) -> str:
    if flight_status.cancelled:
        return "Ausgleichsanspruch bei Annullierung"
    return f"Ausgleichsanspruch bei {flight_status.delay_minutes} Minuten Verspätung"


def answer(
    question: str,
    flight_number: str,
    flight_date: str,
    on_step: OnStep,
    on_chunks: OnChunks | None = None,
) -> Eu261Result:
    on_step(AGENT_NAME, f"fragt Flugstatus für {flight_number} am {flight_date} ab…", "running")
    try:
        flight_status = get_flight_status(flight_number, flight_date)
    except FlightStatusUnavailable as exc:
        on_step(AGENT_NAME, str(exc), "error")
        return Eu261Result(answer=str(exc), flight_status=None, chunks=[])

    delay_note = f", Verspätung {flight_status.delay_minutes} Min." if flight_status.delay_minutes else ""
    on_step(AGENT_NAME, f"Status: {flight_status.status}{delay_note}", "done")

    on_step(AGENT_NAME, "prüft Ausgleichsanspruch anhand VO 261/2004 + EuGH-Rechtsprechung…", "running")
    chunks = retrieve(_status_query(flight_status), k=6)

    if on_chunks is not None:
        on_chunks(chunks)

    if not chunks:
        # Gleicher Halluzinations-Schutz wie im Retrieval-Agent (generate.py,
        # NO_SOURCE_MESSAGE): ohne Rechtsauszüge im Kontext keine Bewertung.
        text = (
            "Der Flugstatus liegt vor, aber dazu passende Rechtsauszüge finde ich in "
            "der Wissensbasis nicht. Ich kann den Ausgleichsanspruch daher nicht "
            "verlässlich beurteilen.\n\nDies ersetzt keine Rechtsberatung im "
            "rechtlichen Sinne."
        )
        on_step(AGENT_NAME, "keine passenden Rechtsauszüge gefunden.", "error")
        return Eu261Result(answer=text, flight_status=flight_status, chunks=[])

    context = "\n\n".join(f"[Quelle: {c['source']}]\n{c['text']}" for c in chunks)
    flight_facts = (
        f"Flugnummer: {flight_number}\n"
        f"Datum: {flight_date}\n"
        f"Status: {flight_status.status}\n"
        f"Verspätung: {flight_status.delay_minutes} Minuten\n"
        f"Abflug: {flight_status.departure_airport or 'unbekannt'}\n"
        f"Ankunft: {flight_status.arrival_airport or 'unbekannt'}"
    )
    user_message = f"""Flugfakten:

{flight_facts}

Rechtsauszüge:

{context}

---

Frage: {question}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    text = response.content[0].text
    on_step(AGENT_NAME, "Anspruchsprüfung abgeschlossen.", "done")

    return Eu261Result(answer=text, flight_status=flight_status, chunks=chunks)
