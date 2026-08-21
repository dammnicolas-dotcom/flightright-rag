"""
Chat-Agent: einzige Komponente (neben app.py) mit Streamlit-Bezug. Baut aus
dem übergebenen st.status-Container den on_step-Callback für den
Orchestrator (macht den Agent-Flow live sichtbar) und übernimmt die finale
Aufbereitung der Antwort für die Anzeige.
"""

import streamlit as st

from agents.orchestrator import run as orchestrator_run

STATE_ICON = {"running": "⏳", "done": "✅", "error": "⚠️"}


def handle_question(question: str, status, show_chunks: bool) -> None:
    def on_step(agent: str, message: str, state: str) -> None:
        icon = STATE_ICON.get(state, "•")
        status.write(f"{icon} **{agent}**: {message}")

    def on_chunks(chunks: list[dict]) -> None:
        if not show_chunks:
            return
        st.subheader("Retrievte Chunks")
        for c in chunks:
            with st.expander(f"{c['source']} (Distanz: {c['distance']:.3f})"):
                st.write(c["text"])

    result = orchestrator_run(question, on_step, on_chunks)

    on_step("Chat-Agent", "bereitet Antwort zur Anzeige auf.", "done")
    status.update(
        label="Antwort fertig" if result.chunks or result.flight_status else "Antwort fertig (Rückfrage)",
        state="error" if result.agent == "EU261-Agent" and result.flight_status is None else "complete",
    )

    st.subheader("Antwort")
    st.write(result.answer)

    if result.flight_status is not None:
        fs = result.flight_status
        delay_note = f", Verspätung {fs.delay_minutes} Min." if fs.delay_minutes else ""
        st.caption(f"Flugstatus {fs.flight_number} ({fs.date}): {fs.status}{delay_note}")

    if result.chunks:
        st.subheader("Quellen")
        for c in result.chunks:
            label = f"**{c['source']}**"
            if c["url"]:
                st.markdown(f"- {label} — [Quelle]({c['url']})")
            else:
                st.markdown(f"- {label}")
