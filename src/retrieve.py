"""
Retrieval-Logik: nimmt eine Nutzerfrage und liefert die Top-k relevantesten
Chunks aus der Chroma-Collection zurück, inkl. Metadaten für die
Quellenanzeige im Frontend.
"""

import os

import chromadb
from chromadb.utils import embedding_functions

PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "chroma")
COLLECTION_NAME = "fluggastrechte"

# Schwellenwert für die Chroma-Distanz (kleiner = ähnlicher), ab dem ein Chunk
# als "nicht mehr passend" gilt und verworfen wird, statt als schwache Quelle
# in den Kontext für generate_answer zu wandern (Halluzinations-Schutz).
# Empirisch aus eval/testset.jsonl ermittelt: tatsächlich einschlägige
# Top-Treffer liegen meist deutlich unter 1.2, generische/irrelevante Artikel
# (z.B. Art. 1, Art. 18) liegen typischerweise darüber. Das Embedding-Modell
# (all-MiniLM-L6-v2, englisch trainiert) ist für Deutsch nicht optimiert -
# der Schwellenwert filtert daher eindeutiges Rauschen heraus, ersetzt aber
# kein für Deutsch optimiertes Modell (siehe TODO in ingest.py).
DEFAULT_MAX_DISTANCE = 1.2


def get_collection():
    client = chromadb.PersistentClient(path=PERSIST_DIR)
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    return client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)


def retrieve(
    query: str,
    k: int = 6,
    doc_type: str | None = None,
    max_distance: float | None = DEFAULT_MAX_DISTANCE,
) -> list[dict]:
    """
    Gibt eine Liste von Chunks zurück:
    [{"text": ..., "source": ..., "doc_type": ..., "url": ..., "distance": ...}, ...]

    doc_type: optional "verordnung" | "urteil" | "faq", um das Retrieval
    gezielt einzuschränken (z.B. für eine "nur Gesetzestext"-Ansicht).

    max_distance: Chunks mit einer Distanz oberhalb dieses Werts werden
    verworfen (siehe DEFAULT_MAX_DISTANCE). None deaktiviert den Filter.
    Es wird intern mehr als k Chunks abgefragt, damit nach dem Filtern noch
    bis zu k relevante Chunks übrig bleiben können.
    """
    collection = get_collection()
    where = {"doc_type": doc_type} if doc_type else None

    fetch_n = k if max_distance is None else k * 3
    results = collection.query(
        query_texts=[query],
        n_results=fetch_n,
        where=where,
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        distance = results["distances"][0][i]
        if max_distance is not None and distance > max_distance:
            continue
        chunks.append({
            "text": results["documents"][0][i],
            "source": results["metadatas"][0][i]["source"],
            "doc_type": results["metadatas"][0][i]["doc_type"],
            "url": results["metadatas"][0][i]["url"],
            "distance": distance,
        })
        if len(chunks) == k:
            break
    return chunks
