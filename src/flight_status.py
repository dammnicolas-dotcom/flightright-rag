"""
Client für eine externe Flugstatus-API (AviationStack), damit der EU261-Agent
den tatsächlichen Status eines konkreten Fluges (Verspätung/Annullierung)
abfragen kann. Hinter einer schmalen Funktion gekapselt, damit sich der
Provider (z.B. Wechsel zu AeroDataBox) austauschen lässt, ohne den
EU261-Agent anzufassen.

Hinweis: Der kostenlose AviationStack-Tarif schränkt den Zugriff auf
vergangene Flüge ggf. ein (historische Daten sind teils kostenpflichtig) -
Nutzerfragen beziehen sich aber meist auf einen bereits stattgefundenen Flug.
Das äußert sich hier als FlightStatusUnavailable mit einer erklärenden
Meldung, nicht als Absturz oder stille Fehlantwort.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://api.aviationstack.com/v1/flights"


class FlightStatusUnavailable(Exception):
    """Kein verwertbarer Flugstatus verfügbar (kein Key, Rate-Limit, kein Treffer)."""


class FlightStatus:
    def __init__(
        self,
        flight_number: str,
        date: str,
        status: str,
        delay_minutes: int,
        departure_airport: str | None,
        arrival_airport: str | None,
    ):
        self.flight_number = flight_number
        self.date = date
        self.status = status  # z.B. "scheduled" | "active" | "landed" | "cancelled" | "diverted"
        self.delay_minutes = delay_minutes
        self.departure_airport = departure_airport
        self.arrival_airport = arrival_airport

    @property
    def cancelled(self) -> bool:
        return self.status == "cancelled"


def get_flight_status(flight_number: str, date: str) -> FlightStatus:
    api_key = os.environ.get("AVIATIONSTACK_API_KEY")
    if not api_key:
        raise FlightStatusUnavailable(
            "Kein AVIATIONSTACK_API_KEY konfiguriert - Flugstatus kann nicht "
            "abgerufen werden."
        )

    try:
        response = requests.get(
            API_URL,
            params={
                "access_key": api_key,
                "flight_iata": flight_number,
                "flight_date": date,
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise FlightStatusUnavailable(f"Flugstatus-API nicht erreichbar: {exc}") from exc

    payload = response.json()
    if payload.get("error"):
        raise FlightStatusUnavailable(
            f"Flugstatus-API-Fehler: {payload['error'].get('message', 'unbekannt')}"
        )

    results = payload.get("data") or []
    if not results:
        raise FlightStatusUnavailable(
            f"Kein Flugstatus für {flight_number} am {date} gefunden - ggf. liegt "
            "der Flug außerhalb des im aktuellen API-Tarif verfügbaren Zeitraums."
        )

    flight = results[0]
    departure = flight.get("departure") or {}
    arrival = flight.get("arrival") or {}

    return FlightStatus(
        flight_number=flight_number,
        date=date,
        status=flight.get("flight_status", "unknown"),
        delay_minutes=arrival.get("delay") or departure.get("delay") or 0,
        departure_airport=departure.get("airport"),
        arrival_airport=arrival.get("airport"),
    )
