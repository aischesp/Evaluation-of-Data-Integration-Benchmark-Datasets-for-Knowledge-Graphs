# PDF-Konvertierung des Entwurfsdokuments

Der Originaltext liegt in `docs/Entwurfsdokument.md`. Für die Abgabe an Marvin Hofer muss er als **PDF** vorliegen (max. 4–5 Seiten).

## Variante A: Pandoc (empfohlen)

Pandoc muss installiert sein. Auf macOS:

```bash
brew install pandoc basictex
```

Konvertierung:

```bash
cd "/Users/Berkay/Desktop/Big Data Praltikum"

pandoc docs/Entwurfsdokument.md \
  -o docs/Entwurfsdokument.pdf \
  --pdf-engine=xelatex \
  -V geometry:margin=2.2cm \
  -V mainfont="Helvetica Neue" \
  -V fontsize=10pt \
  -V colorlinks=true \
  --toc \
  --toc-depth=2 \
  --highlight-style=tango
```

Falls das Resultat > 5 Seiten ist, sind folgende Stellschrauben:

- `-V fontsize=9pt` (eine Schriftstufe kleiner)
- `-V geometry:margin=2.0cm`
- Tabellen kompakter formatieren (z. B. zwei in eine Zeile, oder breitere `columns`)
- Inhaltsverzeichnis (`--toc`) entfernen, falls Platz knapp

## Variante B: VS Code Markdown PDF Extension

1. Extension installieren: `yzane.markdown-pdf`
2. `Entwurfsdokument.md` öffnen
3. Command Palette → `Markdown PDF: Export (pdf)`

## Variante C: Online (Notfall)

- <https://md2pdf.netlify.app/>
- <https://www.markdowntopdf.com/>

Achtung: Datenschutz! Das Dokument enthält keine sensiblen Daten, aber ist persönlich.

## Verifikations-Checkliste vor dem Versand

- [ ] Seitenzahl: 4 ≤ Seiten ≤ 5
- [ ] Alle Tabellen passen auf eine Seite (keine geteilten Header)
- [ ] Mermaid-Diagramme korrekt eingebettet **oder** als ASCII-Diagramm dargestellt (Pandoc rendert kein Mermaid out-of-the-box — die ASCII-Variante in §5.1 ist deshalb der Fallback)
- [ ] Quellen [1] – [6] korrekt nummeriert
- [ ] Kein nicht-aufgelöster Platzhalter im Text
- [ ] Dateiname `Entwurfsdokument_KG-Quality_Spieker-Oezcekic.pdf`

## Wenn Mermaid-Diagramme benötigt werden

Variante: vorab über `mermaid-cli` zu PNG rendern:

```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i diagram.mmd -o docs/diagrams/pipeline.png
```

Dann im Markdown:

```markdown
![Pipeline](diagrams/pipeline.png)
```

Pandoc übernimmt das Bild dann ins PDF.
