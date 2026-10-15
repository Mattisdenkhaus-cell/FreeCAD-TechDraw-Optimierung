#!/usr/bin/env python3
"""Build/run small Qt-only tests against the actual patched headers; no FreeCAD build."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--qt-prefix', type=Path, help='Optional extracted Debian Qt dev package prefix')
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    source = args.source.resolve()
    root = Path(__file__).resolve().parents[1]
    gui = source / 'src/Mod/TechDraw/Gui'
    if args.qt_prefix:
        includes = args.qt_prefix.resolve() / 'usr/include/x86_64-linux-gnu/qt5'
        flags = [f'-I{includes}'] + [f'-I{includes / module}' for module in ['QtCore', 'QtGui', 'QtWidgets', 'QtSvg']]
        libs = [f'-l:lib{module}.so.5' for module in ['Qt5Svg', 'Qt5Widgets', 'Qt5Gui', 'Qt5Core']]
    else:
        flags = shlex.split(subprocess.check_output(['pkg-config', '--cflags', 'Qt5Widgets', 'Qt5Svg'], text=True))
        libs = shlex.split(subprocess.check_output(['pkg-config', '--libs', 'Qt5Widgets', 'Qt5Svg'], text=True))
    with tempfile.TemporaryDirectory(prefix='techdraw-qt-') as temp:
        executable = Path(temp) / 'qt_geometry'
        # Same configuration as FreeCAD SetupQt.cmake for Qt >= 5.15.
        template = (source / 'src/QtCore.h.cmake').read_text()
        (Path(temp) / 'QtCore.h').write_text(template.replace(
            '#cmakedefine HAVE_Q_DISABLE_COPY_MOVE', '#define HAVE_Q_DISABLE_COPY_MOVE 1'))
        command = [os.environ.get('CXX', 'g++'), '-std=c++17', '-O2', '-fPIC', '-Wall', '-Wextra', '-Werror',
                   '-DTechDrawGuiExport=', f'-I{temp}', f'-I{source / "src"}', f'-I{gui}', *flags,
                   str(root / 'tests/qt_geometry.cpp'), str(gui / 'QGCustomRect.cpp'),
                   str(gui / 'QGCustomSvg.cpp'), *libs, '-o', str(executable)]
        if args.sanitize:
            command[1:1] = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        subprocess.run(command, check=True)
        environment = dict(os.environ, QT_QPA_PLATFORM='offscreen', XDG_CACHE_HOME=temp, XDG_RUNTIME_DIR=temp)
        if args.sanitize:
            # Qt's offscreen platform retains process-global objects at shutdown.
            environment['ASAN_OPTIONS'] = 'detect_leaks=0'
        subprocess.run([str(executable)], env=environment, check=True)


if __name__ == '__main__':
    main()
