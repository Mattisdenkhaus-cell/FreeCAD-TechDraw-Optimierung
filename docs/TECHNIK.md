# Technische Entscheidungen

## Kanten und Ansichtsrechtecke

`EdgeGeometryCache` speichert den Qt-Pfadsnapshot, die tatsächlich verwendete
Auswahltoleranz, das erzeugte Stroker-Ergebnis und dessen `controlPointRect()`.
Qt-Pfade sind implizit geteilt; wiederholte Abfragen desselben Pfades sind billig.
Der Vergleich verwendet dieselbe Pfadgleichheit wie `QGraphicsPathItem::setPath()`.
Auch Änderungen durch einen Basisklassenzeiger werden beim nächsten Zugriff erkannt.
Änderungen an `EdgeFuzz` erzeugen einen neuen Umriss. Farbe, Zoom und Auswahl ändern
keine Geometrie und benötigen keinen neuen Umriss. Alle Zugriffe bleiben im GUI-Thread.

Die originale Stroker-Konfiguration und die Auswahlfläche bleiben erhalten. Es gibt
keinen Cache der zugrunde liegenden CAD-/Bemaßungsgeometrie. Zusätzlicher Speicher:
pro abgefragter Kante der Stroker-Pfad und zwei kleine Qt-Cacheobjekte; die benötigte
Speichermenge wächst mit der Komplexität der Kanten. Bei extrem großen Blättern messen.
Die bestehende Behandlung einer live geänderten globalen `EdgeFuzz`-Einstellung
(Neuzeichnen/Neuaufbau durch FreeCAD) bleibt bestehen; der Cache verwendet beim Zugriff
immer den aktuellen Wert und fügt keine globale Preference-Beobachtung hinzu.

In `QGIView` und `QGIViewDimension` ersetzt `mapRectFromItem()` die Konstruktion und
anschließende Begrenzungsberechnung eines temporären Polygons. Es wird ausdrücklich
kein zusätzlicher Cache über dynamische Kindobjekte gelegt.

## Bemaßungsinteraktion

`QGIViewDimension::hover()` ändert nur die vorhandene Normal-/Hover-/Auswahlfarbe.
Die `setPretty*()`-Methoden fordern Updates für Maßlinien und beide Pfeile an.
Das bisherige vollständige `draw()` bei Hover, einschließlich Referenzauswertung und
Aktualisierung des gesamten Elternobjekts, entfällt. Maßtextbewegungen, Selektion,
Recompute, Referenzberechnung und Snapping behalten ihre bisherigen Geometriepfade.
Die Tests verwenden die wirklichen geänderten Methodenkörper in isolierten Qt-
Testumgebungen; echte Maus-/Snapping-Interaktion ist damit nicht bewiesen.

## SVG-Batching

Die Idee des historischen Patches bleibt: ein Grafikelement statt eines Elements
je SVG-Kachel. Implementiert in `QGIBatchedSvgHatch.h`:

- Sichtbare Spalten/Zeilen direkt aus dem exponierten Rechteck berechnen, danach
  dieselbe Kachel-Intersection wie zuvor prüfen. Auch überlappende Kacheln und
  nicht quadratische SVGs werden berücksichtigt. Keine Volliteration des Rasters.
- Originale spaltenweise Reihenfolge sowie `maxTiles + 1`-Verhalten erhalten.
  64-Bit-Zählung, begrenzte Integer-Konvertierungen und ungültige Skalierungen prüfen.
- Bounding-Rect deckt die tatsächlich vorhandenen Kacheln ab. `centerAt()` verwendet
  ausschließlich das ursprüngliche Rechteck, damit Zusatzabdeckung keine Verschiebung
  verursacht. Der upstream vorhandene Y-Ursprung `-overlayWidth` bleibt unverändert.
- Renderer ist weiterhin im Besitz der Fläche; `QPointer` verhindert Zugriff nach
  Freigabe. Repaint-Signal wird verbunden und beim Reset/Destruktor getrennt.
- Je Kachel dieselbe lokale Translation/Skalierung wie beim Qt-SVG-Item verwenden;
  keine Raster-/LOD-Ersatzdarstellung. Malzustand pro Kachel sichern/wiederherstellen.
- Der ursprüngliche SVG-Objektpfad ist mit `TECHDRAW_BATCH_SVG_HATCH=0` kompilierbar.
  Alte Kacheln werden beim Neuaufbau entfernt; der Konstruktor im `#else` bleibt erhalten.

Die XML-Einfärbung sowie PDF-/SVG-Pixmap-Exportpfade werden nicht geändert. Ihre
upstream bekannten Einschränkungen werden daher auch nicht als behoben behauptet.
Der historische Patch bleibt unverändert; der neue Git-Patch ersetzt dessen Anwendung
für die optimierte Variante vollständig. Neue Header werden direkt eingebunden,
keine zusätzliche CMake-Quelle oder Binärabhängigkeit nötig.

## Begrenzte Bildschirmvorschau und Teilaktualisierungen

Der native QWidget-Viewport kann jetzt optional Qt-Änderungsregionen verwenden.
`NavigationPreview` ergänzt separat einen kurzlebigen, auf 64 MiB begrenzten Cache
für aktive Navigation. Beide Optionen sind zunächst aus; bestehende Geometrie-,
SVG- und Exportpfade bleiben erhalten. Details, Invalidierungsregeln und bewusst
akzeptierte Aufnahme-/Abschlusskosten stehen in [INTERAKTION.md](INTERAKTION.md).

Keine zusätzlichen GUI-/OCCT-Threads, gröberen Auswahlflächen, vereinfachten
Modellgeometrien oder zwischengespeicherten Maßwerte. Keine Änderung der
Eigentümerschaft von Ansichtsprimitiven. OpenGL- und Image-Renderer behalten ihre
bisherigen Aktualisierungsmodi. Die bereits vorhandenen asynchronen HLR-/Schnitt-
und Flächenberechnungen werden nicht verändert.

## Build-Zeit

Kurze Linux-Prüfungen benötigen keine FreeCAD-Submodule oder LibPack-Downloads.
Der optionale Windows-Build cached nur das unveränderliche LibPack. Der bewährte
Visual-Studio-Generator und die vollständigen Installations-/Verpackungsschritte
bleiben erhalten. `CMAKE_CXX_COMPILER_LAUNCHER` wäre beim Visual-Studio-Generator
kein wirksamer sccache-Schalter; ein Wechsel zu Ninja wird deshalb nicht als kleine,
ungetestete Beschleunigung eingeschleust. Kein alter Buildbaum wird blind restauriert.
