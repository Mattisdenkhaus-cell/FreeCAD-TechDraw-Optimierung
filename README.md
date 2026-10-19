# FreeCAD TechDraw – Performance-Entwicklung für 1.1.4

Entwicklungsstand für flüssigere Bearbeitung bereits berechneter Zeichnungen.
Die Änderungen liegen als **gemeinsamer C++-Patch** für den verifizierten
FreeCAD-Commit `4fd3bf320d9566a27e60069fc8387448aaa3a094` vor.
Der bisherige Optimierungsstand wurde erfolgreich als portable Windows-Version gebaut. Reale
Zeichnungsvergleiche und manuelle Funktionsprüfungen stehen vor einer Freigabe noch aus.

- Auswahlumrisse und Begrenzungsrechtecke von Kanten wiederverwenden.
- Temporäre Polygone bei Rechtecktransformationen vermeiden.
- Beim Überfahren von Maßtexten nur Farben aktualisieren.
- Vorhandenes SVG-Batching beibehalten, sichtbare Kacheln direkt eingrenzen,
  Platzierung, Kachelgrenze, Renderer-Lebensdauer und A/B-Rückfall absichern.

Der historische `FreeCAD_1.1.4_TechDraw_BatchedSvgHatch_KORRIGIERT.patch` und
`.github/workflows/freecad-techdraw-build.yml` bleiben unverändert als Rückfallstand.
Der neue Patch wird **allein** auf die unveränderten offiziellen Quellen angewendet,
nicht zusätzlich zum historischen Patch.

## Neue Interaktionsoptimierung im Entwicklungsbranch

Zusätzlich enthält der Patch jetzt zwei **zunächst ausgeschaltete** Versuchsfunktionen:
Teilaktualisierung des nativen Bildschirms und eine begrenzte Rastervorschau während
Zoom/Pan. Exakte Szene, Bemaßungsgeometrie und Export bleiben erhalten. Diese Erweiterung
ist **noch nicht im unten verlinkten Windows-Paket enthalten**. Funktionsweise,
Schalter und Grenzen: [Interaktionsanalyse](docs/INTERAKTION.md).

## Schnelle lokale Prüfung (Linux, Qt 5.15)

Git, Python 3, g++, pkg-config, qtbase5-dev und libqt5svg5-dev werden benötigt.
Die kleine Testsuite benötigt weder OCCT noch einen vollständigen FreeCAD-Build.

```sh
git clone --depth 1 --branch 1.1.4 --filter=blob:none --sparse https://github.com/FreeCAD/FreeCAD.git /tmp/freecad-1.1.4
git -C /tmp/freecad-1.1.4 sparse-checkout set src/Mod/TechDraw
python3 scripts/apply_optimizations.py /tmp/freecad-1.1.4 --check
python3 scripts/apply_optimizations.py /tmp/freecad-1.1.4
python3 scripts/run_qt_tests.py /tmp/freecad-1.1.4
python3 scripts/run_qt_tests.py /tmp/freecad-1.1.4 --sanitize
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Das Anwenden auf einen falschen oder bereits veränderten Quellstand wird abgewiesen.
Die Tests kompilieren beide SVG-Schalterstellungen und prüfen Auswahlgeometrie,
Transformationen, Bildgleichheit und tatsächliche geänderte Methoden in kleinen
Testumgebungen. Details und Grenzen: [Validierung](docs/VALIDIERUNG.md).

## GitHub Actions und Windows

Der neue Workflow **FreeCAD 1.1.4 - Optimized TechDraw** bietet:

- `patch-only`: ausschließlich kurze Patch-/Python-Prüfungen.
- `qt-tests`: zusätzlich kompilierte Qt-Tests und Sanitizer unter Linux.
- `validate-artifact`: kurzer Start-/Exporttest eines bereits erzeugten Windows-Archivs,
  ohne erneute Kompilierung; `artifact_run` bezeichnet dessen erfolgreichen Build-Lauf.
- `full-build`: vollständiger Windows-Build nur bei zusätzlicher ausdrücklicher
  Bestätigung `confirm_long_build=true`. Er kann mehrere Stunden dauern.

Pull Requests führen nur die kurzen Linux-Prüfungen aus. Der Windows-Build übernimmt
LibPack, CMake-Installation, Ressourcen-/Modulprüfung und portable Verpackung aus dem
funktionierenden Workflow. LibPack wird wiederverwendet. MSBuild bleibt konservativ
bei zwei parallelen Jobs (optional drei/vier); Compiler-/Buildbaum-Caches werden
nicht ohne Nachweis einer sicheren Integration aktiviert.

Varianten: `upstream`, `optimized`, `optimized-unbatched`. Die letzte Variante nutzt
`TECHDRAW_BATCH_SVG_HATCH=0`, behält aber die übrigen Optimierungen.
Das Archiv separat entpacken und `bin/FreeCAD.exe` starten. Für unabhängige Einstellungen
mit `--user-cfg <separate-Datei>` und `--system-cfg <separate-Datei>` starten und
Testkopien der Zeichnungen verwenden; es wird kein Installer erstellt.

## Portable Testversion herunterladen

Der erfolgreiche [Windows-Build 38748155482](https://github.com/Mattisdenkhaus-cell/FreeCAD-TechDraw-Optimierung/actions/runs/38748155482)
enthält das [vollständige Windows-Paket](https://github.com/Mattisdenkhaus-cell/FreeCAD-TechDraw-Optimierung/actions/runs/38748155482/artifacts/11994042499)
als Artefakt `FreeCAD-1.1.4-TechDraw-optimized-Windows-COMPLETE` (rund 642 MB).
Die Aufbewahrung endet laut GitHub am **22. Oktober 2026 um 17:27 UTC**.
Gebaut wurde Commit `1b46341cb5e7ccef49ddba2030aa61f96886c9fb`. Der anschließende
[Windows-Start-/Exporttest](https://github.com/Mattisdenkhaus-cell/FreeCAD-TechDraw-Optimierung/actions/runs/38862598647)
ist mit allen fünf Prüfgruppen bestanden (Qt offscreen; Details unter Validierung).

1. Bei GitHub anmelden und das Artefakt herunterladen.
2. Die heruntergeladene ZIP-Datei und anschließend das enthaltene `.7z`-Archiv
   mit 7-Zip in einen eigenen Ordner entpacken.
3. PowerShell in diesem entpackten Ordner öffnen und mit eigenen Einstellungen starten:

   ```powershell
   & .\bin\FreeCAD.exe --user-cfg "$PWD\techdraw-user.cfg" --system-cfg "$PWD\techdraw-system.cfg"
   ```

4. Eine **Kopie** einer Zeichnung öffnen und Auswahl, Maßtextbewegung, Zoom,
   Schraffuren und Exporte prüfen. Für vergleichbare Messungen die
   [Benchmark-Anleitung](benchmarks/README.md) verwenden.

Für den einfachen Einstieg gibt es das eigenständige
[Testmakro TechDrawTest.FCMacro](benchmarks/TechDrawTest.FCMacro): eine Datei,
nur das Zeichnungsblatt auswählen. Eine temporäre Testkopie wird automatisch
erstellt; die Ergebnisse landen unter `Downloads`.

[Quellcodeanalyse](docs/ANALYSE.md) · [Technische Entscheidungen](docs/TECHNIK.md) ·
[Benchmark-Anleitung](benchmarks/README.md) · [Fortsetzungsstand](docs/FORTSETZUNG.md)
