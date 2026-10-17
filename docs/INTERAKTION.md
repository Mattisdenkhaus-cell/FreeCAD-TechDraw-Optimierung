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

## Gewählte Änderungen

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

Beide Maßnahmen besitzen einen unabhängigen Rückfallschalter. Vor einer Aktivierung
in einer Zielinstallation sind Tests der realen Qt-6-/Windows-Ausgabe erforderlich.
Qt-Teiltests prüfen Paint-Aufrufe, Bildgleichheit nach Abschluss, Invalidierung,
Speichergrenze sowie unveränderte Auswahl-/Exportpfade. Synthetische Messungen
werden ausdrücklich nicht als Beschleunigungswerte realer Zeichnungen ausgegeben.

## Nicht Teil dieses Schritts

Keine neue Rendering-Engine, kein OCCT-Umbau, keine Dokumentberechnung in zusätzlichen
Threads und kein vereinfachter Maßwert. `QGraphicsScene`, Widgets und deren Caches
bleiben im GUI-Thread. Eine aufwendige erste Rasteraufnahme und die abschließende
Vektordarstellung bleiben Kosten, die ausdrücklich gemessen werden müssen.
Die bisherigen SVG-, Kanten- und Hover-Optimierungen bleiben Bestandteil des Patches.

## Implementierte Versuchsschalter

Die beiden Maßnahmen sind im gemeinsamen Patch implementiert und **standardmäßig
ausgeschaltet**. Sie sind noch nicht im Windows-Artefakt aus Lauf `38748155482`
enthalten. Die Schalter gelten nur für einen neu aus diesem Patch gebauten Stand:

```python
p = App.ParamGet("User parameter:BaseApp/Preferences/Mod/TechDraw/General")
p.SetBool("PartialViewportUpdates", True)
p.SetBool("NavigationPreview", True)
```

Blattfenster schließen und wieder öffnen. Für A/B-Prüfungen beide Schalter einzeln
und gemeinsam testen; mit `False` ist der bisherige Darstellungspfad verfügbar.
`PartialViewportUpdates` wird beim Einrichten des Renderers gelesen. `NavigationPreview`
wird an den bestehenden Navigationspfaden für Rad-/Mauszoom, Pan und Tastatur-Pan geprüft.
Aktive Werkzeuge und die Platzierung von Positionsnummern verwenden keine Vorschau.

Die Vorschau hält genau ein Bild mit je 25 % Randreserve pro Seite. Der Speicher ist
auf **64 MiB pro aktivem Blatt** begrenzt und unabhängig von der gesamten Blattgröße.
Beim Überschreiten der Grenze bleibt die Darstellung exakt. Größen-, DPI-, Palette-
und Renderhint-Wechsel, Szenen-/Auswahländerungen sowie unzureichende Bildabdeckung
verwerfen die Vorschau. Nach **120 ms ohne weitere Navigationsanforderung** wird das
Bild freigegeben und ein zusammengefasstes exaktes Update angefordert. Eine bereits
laufende Berechnung wird dadurch nicht präemptiv unterbrochen.

Innerhalb der Reserve werden mehrere Zoomstufen durch Skalierung desselben Bildes
bedient; außerhalb wird exakt gezeichnet beziehungsweise bei der nächsten Bewegung
neu aufgenommen. Das ist bewusst kein dauerhaftes Mehrstufen-/Kachel-Cachesystem.
Während der Bewegung kann die Vorschau weicher aussehen. Die Szene mit allen
selektierbaren Items und Referenzen bleibt bestehen; weder Maßwerte noch Fangpunkte
oder Modellgeometrie werden durch Pixel ersetzt. Der Cache wird nur im nativen
`paintEvent` benutzt. `QGraphicsView::render`, `QGraphicsScene::render`, SVG und Druck
verwenden weiterhin den exakten Zeichenpfad.

Die Hintergrundroutine berücksichtigt jetzt das von Qt angeforderte Szenenrechteck.
Das verhindert künstliche Fensterrahmen im vergrößerten Aufnahmepuffer. Vor der
Aufnahme wird derselbe deckende Palettenhintergrund wie beim QWidget verwendet,
damit transparente TechDraw-Hintergründe keine alten Bildreste überlagern.
Der RGB32-Puffer übernimmt die logische Schrift-DPI des Viewports; seine Position
ist auf physische Pixel ausgerichtet, auch bei gebrochener Display-Skalierung.
Nicht deckende oder gemusterte Widget-Grundierungen fallen auf exakte Darstellung zurück.

## Kosten und verbleibende Grenzen

- Die erste Rasteraufnahme und das abschließende exakte Zeichnen bleiben im GUI-Thread.
  Eine kurze einzelne Radbewegung kann dadurch mehr Arbeit verursachen als vorher.
  Der Nutzen entsteht bei mehreren zusammenhängenden Navigationsschritten.
- GUI-/OCCT-Arbeit außerhalb dieses Bildschirm-Paintpfades wird nicht beschleunigt.
  Insbesondere Selektion kann weiterhin lineare Schleifen über Kindobjekte auslösen.
- Ständige Szenenänderungen können den Cache wiederholt verwerfen. Das erhält die
  Korrektheit, garantiert aber in diesem Fall keine flüssige Vorschau.
- Die kleinen Qt-Tests ersetzen keine Windows-/Qt-6-Integration, Maus-/Snapping-
  Prüfung oder Sichtprüfung komplexer PDF-/SVG-/DXF-Exporte.
- Das bisherige Python-Testmakro setzt Zoom/Scroll direkt am Widget. Dadurch misst
  es **nicht** den hier an echte Navigation gekoppelten Vorschaupfad. Es eignet sich
  weiterhin zum Vergleich der exakten Darstellung; Preview muss separat durch
  tatsächliche Navigation geprüft werden. Eine Übertragung der Mikrobenchmarkzahlen
  auf diese JSON-Ergebnisse wäre falsch.
