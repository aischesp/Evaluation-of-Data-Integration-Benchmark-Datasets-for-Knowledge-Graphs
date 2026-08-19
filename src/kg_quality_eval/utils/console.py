"""Konsolenausgabe, die auch ausserhalb von UTF-8-Terminals funktioniert.

Die Skripte geben Zeichen wie ✓, ── und ═══ aus. Unter Windows ist die Konsole
standardmaessig cp1252 — dort wirft schon die erste Ausgabezeile einen
UnicodeEncodeError und das Skript bricht ab, bevor es irgendetwas geschrieben
hat. Ein Aufruf von `enable_utf8_output()` am Anfang jedes Skripts verhindert
das.
"""

from __future__ import annotations

import sys


def enable_utf8_output() -> None:
    """Stellt stdout und stderr auf UTF-8 um, wo das noetig und moeglich ist.

    Ersetzt nicht darstellbare Zeichen, statt abzubrechen — eine unleserliche
    Box-Zeichnung ist besser als ein abgestuerzter Auswertungslauf.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:          # z. B. umgeleitet auf ein Objekt ohne API
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):    # Stream nicht rekonfigurierbar
            continue
