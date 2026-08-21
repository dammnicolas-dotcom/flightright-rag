"""
Orchestrator: reine Routing-Logik ohne UI-Abhängigkeit (kein Streamlit-Import,
dadurch einzeln testbar). Klassifiziert die Anfrage und delegiert an den
passenden Spezialagenten; bei einer Entschädigungsfrage ohne erkennbare
Flugnummer/Datum wird gezielt nachgefragt, statt zu raten oder den
EU261-Agent mit unvollständigen Daten aufzurufen.
"""

from dataclasses import dataclass
from typing import Callable

from agents.classifier import classify
from agents.eu261_agent import answer as eu261_answer
from agents.retrieval_agent import answer as retrieval_answer
from flight_status import FlightStatus

OnStep = Callable[[str, str, str], None]
OnChunks = Callable[[list[dict]], None]

MISSING_INFO_MESSAGE = (
    "Um deinen Ausgleichsanspruch für einen konkreten Flug zu prüfen, brauche ich "
    "Flugnummer und Datum des betroffenen Fluges (z.B. \"LH441 am 2026-03-14\")."
)


@dataclass
class AgentResult:
    answer: str
    agent: str
    chunks: list[dict]
    flight_status: FlightStatus | None = None


def run(question: str, on_step: OnStep, on_chunks: OnChunks | None = None) -> AgentResult:
    on_step("Klassifikationsagent", "prüft Anfrage…", "running")
    classification = classify(question)
    on_step("Klassifikationsagent", f"Kategorie: {classification.category}", "done")

    if classification.category == "allgemein":
        result = retrieval_answer(question, on_step, on_chunks)
        return AgentResult(answer=result.answer, agent="Retrieval-Agent", chunks=result.chunks)

    if not classification.flight_number or not classification.flight_date:
        on_step("Orchestrator", "Flugnummer/Datum fehlen für Anspruchsprüfung.", "error")
        return AgentResult(answer=MISSING_INFO_MESSAGE, agent="Orchestrator", chunks=[])

    result = eu261_answer(
        question, classification.flight_number, classification.flight_date, on_step, on_chunks
    )
    return AgentResult(
        answer=result.answer,
        agent="EU261-Agent",
        chunks=result.chunks,
        flight_status=result.flight_status,
    )
