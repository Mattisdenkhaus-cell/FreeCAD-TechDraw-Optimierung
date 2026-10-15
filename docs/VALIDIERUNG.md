# Validierungsstand – 15. Oktober 2026

Basis FreeCAD 1.1.4: `4fd3bf320d9566a27e60069fc8387448aaa3a094`.
Lokale Umgebung: Debian 13, Qt 5.15.15, g++, Raster-Offscreen-Qt-Tests.

## Bestanden

- Gemeinsamen Patch auf einen zweiten, sauberen Checkout geprüft und angewendet;
  `git diff --check` ohne Fehler. Wiederanwendung wird ohne Veränderung abgewiesen.
- C++-Teiltests mit `-Wall -Wextra -Werror`, SVG-Schalter **1 und 0**.
- Gleichheit von Auswahlumriss und Bounding-Rect bei Pfadwechsel, übersetzten/
  veränderten/geteilten/leeren Pfaden und geänderter Auswahltoleranz; zusätzliche
  Punkt-in-Auswahlflächen-Prüfungen. Reale geänderte `QGIEdge`-Methoden werden
  ebenfalls kompiliert und gegen die ursprüngliche Berechnung geprüft.
- 90 Rechtecktransformationen (Rotation, Skalierung, Scherung) mit gleicher Begrenzung.
- 400 deterministische SVG-Raster/Ausschnitte gegen ursprüngliche Schleifenreihenfolge,
  einschließlich überlappender Kacheln und Kachelgrenzen. Sehr großes Raster mit kleinem
  Ausschnitt, Reset und ungültige Schrittweite zusätzlich geprüft.
- 72 **pixelgleiche** SVG-Szenen: Rotation, Skalierung, Ausschnitt/Zoom, Kachelgrenze,
  elliptische Fläche mit ausgespartem Loch. Reale `QGCustomSvg`-/`QGCustomRect`-Klassen
  werden kompiliert. Renderer-Freigabe wird geprüft.
- Tatsächlicher `buildSvgHatch()`-Methodenkörper und Konstruktor-Zuweisung in beiden
  Schalterstellungen: wiederholter Aufbau ohne Verschiebung/Objektansammlung,
  ungültige Skalierung leert Kacheln.
- Tatsächliche Hover-/Farbmethoden in einer isolierten Qt-Testumgebung: Normal/Hover/
  Auswahl stimmen, keine Geometrieneuberechnung oder Maßtextverschiebung.
- AddressSanitizer und UndefinedBehaviorSanitizer in beiden Schalterstellungen ohne
  Befund. Leak-Prüfung wegen globaler Qt-Offscreen-Objekte deaktiviert; dies ist kein
  vollständiger Leak-Nachweis für FreeCAD.
- Sieben Python-Tests: falscher Quellcommit wird ohne Dateiverlust abgewiesen,
  Benchmark-Statistik und Ablehnung inkompatibler/fehlerhafter Messdaten; zusätzlich
  CRLF-Patchanwendung und weiterhin wirksame Whitespace-Prüfung unter Windows.
- Neuer Workflow mit actionlint 1.7.7 geprüft. Historischer Patch und Workflow unverändert.

Der Qt-Test gibt einen Mikrobenchmark für wiederholte Umriss-/Bounding-Rect-Abfragen
mit unverändertem Pfad aus. Der Cache spart dort nachweisbar Stroker-Aufrufe und Zeit.
Diese Messung umfasst weder ein echtes Zeichnungsblatt noch Qt-Szenenindizierung,
Preference-Abfragen oder GPU-Zeiten und begründet **keine FPS-/Gesamtbeschleunigungszahl**.

## Benchmark-API-Smoke-Test

Mit dem bereits installierten **unveränderten FreeCAD 1.0.0 unter Linux** wurde ein
kleines Testdokument mit TechDraw-Ansicht und Bemaßung erzeugt. Das Benchmark-Werkzeug
lief durch alle fünf Messarten mit jeweils drei Messschritten und stellte seinen
Zustand ohne gemeldeten Fehler wieder her. Dies prüft die verwendeten Python-/Widget-
APIs. Wegen anderer FreeCAD-Version und Offscreen-/OpenGL-Warnungen gelten diese
Werte ausdrücklich **nicht** als Rendering- oder Performance-Nachweis für 1.1.4.
Es wurden keine solchen Messwerte als Optimierungsergebnis übernommen.

## Noch offen

- Vollständige Kompilierung/Linken von FreeCAD 1.1.4 unter Windows, Start und portable
  Verpackung der optimierten Variante. Der korrigierte Windows-Lauf `38748155482`
  ist gestartet; sein Endergebnis bleibt abzuwarten.
- Original-vs-optimiert-Messungen mit großen realen Zeichnungen auf Zielhardware.
- Mausauswahl, Erstellen/Ziehen/Snapping von Bemaßungen, Schnitt-/Detailansichten,
  Dokument-Wiederöffnung und visuelle Export-/Druckvergleiche (PDF/SVG/DXF).
- Das Benchmark-Werkzeug ist kein Ersatz für diese manuellen Funktionsprüfungen.

Die Tests kompilieren die neuen Header, zwei originale Qt-Elementklassen und gezielt
extrahierte geänderte Methodenkörper. FreeCAD-/OCCT-abhängige Klassen werden dabei
nicht vollständig gebaut. Diese Grenze wird nicht durch statische Checks aufgehoben.

## Vorbereitung der portablen Startprüfung

`scripts/portable_smoke.FCMacro` wird im Workflow-Modus `validate-artifact` mit dem
entpackten Windows-Programm und separaten Konfigurationsdateien ausgeführt. Geprüft
werden Version/Module, projizierte Kanten, Bemaßung, SVG-Schraffur, öffentliche
Kantenauswahl, Maßtext-Eigenschaftsänderung, PDF/SVG/DXF-Dateierzeugung und erneutes
Öffnen der gespeicherten FCStd-Datei. Die asynchrone Projektion wird begrenzt abgewartet.
Die Datei-Erzeugung beweist keine visuelle Exportgleichheit.

Das Makro ist mit dem vorhandenen Linux-FreeCAD 1.0.0 erfolgreich erprobt, einschließlich
aller fünf Prüfgruppen. Windows-1.1.4-Ergebnisse werden erst nach erfolgreichem
Artefaktbuild erfasst. Der GUI-Start erfolgt offscreen; GPU-/Displayqualität ist damit
nicht bewertet. Die neue Workflow-Variante wurde mit actionlint geprüft.
