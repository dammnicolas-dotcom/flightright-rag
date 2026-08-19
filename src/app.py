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

import streamlit as st

from retrieve import retrieve
from generate import generate_answer

st.set_page_config(page_title="Fluggastrechte-Assistent", page_icon="✈️")

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
