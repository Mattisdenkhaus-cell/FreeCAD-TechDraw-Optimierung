# Feste Referenz und Ladeverzögerung – 19. Oktober 2026

Die private Zeichnung ist laut Benutzer ein normaler Arbeitsfall; größere Blätter
kommen regelmäßig vor. Sie wird nicht auf eine künstlich kleine Zeichnung reduziert
und nicht ins Repository hochgeladen.

SHA256: `faf4caa9467553a4b9a85692e3b611e6daaecb1537b73b52efdc40fe4709b009`.
Der Upload und die Originalmessung `8a9711f8` haben denselben Hash. Archivgröße rund
3 MB, entpackt rund 27 MB, 318 Dokumentobjekte. Das Blatt enthält eine Gruppe mit
zwei Projektionsansichten und zwei Schnittansichten; SVG-Muster sind eingebettet.

## Originalmessung

| Abschnitt | Zeit |
|---|---:|
| Kopie laden | 8,47 s |
| Recompute-Aufruf | 0,002 s |
| Auf erste Kante der Testansicht warten | 22,75 s |
| Blatt anzeigen | 5,43 s |
| GUI aktualisieren | 7,21 s |
| Runner initialisieren (bisher erneut show/updateGui) | 19,68 s |
| Auswahltest einschließlich Wiederherstellung | 18,64 s |
| Gesamtablauf | 82,67 s |

Die Auswahlmessungen betragen 3,02 / 8,10 / 2,92 s. Das Setzen der Auswahl kostet
jeweils 1,76–1,85 s, das Löschen nur 16–18 ms. Im langsamen mittleren Schritt benötigt
`Gui.updateGui()` allein 5,93 s. Das kann noch anstehende GUI-/Szenenarbeit enthalten;
es ist kein isoliertes CPU-Profil des Auswahlalgorithmus. Eine erste Kante beweist
nicht das Ende aller asynchronen Flächenarbeiten.

Für die optimierte Version berichtet der Benutzer über zehn Minuten beim Öffnen,
insbesondere bei Schnittansichten. Die Diagnose brach vor der eigentlichen Messung
ab: keine projizierte Kante der Testansicht innerhalb der Wartefrist. Dafür gibt es
noch keine verwertbaren optimierten Auswahlzeiten mit dieser festen Datei.

## Installationen laut Benutzer

| Komponente | Original | Unser Build |
|---|---|---|
| FreeCAD / Quellbasis | 1.1.4 / 4fd3bf320 | 1.1.4 / 4fd3bf320 plus Patch |
| Buildtyp | Release | Release |
| Qt / PySide | 6.8.3 | 6.8.3 |
| OCC | 7.8.1 | 7.8.1 |
| Python | 3.11.14 | 3.12.10 |
| Boost | 1.86 | 1.87 |
| VTK | 9.3.1 | 9.4.2 |
| Xerces | 3.3.0 | 3.2.5 |
| IfcOpenShell | 0.8.4 | 0.8.1.post1 |
| FrameForge | 0.2.1 | 0.2.1 |

Die aufgeführten Addons stimmen überein. Die unterschiedlichen Laufzeitpakete sind
relevante Vergleichsbedingungen, kein bewiesener Grund für die Verzögerung. Der
Quellhash im About-Dialog identifiziert den nachträglich angewendeten Patch nicht.

## Belegte Korrekturen

Das Makro zeigte die Seite bisher zweimal an und speicherte vor Runner-Erstellung
keinen Fehlerbericht. Es protokolliert jetzt vor möglicherweise langsamen Aufrufen
und nach ihrem Abschluss. Fehlerdaten werden vor dem Aufräumen geschrieben, denn
`DrawViewSection::~DrawViewSection` und `DrawViewPart::~DrawViewPart` warten auf
laufende Cut-/HLR-/Face-Futures. Eine 60-s-Wartegrenze garantiert somit keine maximale
Gesamtdauer. Es werden keine aktiven Worker unsicher beendet.

Die reine Auswahldiagnose verwendet ein bereits aktives, unverändert gespeichertes
Blatt direkt. Kein erneutes Dokumentladen, kein Recompute und keine Maß-/Modelländerung.
Andere Fälle und der vollständige Benchmark behalten ihre temporäre Kopie. Direkte
und kopierte Läufe werden vom Vergleichswerkzeug als unterschiedliche Bedingungen
abgewiesen. Dateizustand, Undo, Objekte und Auswahl werden in Integrationstests geprüft.

Ein separater Qt-Versuch zeigt die SVG-Clip-Lücke: Bei einer schmalen Elternfläche
betrug `option.exposedRect` rund 484 × 484, der aktive Painter-Clip dagegen 6 × 201.
Das bisherige Batching besuchte trotzdem Kacheln außerhalb dieses Clips. Der neue
Zeichenpfad schneidet den Expositionsbereich zusätzlich mit `clipBoundingRect()`;
zwei zusätzliche Gerätepixel erhalten dabei Antialias-/SVG-Strichränder auch bei
Rotation. Die eigentliche Qt-Pfadbeschneidung bleibt aktiv. Der strikte Pixelvergleich
fand ohne diesen Rand eine Abweichung bei 90 Grad; seine Toleranz wurde nicht gelockert.
Ein Regressionstest begrenzt 10.000 mögliche Kachelbesuche auf die 124 am schmalen Clip inklusive Antialias-Rand.
Bestehende Pixelvergleiche mit originalen SVG-Items prüfen die Ausgabe weiterhin.
Diese Korrektur erhält SVG-Batching, exakte Geometrie und Vektorzeichnung. Sie ist
noch kein Nachweis, dass der komplette Zehn-Minuten-Fall behoben ist.

## Grenzen der lokalen Reproduktion

Die vorhandene Linux-FreeCAD-1.0-Installation lädt nur 299 statt 318 Objekte,
meldet fehlendes FrameForge und ungültige Binder. Der begrenzte Versuch wurde beendet;
seine Zeiten werden nicht als Vergleich veröffentlicht. Die kleine erzeugte
Makro-Testzeichnung ist weiterhin für API-/Schutztests geeignet. Für eine belastbare
End-to-End-Aussage fehlen eine vollständige kompatible Umgebung und die optimierte
Messung auf der festen Referenzdatei. Kein neuer mehrstündiger Build ohne Zustimmung.
