"""FreeCAD GUI-step benchmark using document APIs and Qt widgets, never scene items."""
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import tempfile
import time


def summary(samples):
    ordered = sorted(samples)
    if not ordered:
        return {'count': 0, 'status': 'unrun'}
    return {'count': len(ordered), 'status': 'measured',
            'median_ms': statistics.median(ordered),
            'p95_ms': ordered[math.ceil(0.95 * len(ordered)) - 1],
            'min_ms': ordered[0], 'max_ms': ordered[-1]}


class Runner:
    def __init__(self, App, Gui, QtCore, QtWidgets, config):
        self.App, self.Gui, self.QtCore = App, Gui, QtCore
        self.config = config
        self.doc = App.ActiveDocument
        if self.doc is None:
            raise RuntimeError('Open the same saved test drawing in each FreeCAD version first.')
        if not self.doc.FileName or not Path(self.doc.FileName).is_file():
            raise RuntimeError('The benchmark needs a saved FCStd fixture for a reproducible hash.')
        if Gui.activeDocument().Modified:
            raise RuntimeError('Use an unmodified saved fixture; save your work before benchmarking.')
        pages = [obj for obj in self.doc.Objects if obj.TypeId == 'TechDraw::DrawPage']
        page_name = config.get('page')
        self.page = self.doc.getObject(page_name) if page_name else (pages[0] if pages else None)
        if self.page is None or self.page.TypeId != 'TechDraw::DrawPage':
            raise RuntimeError('No TechDraw page found.')
        # The copy launcher has already displayed and flushed this exact page.
        if not config.get('page_already_shown', False):
            Gui.activeDocument().getObject(self.page.Name).show()
            Gui.updateGui()
        mdi = Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
        window = mdi.activeSubWindow() if mdi else None
        views = window.findChildren(QtWidgets.QGraphicsView) if window else []
        if len(views) != 1:
            raise RuntimeError('Expected one graphics VIEW widget in the active TechDraw page.')
        self.view = views[0]  # QWidget only: no scene(), items(), or ownership manipulation
        self.viewport = self.view.viewport()
        self.saved_transform = self.view.transform()
        self.saved_scroll = (self.view.horizontalScrollBar().value(), self.view.verticalScrollBar().value())
        self.saved_selection = [(s.DocumentName, s.ObjectName, tuple(s.SubElementNames))
                                for s in Gui.Selection.getSelectionEx()]
        self.selection_diagnostics = bool(config.get('selection_diagnostics', False))
        names = (['edge_selection'] if self.selection_diagnostics else
                 ['redraw', 'zoom', 'pan', 'edge_selection', 'dimension_property_move'])
        self.samples = {name: [] for name in names}
        self.selection_phases = []
        self.selection_warmup = []
        self.notes = {}
        self.warmup = int(config.get('warmup', 5))
        self.repeats = int(config.get('repeats', 30))
        if not 0 <= self.warmup <= 100 or not 1 <= self.repeats <= 1000:
            raise ValueError('Invalid warmup/repeats (limits: 100/1000).')
        page_views = list(self.page.Views)
        edge_name = config.get('view')
        self.edge_view = self.doc.getObject(edge_name) if edge_name else next(
            (v for v in page_views if v.isDerivedFrom('TechDraw::DrawViewPart')), None)
        self.edge = config.get('edge', 'Edge1')
        dim_name = config.get('dimension')
        self.dimension = self.doc.getObject(dim_name) if dim_name else next(
            (v for v in page_views if v.TypeId == 'TechDraw::DrawViewDimension'), None)
        self.dimension_xy = (self.dimension.X.Value, self.dimension.Y.Value) if self.dimension else None
        self.output = Path(config.get('output', str(Path(tempfile.gettempdir()) / 'techdraw-benchmark.json')))
        self.result = {
            'schema': 1, 'label': config.get('label', 'unspecified'),
            'freecad': App.Version(), 'qt': QtCore.qVersion(), 'platform': platform.platform(),
            'fixture_sha256': hashlib.sha256(Path(self.doc.FileName).read_bytes()).hexdigest(),
            'page': self.page.Name, 'view': self.edge_view.Name if self.edge_view else None,
            'edge': self.edge, 'dimension': self.dimension.Name if self.dimension else None,
            'viewport_px': [self.viewport.width(), self.viewport.height()],
            'device_pixel_ratio': self.viewport.devicePixelRatioF(),
            'initial_transform': [getattr(self.saved_transform, f'm{r}{c}')() for r in range(1, 4) for c in range(1, 4)],
            'initial_scroll': self.saved_scroll,
            'warmup': self.warmup, 'repeats': self.repeats,
            'fixture_kind': config.get('fixture_kind', 'unspecified'),
            'renderer_note': config.get('renderer_note', 'record renderer/settings manually'),
            'metric': 'GUI step wall time incl. synchronous viewport repaint; not FPS or GPU completion',
        }
        if self.selection_diagnostics:
            prefs = App.ParamGet('User parameter:BaseApp/Preferences/Mod/TechDraw/General')
            mode = self.view.viewportUpdateMode()
            self.result['diagnostics'] = {
                'kind': 'selection-phases-v1',
                'navigation_preview_preference': prefs.GetBool('NavigationPreview', False),
                'partial_viewport_updates_preference': prefs.GetBool('PartialViewportUpdates', False),
                'viewport_class': self.viewport.metaObject().className(),
                'viewport_update_mode': int(getattr(mode, 'value', mode)),
                'viewport_visible': self.viewport.isVisible(),
                'viewport_region_empty': self.viewport.visibleRegion().isEmpty(),
                'open_document_count': len(App.listDocuments()),
                'document_object_count': len(self.doc.Objects),
                'page_view_count': len(page_views),
                'graphics_view_count': len(Gui.getMainWindow().findChildren(QtWidgets.QGraphicsView)),
                'note': 'Preferences do not prove patch presence. Timings include synchronous selection observers; no FPS or CPU profile.',
            }
        self.operations = iter((name, i) for name in self.samples for i in range(self.warmup + self.repeats))
        self.finished = False
        self.drag_transaction = False
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.step)

    def start(self):
        # Dimension updates are undone as one transaction; no files are saved.
        self.doc.openTransaction('TechDraw benchmark (temporary)')
        self.drag_transaction = True
        self.timer.start(100)
        return self

    def operation(self, name, i):
        self.last_selection_phases = {}
        def timed(phase, callback):
            if not self.selection_diagnostics or name != 'edge_selection':
                return callback()
            started = time.perf_counter_ns()
            value = callback()
            self.last_selection_phases[phase] = (time.perf_counter_ns() - started) / 1e6
            return value

        sign = 1 if i % 2 == 0 else -1
        if name == 'redraw':
            pass
        elif name == 'zoom':
            self.view.setTransform(self.saved_transform)
            self.view.scale(1.05 if sign > 0 else 0.95, 1.05 if sign > 0 else 0.95)
        elif name == 'pan':
            bar = self.view.horizontalScrollBar()
            base = self.saved_scroll[0]
            target = max(bar.minimum(), min(bar.maximum(), base + sign * 25))
            if bar.minimum() == bar.maximum() or target == bar.value():
                return 'No available scroll range; zoom in identically before both runs.'
            bar.setValue(target)
        elif name == 'edge_selection':
            if self.edge_view is None:
                return 'No drawing view on page.'
            timed('clear_selection', self.Gui.Selection.clearSelection)
            timed('add_selection', lambda: self.Gui.Selection.addSelection(
                self.doc.Name, self.edge_view.Name, self.edge))
            selected = timed('verify_selection', self.Gui.Selection.getSelectionEx)
            if not any(s.ObjectName == self.edge_view.Name and self.edge in s.SubElementNames for s in selected):
                raise RuntimeError('Edge selection was not accepted.')
        elif name == 'dimension_property_move':
            if self.dimension is None:
                return 'No dimension on page.'
            # Model-property move deliberately includes recompute. This is not a mouse drag.
            self.dimension.X = self.dimension_xy[0] + sign
            self.dimension.Y = self.dimension_xy[1]
            self.doc.recompute()
        timed('gui_update', self.Gui.updateGui)
        timed('viewport_repaint', self.viewport.repaint)
        return None

    def step(self):
        try:
            name, i = next(self.operations)
        except StopIteration:
            self.finish()
            return
        try:
            if i == 0:
                self.view.setTransform(self.saved_transform)
                self.view.horizontalScrollBar().setValue(self.saved_scroll[0])
                self.view.verticalScrollBar().setValue(self.saved_scroll[1])
                self.Gui.updateGui()
            started = time.perf_counter_ns()
            skipped = self.operation(name, i)
            elapsed = (time.perf_counter_ns() - started) / 1e6
            if skipped:
                self.notes[name] = skipped
            elif self.selection_diagnostics and i < self.warmup:
                self.selection_warmup.append({'total_ms': elapsed, 'phases_ms': self.last_selection_phases})
            elif i >= self.warmup:
                self.samples[name].append(elapsed)
                if self.selection_diagnostics:
                    self.selection_phases.append(self.last_selection_phases)
        except Exception as error:
            self.result['error'] = f'{type(error).__name__}: {error}'
            self.finish()
            return
        self.timer.start(0)

    def finish(self):
        if self.finished:
            return
        restore_started = time.perf_counter_ns()
        self.finished = True
        self.timer.stop()
        try:
            if self.drag_transaction:
                self.doc.abortTransaction()
                self.doc.recompute()
            self.view.setTransform(self.saved_transform)
            self.view.horizontalScrollBar().setValue(self.saved_scroll[0])
            self.view.verticalScrollBar().setValue(self.saved_scroll[1])
            self.Gui.Selection.clearSelection()
            for document, obj, subs in self.saved_selection:
                if subs:
                    for sub in subs:
                        self.Gui.Selection.addSelection(document, obj, sub)
                else:
                    self.Gui.Selection.addSelection(document, obj)
            self.Gui.updateGui()
        except Exception as error:
            self.result['restore_error'] = str(error)
        self.result['samples_ms'] = self.samples
        self.result['summary'] = {name: summary(values) for name, values in self.samples.items()}
        self.result['notes'] = self.notes
        if self.selection_diagnostics:
            self.result['selection_phases_ms'] = self.selection_phases
            self.result['selection_warmup'] = self.selection_warmup
            self.result['restore_ms'] = (time.perf_counter_ns() - restore_started) / 1e6
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text(json.dumps(self.result, indent=2), encoding='utf-8')
        self.App.Console.PrintMessage(f'TechDraw benchmark written: {self.output}\n')


def start():
    import FreeCAD as App
    import FreeCADGui as Gui
    from PySide import QtCore, QtGui
    try:
        from PySide import QtWidgets
    except ImportError:
        QtWidgets = QtGui
    config_path = os.environ.get('TECHDRAW_BENCH_CONFIG')
    config = json.loads(Path(config_path).read_text(encoding='utf-8')) if config_path else {}
    return Runner(App, Gui, QtCore, QtWidgets, config).start()
