#!/usr/bin/env python3
"""Build/run small Qt-only tests against the actual patched headers; no FreeCAD build."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile


def extract_method(source, signature):
    if source.count(signature) != 1:
        raise RuntimeError(f'Expected exactly one method: {signature}')
    start = source.index(signature)
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        if source[end] == '{': depth += 1
        if source[end] == '}': depth -= 1
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--qt-prefix', type=Path, help='Optional extracted Debian Qt dev package prefix')
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--navigation-only', action='store_true', help='Only native viewport/navigation tests')
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
        methods = []
        for filename, signatures in {
            'QGIEdge.cpp': ['QRectF QGIEdge::boundingRect() const', 'QPainterPath QGIEdge::shape() const'],
            'QGIViewDimension.cpp': ['void QGIViewDimension::hover(bool state)',
                'void QGIViewDimension::setPrettyPre()', 'void QGIViewDimension::setPrettySel()',
                'void QGIViewDimension::setPrettyNormal()'],
        }.items():
            contents = (gui / filename).read_text()
            methods.extend(extract_method(contents, signature) for signature in signatures)
        (Path(temp) / 'patched_methods.inc').write_text('\n'.join(methods))
        page = (gui / 'QGVPage.cpp').read_text()
        (Path(temp) / 'navigation_paint.inc').write_text('\n'.join(
            extract_method(page, signature) for signature in [
                'void QGVPage::paintEvent(QPaintEvent* event)',
                'void QGVPage::setRenderer(RendererType type)',
                'void QGVPage::beginNavigationPreview()',
                'void QGVPage::drawBackground(QPainter* painter, const QRectF& rect)']))
        nav = (gui / 'QGVNavStyle.cpp').read_text()
        (Path(temp) / 'navigation_hooks.inc').write_text('\n'.join(
            extract_method(nav, signature) for signature in [
                'void QGVNavStyle::zoom(double factor)', 'void QGVNavStyle::pan(QPoint p)']))
        face = (gui / 'QGIFace.cpp').read_text()
        (Path(temp) / 'hatch_method.inc').write_text(extract_method(face, 'void QGIFace::buildSvgHatch()'))
        ctor = extract_method(face, 'QGIFace::QGIFace(int index)')
        begin = ctor.index('#if TECHDRAW_BATCH_SVG_HATCH')
        end = ctor.index('#endif', begin) + len('#endif')
        (Path(temp) / 'hatch_constructor.inc').write_text(ctor[begin:end])
        test_sources = ([str(root / 'tests/qt_navigation_main.cpp'),
                         str(root / 'tests/qt_navigation.cpp')] if args.navigation_only else
                        [str(root / 'tests/qt_geometry.cpp'), str(root / 'tests/qt_navigation.cpp'),
                         str(root / 'tests/qt_integration.cpp'), str(root / 'tests/qt_hatch_integration.cpp'),
                         str(gui / 'QGCustomRect.cpp'), str(gui / 'QGCustomSvg.cpp')])
        command = [os.environ.get('CXX', 'g++'), '-std=c++17', '-O2', '-fPIC', '-Wall', '-Wextra', '-Werror',
                   '-DTechDrawGuiExport=', f'-I{temp}', f'-I{source / "src"}', f'-I{gui}', *flags,
                   *test_sources, *libs, '-o', str(executable)]
        if args.sanitize:
            command[1:1] = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        environment = dict(os.environ, QT_QPA_PLATFORM='offscreen', XDG_CACHE_HOME=temp, XDG_RUNTIME_DIR=temp)
        if args.sanitize:
            # Qt's offscreen platform retains process-global objects at shutdown.
            environment['ASAN_OPTIONS'] = 'detect_leaks=0'
        for batch_mode in ((1,) if args.navigation_only else (1, 0)):
            subprocess.run(command + [f'-DTECHDRAW_BATCH_SVG_HATCH={batch_mode}'], check=True)
            for scale in (('1', '1.25', '1.5', '2') if args.navigation_only else ('1',)):
                environment['QT_SCALE_FACTOR'] = scale
                subprocess.run([str(executable)], env=environment, check=True)


if __name__ == '__main__':
    main()
