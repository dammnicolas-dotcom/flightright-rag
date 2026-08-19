"""
Nimmt eine Nutzerfrage plus retrievte Chunks und generiert eine Antwort über
die Claude API - mit der klaren Vorgabe, sich ausschließlich auf die
mitgelieferten Quellen zu stützen und diese zu referenzieren.
"""

import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Fester Text statt eines API-Aufrufs, wenn retrieve() nach dem
# Distanz-Schwellenwert (siehe retrieve.py, DEFAULT_MAX_DISTANCE) keinen
# einzigen Chunk mehr liefert. Halluzinationsschutz hat Priorität vor
# Antwortqualität: ohne jede Quelle im Kontext gibt es nichts, worauf sich
# eine Antwort stützen könnte, also wird gar nicht erst generiert.
NO_SOURCE_MESSAGE = (
    "Dazu liegt mir keine passende Quelle in der Wissensbasis vor. Ich kann "
    "diese Frage daher nicht auf Basis der VO 261/2004, der hinterlegten "
    "EuGH-Urteile oder der FAQ-Fallbeispiele beantworten.\n\n"
    "Dies ersetzt keine Rechtsberatung im rechtlichen Sinne."
)

SYSTEM_PROMPT = """Du bist ein Assistent für Fragen zu Fluggastrechten nach der \
EU-Verordnung 261/2004. Du beantwortest Fragen ausschließlich auf Basis der \
mitgelieferten Quellenauszüge.

Regeln:
- Stütze dich NUR auf die mitgelieferten Quellen. Erfinde keine Artikel, \
Paragraphen oder Urteile.
- Die mitgelieferten Quellenauszüge stammen aus einem automatischen Retrieval \
und sind nicht garantiert alle thematisch einschlägig. Prüfe für jeden Auszug \
selbst, ob er die gestellte Frage tatsächlich inhaltlich beantwortet, bevor du \
dich darauf stützt. Ignoriere Auszüge, die nur oberflächlich ähnlich klingen \
oder ein anderes Thema behandeln (z.B. ein anderer Artikel, ein anderer \
Anspruchsgrund), auch wenn sie im Kontext mitgeliefert wurden.
- Wenn KEINER der mitgelieferten Auszüge die Frage tatsächlich beantwortet, \
sag das explizit (z.B. "Dazu liegt mir keine passende Quelle vor.") statt zu \
spekulieren oder eine nur entfernt verwandte Quelle als Antwort zu verwenden. \
Im Zweifel gilt: lieber keine Antwort als eine unsichere.
- Nenne bei jeder inhaltlichen Aussage die konkrete Quelle (z.B. "Art. 5 Abs. 1 \
lit. c VO 261/2004" oder "EuGH, Sturgeon, C-402/07").
- Antworte auf Deutsch, klar und ohne Floskeln.
- Weise am Ende jeder Antwort kurz darauf hin, dass dies keine Rechtsberatung \
im rechtlichen Sinne ersetzt.
"""


def build_context_block(chunks: list[dict]) -> str:
    parts = []
    for c in chunks:
        parts.append(f"[Quelle: {c['source']}]\n{c['text']}")
    return "\n\n".join(parts)


def generate_answer(question: str, chunks: list[dict]) -> str:
    if not chunks:
        return NO_SOURCE_MESSAGE

    context = build_context_block(chunks)

    user_message = f"""Kontext (retrievte Quellenauszüge):

{context}

---

Frage: {question}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text
