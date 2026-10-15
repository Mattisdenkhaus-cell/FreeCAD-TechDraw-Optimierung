# Vergleichbare GUI-Schritte messen

`TechDrawBench.FCMacro` läuft innerhalb von FreeCAD. Das Werkzeug greift nur auf
Dokumentobjekte, Auswahl-API und Qt-**Widgets** zu. Es ruft weder `scene()` noch
`items()` auf und verändert keine Qt-Grafikobjekt-Besitzstruktur.

## Durchführung auf Windows

1. Die identische gespeicherte FCStd-Datei in Original und optimierter portabler
   Version öffnen. Gleiche Einstellungen, Renderer, Fenstergröße, DPI-Skalierung,
   Zoom und Scrollposition verwenden. Berechnung vollständig abwarten.
2. `example.json` kopieren, Kennzeichnung (`label`), Szenario (`fixture_kind`) und
   Ausgabepfad festlegen. Optional die internen Namen `page`, `view`, `dimension`
   sowie `edge` setzen. Ohne Namen verwendet das Werkzeug die erste Seite,
   deren erste Bauteilansicht/Bemaßung und `Edge1`.
3. Vor dem Start von FreeCAD in PowerShell festlegen:
   `$env:TECHDRAW_BENCH_CONFIG = 'C:/FC/benchmark-config.json'`.
   Ohne Konfiguration gelten 5 Aufwärm- und 30 Messdurchläufe; die Ausgabe landet
   als `techdraw-benchmark.json` im temporären Verzeichnis.
4. Makro `TechDrawBench.FCMacro` ausführen. Während des Laufs nicht editieren oder
   die Seite schließen. Das Werkzeug speichert **keine** FCStd-Datei. Temporäre
   Maßpositionen werden durch Abbruch einer eigenen Transaktion zurückgesetzt;
   Auswahl und View-Transformation werden wiederhergestellt. Für Messungen immer
   eine Testkopie verwenden; bei einem Fehler die JSON-Felder `error` und
   `restore_error` prüfen und die Kopie ohne Speichern schließen.
5. Je Variante mindestens drei getrennte Läufe durchführen, abwechselnd Original
   und optimiert. Vergleich: `python benchmarks/compare.py original.json optimized.json`.
   Das Programm lehnt abweichende dokumentierte Bedingungen und fehlerhafte Läufe ab.

## Szenarien und Interpretation

Für **beide** Klassen messen: große Baugruppe ohne Schraffuren sowie Schnittansicht
mit SVG-Schraffuren; zusätzlich ein Blatt mit mehreren Ansichten und Bemaßungen.
Der Datei-SHA256 stellt sicher, dass dieselbe gespeicherte Datei verglichen wird.

- `redraw`: synchrones Neuzeichnen des Viewports.
- `zoom`: wechselnde View-Transformation um den Ausgangszoom.
- `pan`: horizontale Scrollbewegung; ohne Scrollbereich als nicht gemessen markiert.
- `edge_selection`: Auswahl über FreeCADs öffentliche Selection-API, einschließlich
  Aktualisierung der Seite. Misst keine Maus-Hit-Test-Suche.
- `dimension_property_move`: Positionsänderung von X/Y des Maßtexts über
  Dokumenteigenschaften einschließlich Recompute. Dies ist **kein** simuliertes
  Mausziehen; der tatsächliche Drag-/Snapping-Pfad bleibt ein manueller GUI-Test.

Ausgegeben werden Rohwerte, Median, p95, Versionen und Testbedingungen. Die Werte
sind GUI-Schrittlaufzeiten einschließlich `Gui.updateGui()` und synchronem Repaint,
**keine FPS** und keine garantierten GPU-Abschlusszeiten. CPU-Mikrobenchmarks aus den
Qt-Tests separat halten. Der Vergleich prüft Metadaten, ersetzt aber keine Kontrolle
identischer Treiber, Energieprofile, Hintergrundlast und FreeCAD-Einstellungen.

## Zusätzlich vor Freigabe prüfen

Kanten per Maus auswählen, Maße erstellen, Texte ziehen und einrasten lassen,
Ansichten drehen/skalieren, Schraffurfarbe/-skalierung/-versatz ändern, Datei neu
öffnen. PDF/SVG/DXF und Druck bei hoher Auflösung mit dem Original vergleichen.
Die vorhandenen Exportpfade werden erhalten, sind hier aber nicht vollständig
getestet. Für A/B-Vergleiche stehen im neuen Workflow `upstream`, `optimized` und
`optimized-unbatched` zur Verfügung; Vollbuilds erst nach ausdrücklicher Zustimmung.
