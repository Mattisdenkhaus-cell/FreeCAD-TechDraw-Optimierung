Große, bereits berechnete TechDraw-Zeichnungen zeichnen bei Navigation und kleinen Farbänderungen viele unveränderte Elemente erneut. Dieser Patch für den festgelegten FreeCAD-1.1.4-Quellcommit `4fd3bf320d9566a27e60069fc8387448aaa3a094` ergänzt eine optionale Bildschirmvorschau für Zoom/Pan und reduziert wiederholte Geometrie- und Zeichenarbeit.

- Kanten-Auswahlumrisse und Bounding-Rects nach Pfad/Auswahltoleranz cachen; Rechtecke ohne temporäres Polygon transformieren.
- Bei Maßtext-Hover Farben aktualisieren, geometrische Maßberechnung und Drag-/Snapping-Pfade erhalten.
- SVG-Schraffuren bündeln, sichtbare Kacheln eingrenzen und Renderer-Lebensdauer absichern; ursprüngliche Reihenfolge und Platzierung erhalten.
- Optional native Teilaktualisierung und eine kurzlebige Rastervorschau mit 64 MiB Speichergrenze verwenden. Nach 120 ms Navigationsruhe exakt neu zeichnen; Szenenänderungen, Auswahl, Bildabdeckung und DPI berücksichtigen. Beide Optionen sind standardmäßig aus. Exakte Szene, Auswahlgeometrie und Export bleiben erhalten.
- Benchmark-Makro mit automatischer temporärer Dokumentkopie sowie getrennten Validierungs-/Build-Workflow bereitstellen. Historischen SVG-Patch und bisherigen Workflow unverändert erhalten.

Vorhandene asynchrone HLR-/Flächen-/Schnittberechnungen bleiben erhalten. Die erste Rasteraufnahme und das abschließende exakte Zeichnen laufen weiterhin im GUI-Thread. Architektur, Versuchsschalter und Grenzen stehen in `docs/INTERAKTION.md`.

**Validierung:** [Linux-CI 39030737964](https://github.com/Mattisdenkhaus-cell/FreeCAD-TechDraw-Optimierung/actions/runs/39030737964) bestanden: saubere Patchanwendung, sieben Python-Tests, Qt-Regressionen mit beiden SVG-Schalterstellungen und AddressSanitizer/UndefinedBehaviorSanitizer (Qt-Offscreen-Leak-Prüfung deaktiviert). Geprüft sind unter anderem 72 pixelgleiche SVG-Szenen, 400 Kachelausschnitte, 90 Rechtecktransformationen sowie Cache-Invalidierung, unveränderte Auswahlgeometrie und SVG-Szenenexport. Navigation zusätzlich lokal bei 100/125/150/200 % DPI geprüft; exaktes Endbild bytegleich. Die synthetischen Messdaten belegen keine Gesamtbeschleunigung realer Zeichnungen.

**Windows-Stand:** [Vollbuild 38748155482](https://github.com/Mattisdenkhaus-cell/FreeCAD-TechDraw-Optimierung/actions/runs/38748155482) und [portabler Start-/Exporttest 38862598647](https://github.com/Mattisdenkhaus-cell/FreeCAD-TechDraw-Optimierung/actions/runs/38862598647) bestanden für den bisherigen Optimierungsstand. Dieses Windows-Paket enthält die neue Navigationserweiterung noch nicht. Ein weiterer mehrstündiger Build benötigt eine neue ausdrückliche Zustimmung.

Der PR bleibt bis zur Windows-/Qt-6-Integration, realen Zeichnungsbenchmarks und manuellen Auswahl-/Bemaßungs-/Exportprüfungen ein Entwurf. Details: `docs/VALIDIERUNG.md`, `docs/FORTSETZUNG.md`, `benchmarks/README.md`.
