# FreeCAD TechDraw – Performance-Entwicklung für 1.1.4

Entwicklungsstand für flüssigere Bearbeitung bereits berechneter Zeichnungen.
Die Änderungen liegen als **gemeinsamer C++-Patch** für den verifizierten
FreeCAD-Commit `4fd3bf320d9566a27e60069fc8387448aaa3a094` vor.
Eine neue portable Windows-Version wurde noch nicht gebaut oder freigegeben.

- Auswahlumrisse und Begrenzungsrechtecke von Kanten wiederverwenden.
- Temporäre Polygone bei Rechtecktransformationen vermeiden.
- Beim Überfahren von Maßtexten nur Farben aktualisieren.
- Vorhandenes SVG-Batching beibehalten, sichtbare Kacheln direkt eingrenzen,
  Platzierung, Kachelgrenze, Renderer-Lebensdauer und A/B-Rückfall absichern.

Der historische `FreeCAD_1.1.4_TechDraw_BatchedSvgHatch_KORRIGIERT.patch` und
`.github/workflows/freecad-techdraw-build.yml` bleiben unverändert als Rückfallstand.
Der neue Patch wird **allein** auf die unveränderten offiziellen Quellen angewendet,
nicht zusätzlich zum historischen Patch.

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

[Quellcodeanalyse](docs/ANALYSE.md) · [Technische Entscheidungen](docs/TECHNIK.md) ·
[Benchmark-Anleitung](benchmarks/README.md) · [Fortsetzungsstand](docs/FORTSETZUNG.md)
