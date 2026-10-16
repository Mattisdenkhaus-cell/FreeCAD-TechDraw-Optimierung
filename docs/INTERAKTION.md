# Interaktion fertig berechneter Zeichnungen

Untersuchungsstand: FreeCAD 1.1.4, Quellcommit
`4fd3bf320d9566a27e60069fc8387448aaa3a094`. Inventor dient ausschließlich als
funktionales Vorbild für temporäre Rasterdarstellung und Hintergrundaktualisierung;
keine Autodesk-Implementierung oder proprietäre Quelle wird verwendet.

## Bereits vorhanden

| Konzept | FreeCAD-Pfad | Konsequenz |
|---|---|---|
| Hintergrundprojektion | `DrawViewPart::buildGeometryObject`: `QtConcurrent::run`, HLR-Watcher; Flächenermittlung ebenfalls asynchron | Keine zusätzlichen GUI-/Dokumentzugriffe in Worker verschieben. |
| Hintergrundschnitt | `DrawViewSection.cpp`: Schnitt-Future mit Watcher | Vorhandene Fertigstellung und Invalidierung beibehalten. |
| Geometriespeicher | `DrawViewPart`/`GeometryObject`, getrennt von `QGIViewPart` und Zeichenprimitiven | Bildschirmvorschau darf diese exakte Geometrie nicht ersetzen. |
| Grobdarstellung | `CoarseView`, polygonale HLR; beeinflusst auch Flächenbehandlung | Kein geeigneter Ersatz für eine reine Interaktionsvorschau. |
| Szenenindex | `QGSPage` verwendet bereits `BspTreeIndex` | Kein neues eigenes globales Suchverzeichnis erforderlich. |
| Hintergrundcache | `QGVPage`: `CacheBackground` | Cached nicht die Kanten, Ansichten oder Bemaßungen. |
| Image-Renderer | `QGVPage::paintEvent`: rendert bei jedem Paint erneut in `m_image` | Ein Bildpuffer ist noch kein wiederverwendbarer Inhaltscache. |
| Aktualisierungssteuerung | `DrawPage::KeepUpdated` und View-Overrides | Kein pauschales Abschalten von Modellaktualisierungen. |

`QGIViewPart` und seine primitiven Kinder verwenden `NoCache`; ein Cache am
Elternelement würde die Kinder nicht automatisch zu einem Raster zusammenfassen.
`DeviceCoordinateCache` an jeder Kante verursacht viele Einzelcaches und wird beim
Zoomen neu aufgebaut. `ItemCoordinateCache` könnte bei festen Auflösungen die
Darstellungsqualität verschlechtern. Beide sind deshalb keine pauschale Lösung.

Der native `QGVPage`-Viewport verwendet bisher `FullViewportUpdate`. Dadurch kann
auch eine kleine Auswahländerung viele unveränderte Primitive erneut zeichnen.
Die Navigation ändert Scrollbars/Transformation im GUI-Thread; hintereinander
ankommende Ereignisse können jeweils teure Vektorzeichenarbeit auslösen.

## Abgegrenzte nächste Änderungen

1. Optional `MinimalViewportUpdate` ausschließlich für den nativen QWidget-Viewport:
   Qt verwendet seine vorhandenen Änderungsregionen und wiederverwendet beim Scrollen
   unveränderte Pixel. Kein Wechsel des OpenGL- oder Image-Renderers.
2. Optional begrenzte Bildschirm-Rastervorschau für aktive Navigation: ein Bild mit
   Randreserve, Wiederverwendung innerhalb seiner Abdeckung, abschließendes exaktes
   Zeichnen nach kurzer Ruhezeit. Keine Rasterkacheln über das gesamte Blatt, kein
   permanenter mehrstufiger Cache und keine neuen Hintergrundthreads.
3. Szenenänderungen, Größen-/DPI-Wechsel und nicht abgedeckte Transformationen müssen
   die Vorschau verwerfen. Export und Druck verwenden weiter die Szene/Vektoren.
   Die exakten Items bleiben für Auswahl, Fangpunkte und Bemaßung vorhanden.

Beide Maßnahmen erhalten einen unabhängigen Rückfallschalter. Vor einer Aktivierung
in einer Zielinstallation sind Tests der realen Qt-6-/Windows-Ausgabe erforderlich.
Qt-Teiltests sollen Paint-Aufrufe, Bildgleichheit nach Abschluss, Invalidierung,
Speichergrenze sowie unveränderte Auswahl-/Exportpfade prüfen. Synthetische Messungen
werden ausdrücklich nicht als Beschleunigungswerte realer Zeichnungen ausgegeben.

## Nicht Teil dieses Schritts

Keine neue Rendering-Engine, kein OCCT-Umbau, keine Dokumentberechnung in zusätzlichen
Threads und kein vereinfachter Maßwert. `QGraphicsScene`, Widgets und deren Caches
bleiben im GUI-Thread. Eine aufwendige erste Rasteraufnahme und die abschließende
Vektordarstellung bleiben Kosten, die ausdrücklich gemessen werden müssen.
Die bisherigen SVG-, Kanten- und Hover-Optimierungen bleiben Bestandteil des Patches.
