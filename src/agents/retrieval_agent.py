"""
Retrieval-Agent: kapselt den bisherigen (unveränderten) RAG-Ablauf aus
retrieve.py + generate.py als einen der Orchestrator-Zweige, inkl.
Zwischenschritt-Meldungen für den UI-Agent-Flow.
"""

from dataclasses import dataclass
from typing import Callable

from generate import generate_answer
from retrieve import retrieve

OnStep = Callable[[str, str, str], None]
OnChunks = Callable[[list[dict]], None]

AGENT_NAME = "Retrieval-Agent"


@dataclass
class RetrievalResult:
    answer: str
    chunks: list[dict]


def answer(question: str, on_step: OnStep, on_chunks: OnChunks | None = None) -> RetrievalResult:
    on_step(AGENT_NAME, "durchsucht Wissensbasis (VO 261/2004, EuGH-Urteile, FAQ)…", "running")
    chunks = retrieve(question, k=6)
    on_step(AGENT_NAME, f"{len(chunks)} passende Quelle(n) gefunden.", "done")

    if on_chunks is not None:
        on_chunks(chunks)

    text = generate_answer(question, chunks)
    return RetrievalResult(answer=text, chunks=chunks)
