# Auswertung der Messungen vom 17. Oktober 2026

Ausgewertet am 18. Oktober (Europe/Berlin). Zuordnung laut Benutzer:
`91c04b3e` = installierte Version, `693526d1` = optimierte Version.
Die privaten Originaldateien werden nicht ins Repository übernommen.

| Testschritt (Median) | Installiert, 1.1.1 | Optimiert, 1.1.4 |
|---|---:|---:|
| Zoom | 499,3 ms | 444,6 ms |
| Verschieben | 491,1 ms | 431,9 ms |
| Kantenauswahl über API | 2.665,0 ms | 15.873,7 ms |

Die beobachtete Auswahlzeit ist etwa 5,96-mal so hoch. Alle zehn Auswahlwerte
liegen in der optimierten Ausgabe zwischen 14,86 und 16,62 Sekunden; es handelt
sich nicht um einen einzelnen Ausreißer. Die zehn Auswahlmessungen summieren sich
auf 26,59 bzw. 157,82 Sekunden. Alle gemessenen Schritte zusammen: 36,53 bzw.
166,67 Sekunden. Bemaßungen wurden nicht getestet. Die sehr kleinen Redraw-Werte
belegen keine tatsächlich gezeichnete Frame-Dauer.

Der Benutzer berichtet 5–10 Minuten für den vollständigen Makroablauf. Die alte
JSON enthält weder Gesamtdauer noch Vorbereitung, drei Aufwärmrunden je Gruppe,
Gruppenwechsel, Wiederherstellung und Aufräumen. Bei ähnlichen Auswahlzeiten wären
allein drei Aufwärmrunden der optimierten Version nochmals rund 48 Sekunden.
Dies ist eine Schätzung, keine aufgezeichnete Messung; die gesamte Wartezeit ist
mit den alten Dateien nicht vollständig erklärbar.

## Vergleichsgrenzen

Fenstergröße (1581 × 1015), DPI-Faktor, Ausgangstransformation/Scrollposition,
Blatt, Schnittansicht, Kante und Qt 6.8.3 stimmen überein. Unterschiedlich sind:

- FreeCAD-Version und Quellcommit: 1.1.1 gegenüber 1.1.4.
- `saved-file` gegenüber `unsaved-snapshot`, mit unterschiedlichen Dateihashes.
- Windows-Plattformtext, bei gleicher aufgezeichneter Buildnummer 26200.

Das bestätigt die gemeldete Verzögerung der Auswahl in diesem Test, isoliert aber
noch nicht deren Ursache im Optimierungspatch. Ein gespeicherter und ein
ungespeicherter Stand können verschiedene Geometrie/Ansichtszustände enthalten;
ein abweichender Archivhash allein beweist allerdings auch keine Geometrieänderung.
Patch-Commit und aktive Versuchsschalter stehen nicht in diesen alten Ergebnissen.
Das alte Makro aktiviert die NavigationPreview nicht durch echte Navigation.

## Nächster Diagnoseschritt

`benchmarks/TechDrawSelectionDiagnose.FCMacro` zerlegt genau den bisherigen
Auswahlvorgang in clear/add/verify/update/repaint und erfasst auch Vorbereitung,
Aufwärmung, Wiederherstellung und Aufräumen. Ein Aufwärmschritt und drei Messungen
begrenzen die Wiederholung. Die automatische Dokumentkopie bleibt erhalten.

Im offiziellen 1.1.4-Code führen `MDIViewPage::clearSceneSelection` und
`selectQGIView` über `QGIViewPart::setGroupSelection` beziehungsweise
`DrawGuiUtil::isSelectedInTree/setSelectedTree` durch Ansichten/Kindobjekte.
`QGIView::updateView` aktualisiert Rahmen und Darstellung. Das sind konkrete
Untersuchungspunkte bei langsamen clear/add-Phasen, bisher kein Nachweis der Ursache.
Es wird noch keine weitere C++-Änderung als Behebung dieser Regression ausgegeben.

## Prüfung des Diagnosewerkzeugs

Sieben Python-Tests bestanden. Im installierten Linux-FreeCAD 1.0.0 wurden der
vollständige Test (gespeichert/ungespeichert), Abbruch und die kurze Auswahldiagnose
mit einem kleinen erzeugten Dokument geprüft. Originaldatei, Dokumentzustand,
Undo-Zähler, Objekte, Maßposition und Auswahl blieben erhalten; Kopie geschlossen.
Die Diagnose enthält genau drei Auswahlwerte, fünf Phasen je Wert, eine Aufwärmung
und die Gesamtablaufzeiten. Qt offscreen prüft hier nur Ablauf und APIs, keine
Windows-Darstellungsqualität oder Performance der Benutzerzeichnung.

In dieser Cloud-Instanz scheitert der installierte FreeCAD-Launcher vor Makrostart
in `Py_EncodeLocale`. Die Prüfung verwendete deshalb die vorhandenen FreeCAD-/GUI-
Module im System-Python mit `Gui.showMainWindow()` und dem Qt-Eventloop. Keine
abgeschwächten Testassertionen; alle vier Fälle endeten mit `verified.json`.
