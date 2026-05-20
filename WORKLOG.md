# Worklog — Asynchrones Änderungsprotokoll

> **Zweck:** Aische und Berkay arbeiten asynchron. Jede inhaltliche Änderung wird hier kurz
> festgehalten — Datum · Initialen · was wurde gemacht · was ist als Nächstes dran.
> Konvention: neueste Einträge **oben**, kurze Sätze, Datei-Pfade verlinkt.

---

## 2026-05-20 · Initialer Aufschlag (auto-prepared)

**Was wurde aufgesetzt:**

- Repo-Struktur angelegt: `docs/`, `src/kg_quality_eval/`, `config/`, `data/`, `notebooks/`, `results/`, `tests/`, `material/`
- Original-Material in `material/` einsortiert (Themen­beschreibung, Meeting-Notes, JAPE-Paper)
- Konzeptdokumente erstellt in `docs/`:
  - [`Entwurfsdokument.md`](docs/Entwurfsdokument.md) ← **Hauptdokument für Testat 1**
  - [`Datensaetze.md`](docs/Datensaetze.md) — Auswahl der 8 Benchmark-Datasets mit Begründung
  - [`Metriken-Katalog.md`](docs/Metriken-Katalog.md) — vollständiger Katalog mit Formeln, MoSCoW-Priorisierung
  - [`Architektur.md`](docs/Architektur.md) — Pipeline, Module, Backend-Strategie
  - [`Offene_Fragen.md`](docs/Offene_Fragen.md) — 12 Fragen für Feedback-Treffen mit Hofer
  - [`Arbeitsplan.md`](docs/Arbeitsplan.md) — Meilensteine bis Testat 3 mit Personen-Zuordnung
  - [`PDF-Konvertierung.md`](docs/PDF-Konvertierung.md) — Anleitung zum PDF-Build
- README.md komplett neu — Projektüberblick, Struktur, Datensätze, Setup, Tech-Stack
- Code-Skelett mit funktionsfähigem OpenEA-Loader + Basis-Statistiken:
  - [`src/kg_quality_eval/core.py`](src/kg_quality_eval/core.py) — `KGPair` & `KnowledgeGraph`
  - [`src/kg_quality_eval/loaders/`](src/kg_quality_eval/loaders/) — `BaseLoader`, `OpenEALoader`
  - [`src/kg_quality_eval/metrics/`](src/kg_quality_eval/metrics/) — `BaseMetric`, `BasicStatistics`
  - [`src/kg_quality_eval/runner.py`](src/kg_quality_eval/runner.py) — CLI-Pipeline-Runner
  - [`src/kg_quality_eval/utils/config.py`](src/kg_quality_eval/utils/config.py) — YAML-Config-Loader
- Tests: [`tests/test_smoke.py`](tests/test_smoke.py) — End-to-End-Smoke-Test mit Dummy-OpenEA-Daten
- Config-Beispiel: [`config/datasets.example.yaml`](config/datasets.example.yaml) — alle 8 Datasets (6 aktiv, 2 kommentiert)
- Build-Files: `requirements.txt`, `pyproject.toml`, `.gitignore`

**Was als Nächstes ansteht** (Aufgaben siehe [`TASKS.md`](TASKS.md)):

1. **Beide:** `docs/Entwurfsdokument.md` querlesen — passt Stil/Inhalt?
2. **Beide:** offene Fragen in `docs/Offene_Fragen.md` durchgehen, vor Versand mit Hofer abstimmen
3. **Berkay:** Entwurfsdokument → PDF via Pandoc (s. `docs/PDF-Konvertierung.md`)
4. **Berkay:** Hofer auf GitHub als Collaborator einladen
5. **Aische:** OpenEA-Zip herunterladen, ein Dataset zum Testen lokal entpacken
6. **Beide:** virtual env anlegen, `pip install -r requirements.txt`, `pytest` laufen lassen

---

<!--
TEMPLATE für neue Einträge:

## YYYY-MM-DD · Initialen · Kurztitel

**Geändert:**
- Datei A — was
- Datei B — was

**Hintergrund / Entscheidung:**
- ...

**Offen / als Nächstes:**
- ...
-->
