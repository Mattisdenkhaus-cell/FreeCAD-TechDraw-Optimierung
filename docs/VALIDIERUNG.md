# Validierungsstand – 17. Oktober 2026

## Ergänzung vom 19. Oktober: Nachprüfung vor dem SVG-Clip-Build

[Schnellprüfung 39239044953](https://github.com/Mattisdenkhaus-cell/FreeCAD-TechDraw-Optimierung/actions/runs/39239044953)
ist für `ccfc493` bestanden: neun Python-Tests, Qt 5.15.13 einschließlich
AddressSanitizer/UndefinedBehaviorSanitizer und erstmals dieselben C++-Tests unter
Qt 6.4.2. Beide SVG-Schalterstellungen bestehen, darunter jeweils 72 pixelgleiche
SVG-Szenen und der Clip-Test mit 124 statt 10.000 Kachelbesuchen. Das prüft Qt 6,
aber nicht exakt die unter Windows verwendete Version 6.8.3.

Der portable Test erzeugt nun zusätzlich eine SVG-schraffierte Schnittansicht,
wartet auf deren Projektion und prüft die Projektion nach dem Wiederöffnen erneut.
Ein lokaler API-Test mit dem vorhandenen FreeCAD 1.0.0 besteht alle fünf erweiterten
Prüfgruppen. Er ist kein Windows- oder Geschwindigkeitsnachweis für die private
Referenzdatei. Das JSON hält die zuletzt gestartete Phase und abgeschlossene
Phasenzeiten fest, auch wenn das Programm später blockiert.

[Windows-Schnitttest 39239181080](https://github.com/Mattisdenkhaus-cell/FreeCAD-TechDraw-Optimierung/actions/runs/39239181080)
hat mit dem **bereits vorhandenen** Paket aus Build `39031047030` ebenfalls bestanden
(FreeCAD 1.1.4, Qt 6.8.3). Erzeugung und Projektion des kleinen Schnitts dauerten
58 ms, Wiederöffnen 110 ms und anschließendes Warten auf Basis-/Schnittprojektion
75 ms. Das reproduziert den Zehn-Minuten-Fall nicht. Es beweist weder eine
Beschleunigung noch die Behebung auf der privaten Datei. Es wurde nicht neu gebaut;
das getestete Paket enthält den neuen Clip-Fix noch nicht. Ergebnis aus dem Joblog:
[windows-section-39239181080.json](validation/windows-section-39239181080.json).

Die folgenden Abschnitte dokumentieren die früheren Prüfstände.

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

## Windows-Vollbuild

[Lauf 38748155482](https://github.com/Mattisdenkhaus-cell/FreeCAD-TechDraw-Optimierung/actions/runs/38748155482)
ist erfolgreich abgeschlossen: vollständige Kompilierung und Linken, CMake-Installation,
Modul-/Ressourcenprüfung und Verpackung der optimierten Variante. Gebauter Commit:
`1b46341cb5e7ccef49ddba2030aa61f96886c9fb`. Das vollständige Windows-Artefakt
`11994042499` ist rund 642 MB groß.

## Noch offen

- Original-vs-optimiert-Messungen mit großen realen Zeichnungen auf Zielhardware.
- Mausauswahl, Erstellen/Ziehen/Snapping von Bemaßungen, Schnitt-/Detailansichten,
  Wiederöffnung realer Zeichnungen und visuelle Export-/Druckvergleiche (PDF/SVG/DXF).
- Das Benchmark-Werkzeug ist kein Ersatz für diese manuellen Funktionsprüfungen.

Die schnellen Qt-Teiltests kompilieren die neuen Header, zwei originale Qt-Elementklassen
und gezielt extrahierte geänderte Methodenkörper. Sie ersetzen keine Integrationstests
mit FreeCAD/OCCT. Der separate Windows-Vollbuild kompiliert die vollständige Anwendung.

## Portable Startprüfung unter Windows bestanden

`scripts/portable_smoke.FCMacro` wird im Workflow-Modus `validate-artifact` mit dem
entpackten Windows-Programm und separaten Konfigurationsdateien ausgeführt. Geprüft
werden Version/Module, projizierte Kanten, Bemaßung, SVG-Schraffur, öffentliche
Kantenauswahl, Maßtext-Eigenschaftsänderung, PDF/SVG/DXF-Dateierzeugung und erneutes
Öffnen der gespeicherten FCStd-Datei. Die asynchrone Projektion wird begrenzt abgewartet.
Die Datei-Erzeugung beweist keine visuelle Exportgleichheit.

[Lauf 38862598647](https://github.com/Mattisdenkhaus-cell/FreeCAD-TechDraw-Optimierung/actions/runs/38862598647)
hat am 16. Oktober das unveränderte Archiv aus dem erfolgreichen Vollbuild unter
Windows 2022 entpackt und mit isolierter Konfiguration gestartet. Alle fünf
Prüfgruppen bestanden mit FreeCAD **1.1.4**; Prozessende erfolgreich. Der Job dauerte
2 Minuten 8 Sekunden. Es wurde nicht neu kompiliert. Das Ergebnis aus dem Joblog
ist dauerhaft in [windows-portable-38862598647.json](validation/windows-portable-38862598647.json)
gesichert. Vollständige Exportdateien und Startlogs stehen im Ergebnisartefakt
`FreeCAD-portable-smoke-38748155482` dieses Prüflaufs (7 Tage Aufbewahrung).

Die Prüfung verwendet Qt offscreen. Sie bestätigt den portablen Programmstart und
die genannten Funktionen an einem kleinen erzeugten Testdokument, aber keine
GPU-/Displayqualität, visuelle Exportgleichheit oder Beschleunigung realer Zeichnungen.
Das Makro war zuvor mit dem vorhandenen Linux-FreeCAD 1.0.0 erfolgreich erprobt.

## Eigenständiges Testmakro

`benchmarks/TechDrawTest.FCMacro` bündelt den Benchmark mit automatischer temporärer
Dokumentkopie. Der Benutzer wählt nur das Blatt aus; Ergebnisse werden automatisch
unter `Dokumente/TechDrawTests` gespeichert. Nach dem Laden wartet das Makro auf die
projizierte Geometrie und aktiviert ausdrücklich das Blatt der Kopie. Die Kopie
benötigt keine Undo-Transaktion: Ihre Änderungen werden beim Schließen verworfen,
wodurch der dokumentübergreifende Undo-Verlauf des Originals erhalten bleibt.

`tests/freecad_copy_smoke.FCMacro` prüft in einem separaten FreeCAD-Prozess drei Fälle:
gespeicherte Zeichnung, ungespeicherte Maßänderung und Abbruch. In der vorhandenen
Linux-Version 1.0.0 offscreen bestanden: beide vollständigen Läufe mit fünf Messgruppen
und je zehn Werten; Abbruch korrekt als Fehler markiert. Original-Dateihash, Dateiname,
Modified-Status, Undo-Zähler, Objektzustände, Maßposition und Auswahl blieben erhalten.
Die temporäre Kopie wurde geschlossen und das Original wieder aktiviert. Die
Testergebnisse stehen im vom Test ausgegebenen temporären Ordner (`verified.json`
bei Erfolg, `error.txt` bei Fehler); Dialogantworten sind automatisiert.

Dies bestätigt den Ablauf an einem kleinen TechDraw-Testdokument, nicht die
Windows-Dialogdarstellung, beliebige externe Dokumentverknüpfungen oder die
Performance der optimierten Version. Die sieben bestehenden Python-Tests bestanden
weiterhin. Kein Windows-Vollbuild für die Makroänderung erforderlich.

## Zusätzliche native Navigationstests

Der erweiterte kombinierte Patch wurde auf einen weiteren frischen offiziellen
1.1.4-Checkout angewendet; alle elf geänderten/neuen Quelldateien stimmen mit dem
Entwicklungscheckout überein. Historischer SVG-Patch und ursprünglicher Workflow
bleiben unverändert. Kein zusätzlicher Windows-Vollbuild wurde gestartet.

Die Qt-Fixtures kompilieren den tatsächlichen `QGVPage`-Paintpfad, Renderer-/
Preview-Steuerung, Hintergrundroutine sowie `QGVNavStyle::zoom/pan` mit dem neuen
Header. Geprüft werden:

- Keine Vektor-Paint-Aufrufe innerhalb eines erfolgreich gecachten Bildschirm-Paints.
- Native Teilaktualisierung bei lokaler Farbänderung: 1 statt 1.120 Item-Paints in
  einer künstlichen Szene mit 2.400 Pfaden. Das ist kein kompletter FreeCAD-Auswahltest.
- Szenenänderungen, Auswahl, Verschieben, Textänderung, Ausblenden, Löschen, Zerstörung
  der Szene, fehlende Abdeckung, Größen-/Renderhint-Wechsel und Rückfallmodi.
- Gleiche Auswahlgeometrie/Positionen und bytegleicher SVG-Szenenexport während der
  Vorschau. Pixelgleiches exaktes Endbild nach Ablauf des Ruhe-Timers.
- Hintergrundgleichheit gegenüber der ursprünglichen Routine, einschließlich
  transparenter Farben, aktivem Qt-Hintergrundcache, Rotation und Skalierung.
- Begrenzte Bildallokation, ungültige Größen/DPI-Werte und Ausrichtung auf physische
  Pixel bei ungeraden Fenstergrößen bei 100, 125, 150 und 200 % Skalierung. Außerhalb
  von Text sind höchstens 4 von 255 Abweichung pro Farbkanal erlaubt. Qt-Versionen
  verwenden beim Text unterschiedliche Kantenglättung: Hier werden die Vordergrund-
  konturen in beiden Richtungen mit höchstens einem physischen Pixel Abstand geprüft.
  Für das exakte Endbild und den SVG-Szenenexport gilt weiterhin Bytegleichheit.

Ein beispielhafter nicht instrumentierter Durchlauf mit 2.000 Pfaden bei 100 % DPI:
20 Zoomschritte exakt etwa **1.067 ms**, Vorschau-Schritte **53 ms**, erste Aufnahme
**9 ms**, abschließendes exaktes Zeichnen **15 ms**. Die Messung enthält erzwungene
Widget-Aufnahmen und Eventloop-Verarbeitung; auf geteilter Cloud-Hardware schwanken
diese Einzelmessungen erheblich. Sie beweist keine Beschleunigung einer
realen Windows-Zeichnung. Einzelwerte einschließlich höherer DPI-Stufen stehen in
[navigation-qt5-20261017.json](validation/navigation-qt5-20261017.json).

Die 120-ms-Ruhefrist bleibt auch unter Sanitizern aktiv. Wird sie wegen langsamer
Ausführung überschritten, darf ein korrektes exaktes Zwischenbild entstehen;
diese zusätzlichen Paints werden separat gezählt, nicht künstlich unterdrückt.
Die ungecachte Abschlussarbeit wird ebenfalls separat ausgewiesen.

[GitHub-Prüflauf 39030737964](https://github.com/Mattisdenkhaus-cell/FreeCAD-TechDraw-Optimierung/actions/runs/39030737964)
bestand am 17. Oktober für `e64445a`: saubere Patchanwendung, sieben Python-Tests,
Qt-Regressionen in beiden SVG-Schalterstellungen sowie AddressSanitizer und
UndefinedBehaviorSanitizer. Windows-Jobs wurden übersprungen. Die vier DPI-Stufen
wurden zusätzlich lokal mit `--navigation-only` geprüft; CI prüft standardmäßig 100 %.
