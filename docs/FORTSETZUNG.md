# Fortsetzungsstand

Branch: `development/techdraw-performance`. Hauptbranch unverändert.
Abgeschlossene Schritte sind in getrennten Git-Commits gesichert.

1. Quellcodeanalyse der angefragten Komponenten abgeschlossen.
2. Gemeinsamer C++-Patch mit Kanten-Cache, Rechtecktransformationen,
   Hover-Farbupdates und abgesichertem SVG-Batching implementiert und lokal getestet.
3. Neuer separater Workflow, Benchmark-Werkzeug und Dokumentation vorhanden.
4. Die ausdrückliche Zustimmung zum optimierten Windows-Vollbuild liegt vor.
   Lauf [38747230182](https://github.com/Mattisdenkhaus-cell/FreeCAD-TechDraw-Optimierung/actions/runs/38747230182)
   wurde mit `mode=full-build`, `variant=optimized`, `parallel_jobs=2` gestartet.
   Gebauter Commit: `4a04e9324f21f2a7249d7ce4747cef86529cdcc8`.
   Die vorgeschalteten Qt-/Python-/Sanitizer-Prüfungen waren erfolgreich.
   Der Windows-Job scheiterte vor der Kompilierung an CRLF-Zeilenenden im Patch.
   Die Patch-Übertragung wird jetzt auf LF normalisiert; strikte Whitespace-Prüfung
   bleibt aktiv. Zwei zusätzliche Regressionstests prüfen diesen Windows-Fall.
   Der korrigierte Lauf [38748155482](https://github.com/Mattisdenkhaus-cell/FreeCAD-TechDraw-Optimierung/actions/runs/38748155482)
   hat Commit `1b46341cb5e7ccef49ddba2030aa61f96886c9fb` erfolgreich kompiliert,
   installiert und als vollständiges portables Windows-Archiv veröffentlicht.
   Artefakt-ID: `11994042499`, rund 642 MB, Ablauf am 22. Oktober 2026 um 17:27 UTC.
   Download und Startanleitung stehen im README.

## Erweiterung für flüssige Navigation

Die zusätzlichen Ziele nach funktionalem Inventor-Vorbild sind in `docs/INTERAKTION.md`
untersucht. Der kombinierte Patch enthält jetzt optionale native Teilaktualisierung
und eine begrenzte Zoom-/Pan-Rastervorschau mit exakter Rückkehr und Invalidierung.
Beide Funktionen sind zunächst aus. Der alte erfolgreiche Windows-Build enthält
sie noch nicht. Der Benutzer hat den neuen mehrstündigen Windows-Build am
17. Oktober 2026 ausdrücklich freigegeben.
Bisheriger SVG-Patch und ursprünglicher Workflow bleiben erhalten.
Implementierung: `fe3f2ef`, DPI-/Darstellungskorrekturen: `6a67a47`, `c24b211`;
plattformübergreifender Textvergleich: `e64445a`. Lokale Navigationstests bestehen
bei vier DPI-Stufen; Messdaten und Prüfgrenzen stehen in `docs/VALIDIERUNG.md`.
GitHub-Prüflauf `39030737964` für `e64445a` ist grün, einschließlich Sanitizern;
Windows-Jobs wurden in diesem Prüflauf übersprungen.

Der freigegebene [Windows-Vollbuild 39031047030](https://github.com/Mattisdenkhaus-cell/FreeCAD-TechDraw-Optimierung/actions/runs/39031047030)
wurde am 17. Oktober um 12:03 UTC für Commit
`3e22c3cdfa2fd8430bb62ee3494fe865f8bf15fd` gestartet: `mode=full-build`,
`variant=optimized`, `confirm_long_build=true`, `parallel_jobs=2`.
Bei Fortsetzung zuerst diesen Lauf prüfen und keinen doppelten Build starten.
Der Windows-Build ist erfolgreich abgeschlossen (17. Oktober, 17:00 Uhr Europe/Berlin).
Der anschließende kurze Artefakttest benötigt keine neue Kompilierung. Die neue
Benutzermessung zeigt jedoch eine deutliche Verzögerung bei der Auswahl; daher
bleibt der PR ein Entwurf und die Navigationserweiterung standardmäßig aus.

## Nächste Freigabestufe

- Windows-Vollbuild `38748155482` und anschließender kurzer Start-/Exporttest
  [38862598647](https://github.com/Mattisdenkhaus-cell/FreeCAD-TechDraw-Optimierung/actions/runs/38862598647)
  sind für den bisherigen Stand erfolgreich abgeschlossen. Alle fünf Prüfgruppen
  bestanden. Der neue Vollbuild für die Navigationserweiterung ist oben verlinkt. Ergebnis dauerhaft unter `docs/validation/` gesichert.
- Der PR bleibt bis zu realen Zeichnungsbenchmarks und manuellen Interaktions-/
  Sichtprüfungen ein Entwurf. Ein separater `upstream`-Vergleichsbuild wurde noch
  nicht freigegeben. Historischer Workflow und SVG-Patch sind unverändert.
- Portable Ausgabe separat entpacken, mit getrennten Einstellungsdateien starten,
  Funktions-/Exportcheckliste aus `benchmarks/README.md` abarbeiten.
  Das neue eigenständige `benchmarks/TechDrawTest.FCMacro` ermöglicht einen ersten
  Messlauf mit reiner Seitenauswahl: automatische temporäre Dokumentkopie,
  JSON-Speicherung unter `Dokumente/TechDrawTests`, kein manuelles Kopieren nötig.
- Große reale Zeichnungen mit und ohne SVG-Schraffuren messen; erst dann Aussagen
  über die Verbesserung der tatsächlichen Bearbeitungsperformance treffen.

## Reproduktion nach Sitzungswechsel

Die benötigten Änderungen und Tests sind vollständig im Repository enthalten;
`/tmp`-Quellen/Compiler-Ausgaben sind entbehrlich. Die Befehle im README klonen den
exakten offiziellen Quellstand und wenden den Patch an. Das Projekt-Checkout der
isolierten Cloud-Aufgabe weiterverwenden; keinen Git-Worktree ohne ausdrücklichen
Auftrag erzeugen. Bestehende Änderungen vor jeder Aktion prüfen und erhalten.

## GitHub-Stand

Entwurfs-PR: https://github.com/Mattisdenkhaus-cell/FreeCAD-TechDraw-Optimierung/pull/1
Der Entwicklungsbranch ist gepusht. Vorhandene Plattformauthentifizierung genügt;
keine zusätzlichen Tokens nötig. Die für die GitHub-API benötigte Domain
`api.github.com` ist im Umgebungskonfigurationsentwurf ergänzt. Eine Veröffentlichung
der Umgebung wird damit nicht behauptet.

## Auswahlverzögerung: aktueller Untersuchungsstand (18. Oktober)

Die vom Benutzer als optimierte Version bezeichnete Messung `693526d1` benötigt
bei der API-Kantenauswahl median 15,87 s statt 2,67 s in `91c04b3e`. Zoom/Pan sind
etwas schneller. Der Benutzer berichtet 5–10 Minuten Gesamtdauer; die alten JSONs
messen nur einzelne Schritte, nicht die vollständige Laufzeit. Andere Quellversion
(1.1.1/1.1.4) und saved-file/unsaved-snapshot verhindern eine eindeutige Zuordnung
zum Patch. Details und nächste Untersuchungspunkte: `docs/AUSWAHLDIAGNOSE.md`.

Neues eigenständiges `benchmarks/TechDrawSelectionDiagnose.FCMacro`: Blatt auswählen,
automatische Kopie, ein Aufwärmschritt und drei Auswahlschritte. Speichert getrennte
clear/add/verify/update/repaint-Zeiten sowie Vorbereitung, Wiederherstellung und
Aufräumen. Lokal vier FreeCAD-API-/Kopierschutz-Prüffälle und sieben Python-Tests
bestanden. Noch keine bestätigte Ursache oder C++-Behebung; kein neuer Vollbuild
für die Diagnose nötig. Nächster benötigter Befund ist die Diagnose-JSON aus der
langsamen Windows-Installation.
