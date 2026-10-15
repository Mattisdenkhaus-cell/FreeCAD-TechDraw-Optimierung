# TechDraw 1.1.4: Analyse und Arbeitsstand

Basis: offizieller Tag `1.1.4`, Commit
`4fd3bf320d9566a27e60069fc8387448aaa3a094`.
Entwicklung auf `development/techdraw-performance`; kein Windows-Vollbuild ohne Zustimmung.

## Befunde

- `QGIEdge::shape()` erzeugt bei jedem Aufruf einen neuen `QPainterPathStroker`.
  `boundingRect()` ruft ebenfalls `shape()` auf. Ein Cache muss sowohl den aktuellen
  Pfad als auch `PreferencesGui::edgeFuzz()` berücksichtigen; auch Aufrufe von
  `QGraphicsPathItem::setPath()` über Basisklassen müssen funktionieren.
- `QGIView::frameRect()` und `customChildrenBoundingRect()` durchlaufen Kinder und
  erzeugen pro Rechteck ein temporäres Polygon. `mapRectFromItem()` vermeidet dies.
  Ein pauschaler Cache der gesamten Kindmenge wäre ohne vollständige Beobachtung
  von Sichtbarkeit, Position, Transformation und Geometrie unsicher.
- `QGIViewDimension::hover()` ruft `draw()` auf: Referenzprüfung, Pfeilaufbau,
  Maßlinienberechnung und Aktualisierung des Elternobjekts nur wegen Farbwechsel.
  Die vorhandenen `setPretty*()`-Methoden erlauben gezielte Farbaktualisierungen.
  Positionsänderungen müssen weiter die echte Maßgeometrie neu berechnen.
- `QGIPrimPath::paint()` synchronisiert Stift und Füllung mit Qt. Diese allgemeine
  Routine wird vorerst erhalten: Änderungen könnten Bounding-Rect-Semantik vieler
  abgeleiteter Klassen beeinflussen.
- `QGIDatumLabel` verwendet bereits Qt-eigenes `childrenBoundingRect()`-Caching.
  Kein zusätzlicher unsicherer Text-/Geometriecache.
- `QGVPage` verwendet für den Raster-Viewport vollständige Aktualisierungen;
  Änderung erst mit echten FreeCAD-GUI-Tests auf Artefakte. OpenGL und Export
  erhalten ihren bisherigen Zeichenpfad.
- `QGIViewPart` baut primitive Objekte bei `drawViewPart()` neu auf. Keine Änderung
  der Lebensdauer/Identität selektierbarer Kanten ohne vollständige GUI-Tests.
- Der vorhandene SVG-Patch spart Kachelobjekte, durchläuft aber beim Zeichnen noch
  jede Kachel. Sein `boundingRect()` beeinflusst außerdem `centerAt()`. Die
  CI-Extraktion verwirft die Kontextzeile mit dem ursprünglichen Konstruktor im
  `#else`-Zweig. Ein regulärer Git-Patch soll die Textanker-Extraktion ersetzen.

## Vorgehen und Grenzen

Gezielte Qt-C++-Teiltests statt FreeCAD-Vollbuild; Caches gegen ungecachte
Referenzberechnungen, SVG-Batching gegen ursprüngliche Qt-SVG-Kacheln prüfen.
Keine behaupteten FPS oder Windows-Messwerte. End-to-End-Tests mit realen
Zeichnungen und portabler Windows-Version bleiben eine eigene Freigabestufe.
Der historische SVG-Patch und der bestehende Windows-Workflow bleiben erhalten;
ein separater optimierter Workflow kann die neue Variante bauen.
