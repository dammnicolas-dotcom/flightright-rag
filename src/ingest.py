"""
Liest alle JSON-Dokumente aus data/raw/, embedded sie und legt sie in einer
persistenten Chroma-Collection ab.

Erwartetes Format pro Dokument (siehe data/raw/vo_261_2004_beispiel.json):
{
    "id": str,            # eindeutige ID, z.B. "vo261-art5-abs1c"
    "doc_type": str,      # "verordnung" | "urteil" | "faq"
    "source": str,        # menschenlesbare Quellenangabe für die Anzeige
    "url": str | None,    # optionaler Link zur Originalquelle
    "text": str           # der eigentliche Inhalt (bereits sinnvoll geschnitten,
                           # z.B. ein Artikel oder ein Leitsatz)
}

Hinweis: Die Chunks liegen hier bereits fachlich sinnvoll vor (pro Artikel /
pro Leitsatz), nicht nach fixer Zeichenlänge. Das ist bei Rechtstexten wichtig,
damit kein Artikel mitten im Satz zerschnitten wird.
"""

import json
import glob
import os

import chromadb
from chromadb.utils import embedding_functions

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "chroma")
COLLECTION_NAME = "fluggastrechte"

# TODO: ggf. gegen ein anderes Embedding-Modell tauschen (z.B. multilingual,
# da die Inhalte auf Deutsch sind) - all-MiniLM-L6-v2 ist ein solider Default
# zum Starten, aber nicht für Deutsch optimiert.
#
# Nutzt Chromas ONNX-basierte DefaultEmbeddingFunction (all-MiniLM-L6-v2),
# statt SentenceTransformerEmbeddingFunction (PyTorch) - dadurch entfällt
# die schwergewichtige torch-Abhängigkeit, die auf manchen Plattformen
# (z.B. ältere macOS/x86_64 + neue Python-Versionen) keine passenden
# Wheels findet.


def load_documents() -> list[dict]:
    docs = []
    for path in glob.glob(os.path.join(DATA_DIR, "*.json")):
        with open(path, encoding="utf-8") as f:
            docs.extend(json.load(f))
    return docs


def build_index(docs: list[dict]) -> None:
    client = chromadb.PersistentClient(path=PERSIST_DIR)
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()

    # Collection frisch aufbauen, damit Re-Ingestion keine Duplikate erzeugt
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME, embedding_function=embedding_fn
    )

    collection.add(
        ids=[d["id"] for d in docs],
        documents=[d["text"] for d in docs],
        metadatas=[
            {
                "doc_type": d["doc_type"],
                "source": d["source"],
                "url": d.get("url") or "",
            }
            for d in docs
        ],
    )
    print(f"{len(docs)} Dokumente indexiert -> {PERSIST_DIR}")


if __name__ == "__main__":
    documents = load_documents()
    if not documents:
        print(f"Keine Dokumente in {DATA_DIR} gefunden. "
              f"Bitte VO-Text, Urteile und FAQ als JSON ablegen (siehe Beispieldatei).")
    else:
        build_index(documents)
