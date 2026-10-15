# Fortsetzungsstand

Branch: `development/techdraw-performance`. Hauptbranch unverändert.
Abgeschlossene Schritte sind in getrennten Git-Commits gesichert.

1. Quellcodeanalyse der angefragten Komponenten abgeschlossen.
2. Gemeinsamer C++-Patch mit Kanten-Cache, Rechtecktransformationen,
   Hover-Farbupdates und abgesichertem SVG-Batching implementiert und lokal getestet.
3. Neuer separater Workflow, Benchmark-Werkzeug und Dokumentation vorhanden.
4. Vor dem ersten neuen Windows-Vollbuild ausdrücklich die Zustimmung einholen.
   Kein mehrstündiger Build wurde gestartet.

## Nächste Freigabestufe

- Pull Request prüfen; schnelle Linux-CI auswerten, sofern GitHub-API/Push verfügbar.
- Nach ausdrücklicher Zustimmung zunächst Windows `optimized` bauen; bei Bedarf
  `upstream` für Vergleichsmessungen mit identischer Toolchain. Der historische
  Workflow und SVG-Patch stehen weiterhin unverändert zur Verfügung.
- Portable Ausgabe separat entpacken, mit getrennten Einstellungsdateien starten,
  Funktions-/Exportcheckliste aus `benchmarks/README.md` abarbeiten.
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
