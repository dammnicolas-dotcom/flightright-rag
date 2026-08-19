"""
Streamlit-Frontend für den Fluggastrechte-RAG-Assistenten.

Drei zentrale UX-Entscheidungen (bewusst, nicht zufällig):
1. Quellenangaben stehen IMMER sichtbar unter der Antwort, nicht versteckt
   in einem Tooltip - Nachvollziehbarkeit ist bei Rechtsthemen kein Nice-to-have.
2. Ein Toggle erlaubt den Blick auf die rohen retrievten Chunks, bevor Claude
   daraus eine Antwort formuliert hat - macht die RAG-Pipeline transparent.
3. Ein Eval-Tab mit vordefinierten Testfragen zeigt, dass die Antwortqualität
   systematisch geprüft wird, nicht nur ad hoc getestet.
"""

import json
import os

import chromadb
import streamlit as st

from retrieve import retrieve, PERSIST_DIR, COLLECTION_NAME
from generate import generate_answer
from ingest import build_index, load_documents

st.set_page_config(page_title="Fluggastrechte-Assistent", page_icon="✈️")


def ensure_index_built() -> None:
    """
    data/processed/chroma/ ist bewusst nicht im Git-Repo (siehe .gitignore) -
    auf einem frischen Deployment (z.B. Streamlit Community Cloud) existiert
    daher noch kein Index. Baut ihn beim ersten Start automatisch aus
    data/raw/ auf, statt dass das manuell per `python src/ingest.py`
    passieren müsste.
    """
    client = chromadb.PersistentClient(path=PERSIST_DIR)
    try:
        client.get_collection(COLLECTION_NAME)
    except Exception:
        with st.spinner("Baue Wissensbasis-Index einmalig auf (kann kurz dauern)..."):
            build_index(load_documents())


def check_password() -> bool:
    """
    Zeigt eine Passwortabfrage, bevor die restliche App gerendert wird.
    Verhindert, dass jeder mit dem öffentlichen App-Link unkontrolliert
    Anfragen stellt und dabei den hinterlegten ANTHROPIC_API_KEY verbraucht.
    Das Passwort liegt in st.secrets (.streamlit/secrets.toml lokal, bzw.
    die Secrets-Verwaltung von Streamlit Community Cloud) - nie im Code.
    """
    if st.session_state.get("authenticated"):
        return True

    app_password = st.secrets.get("APP_PASSWORD")
    if not app_password:
        st.error(
            "Kein APP_PASSWORD in den Secrets konfiguriert - die App ist "
            "aktuell nicht durch ein Passwort geschützt. Bitte APP_PASSWORD "
            "in .streamlit/secrets.toml (lokal) bzw. den Streamlit-Cloud-"
            "Secrets hinterlegen."
        )
        return False

    st.title("🔒 Fluggastrechte-Assistent")
    password = st.text_input("Passwort", type="password")
    if st.button("Anmelden", type="primary"):
        if password == app_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Falsches Passwort.")
    return False


if not check_password():
    st.stop()

ensure_index_built()

st.title("✈️ Fluggastrechte-Assistent")
st.caption(
    "RAG-gestützte Beantwortung von Fragen zu Verspätung, Annullierung und "
    "Ausgleichsansprüchen nach EU-VO 261/2004."
)

tab_chat, tab_eval = st.tabs(["Chat", "Eval-Set"])

with tab_chat:
    show_chunks = st.toggle(
        "Retrieval-Ansicht anzeigen (rohe Quellen-Chunks vor der Antwort)",
        value=False,
    )

    question = st.text_input(
        "Deine Frage",
        placeholder="z.B. Mein Flug hatte 4 Stunden Verspätung, bekomme ich Geld zurück?",
    )

    if st.button("Fragen", type="primary") and question:
        with st.spinner("Suche relevante Quellen..."):
            chunks = retrieve(question, k=6)

        if show_chunks:
            st.subheader("Retrievte Chunks")
            for c in chunks:
                with st.expander(f"{c['source']} (Distanz: {c['distance']:.3f})"):
                    st.write(c["text"])

        with st.spinner("Formuliere Antwort..."):
            answer = generate_answer(question, chunks)

        st.subheader("Antwort")
        st.write(answer)

        st.subheader("Quellen")
        for c in chunks:
            label = f"**{c['source']}**"
            if c["url"]:
                st.markdown(f"- {label} — [Quelle]({c['url']})")
            else:
                st.markdown(f"- {label}")

with tab_eval:
    st.write(
        "Vordefinierte Testfragen mit erwarteter Antwort/Quelle, um die "
        "Antwortqualität nachvollziehbar zu prüfen."
    )

    eval_path = os.path.join(os.path.dirname(__file__), "..", "eval", "testset.jsonl")

    if not os.path.exists(eval_path):
        st.info("Noch kein Eval-Set vorhanden (eval/testset.jsonl).")
    else:
        with open(eval_path, encoding="utf-8") as f:
            testcases = [json.loads(line) for line in f if line.strip()]

        if st.button("Eval-Set durchlaufen"):
            for tc in testcases:
                st.markdown(f"**Frage:** {tc['question']}")
                chunks = retrieve(tc["question"], k=6)
                answer = generate_answer(tc["question"], chunks)
                st.write(answer)
                st.caption(f"Erwartete Quelle: {tc.get('expected_source', '–')}")
                st.divider()
