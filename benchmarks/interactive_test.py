"""Test a selected page; use a copy for model edits or unsaved input."""
from datetime import datetime
from pathlib import Path
import json
import hashlib
import shutil
import tempfile
import time
import uuid

from techdraw_bench import Runner


def projection_snapshot(page):
    """Read public projection state, including projection-group children.

    A first edge is evidence of geometry, not proof that face extraction has ended.
    """
    pending = list(page.Views)
    seen, result = set(), []
    while pending:
        view = pending.pop(0)
        if view.Name in seen:
            continue
        seen.add(view.Name)
        pending.extend(getattr(view, 'Views', []))
        if not view.isDerivedFrom('TechDraw::DrawViewPart'):
            continue
        row = {'name': view.Name, 'type': view.TypeId, 'state': list(view.State)}
        try:
            row['first_edge_available'] = not view.getEdgeByIndex(1).isNull()
        except Exception as error:
            row['first_edge_available'] = False
            row['edge_error'] = f'{type(error).__name__}: {error}'
        result.append(row)
    return result


def start_interactive(selection_diagnostics=False):
    import FreeCAD as App
    import FreeCADGui as Gui
    from PySide import QtCore, QtWidgets

    parent = Gui.getMainWindow()
    title = 'TechDraw-Auswahldiagnose' if selection_diagnostics else 'TechDraw-Test'
    previous = getattr(App, '_techdraw_test_runner', None)
    if previous is not None and not previous.finished:
        QtWidgets.QMessageBox.information(parent, title, 'Ein Test läuft bereits.')
        return previous
    original = App.ActiveDocument
    if original is None:
        QtWidgets.QMessageBox.information(parent, title, 'Bitte zuerst deine Zeichnung öffnen.')
        return None
    pages = [obj for obj in original.Objects if obj.TypeId == 'TechDraw::DrawPage']
    if not pages:
        QtWidgets.QMessageBox.information(parent, title, 'Das Dokument enthält keine TechDraw-Seite.')
        return None
    names = [f'{page.Label} ({page.Name})' for page in pages]
    chosen, ok = QtWidgets.QInputDialog.getItem(
        parent, title, 'Zeichnungsblatt auswählen:',
        names, 0, False)
    if not ok:
        return None
    started = time.perf_counter_ns()
    page_name = pages[names.index(chosen)].Name
    original_name = original.Name
    selection = [(s.DocumentName, s.ObjectName, tuple(s.SubElementNames))
                 for s in Gui.Selection.getSelectionEx()]
    temporary = None
    test_doc = None
    copy_name = None
    progress = None
    preparation = {}
    output = None
    preparing = True
    use_existing = False
    trace = {'status': 'preparing', 'stage': 'initialize', 'page': page_name,
             'freecad': App.Version(), 'qt': QtCore.qVersion(),
             'freecad_home': App.getHomePath(), 'preparation_ms': preparation}

    def checkpoint(stage):
        trace['stage'] = stage
        trace['elapsed_ms'] = (time.perf_counter_ns() - started) / 1e6
        if preparing and output is not None:
            output.write_text(json.dumps(trace, indent=2), encoding='utf-8')

    def prepare(phase, callback):
        checkpoint(phase)
        before = time.perf_counter_ns()
        try:
            value = callback()
        finally:
            preparation[phase] = (time.perf_counter_ns() - before) / 1e6
            checkpoint(phase)
        return value

    def cleanup(restore_selection=True):
        # Only the document opened by this invocation may be discarded.
        if copy_name is not None and copy_name in App.listDocuments():
            Gui.getDocument(copy_name).Modified = False
            checkpoint('close_copy')  # FreeCAD may wait for running projection workers here.
            App.closeDocument(copy_name)
        if original_name in App.listDocuments():
            App.setActiveDocument(original_name)
        if restore_selection:
            Gui.Selection.clearSelection()
            for document, obj, subs in selection:
                for sub in subs or ('',):
                    Gui.Selection.addSelection(document, obj, sub)
        if temporary is not None:
            temporary.cleanup()
        if progress is not None:
            progress.close()

    class InteractiveRunner(Runner):
        def start(self):
            # Full tests edit only the disposable copy. Direct diagnostics select
            # edges only; neither path needs a cross-document undo transaction.
            self.started_at = time.perf_counter_ns()
            self.timer.start(100)
            return self

        def step(self):
            if progress.wasCanceled():
                self.result['error'] = 'Test vom Benutzer abgebrochen.'
                self.finish()
                return
            self.completed_steps += 1
            progress.setValue(min(self.completed_steps, self.total_steps - 1))
            super().step()

        def finish(self):
            if self.finished:
                return
            failures = []
            try:
                super().finish()
                failures.extend(self.result[key] for key in ('error', 'restore_error')
                                if self.result.get(key))
            except Exception as error:
                failures.append(f'Ergebnis konnte nicht geschrieben werden: {error}')
            run_finished = time.perf_counter_ns()
            try:
                cleanup(restore_selection=not use_existing or bool(self.result.get('restore_error')))
            except Exception as error:
                failures.append(f'Temporäre Testkopie konnte nicht aufgeräumt werden: {error}')
                if progress is not None:
                    progress.close()
            if self.selection_diagnostics:
                self.result['lifecycle_ms'] = {
                    'preparation': preparation,
                    'run_including_restore': (run_finished - self.started_at) / 1e6,
                    'cleanup': (time.perf_counter_ns() - run_finished) / 1e6,
                    'total_after_page_choice': (time.perf_counter_ns() - started) / 1e6,
                }
                if failures:
                    self.result['error'] = '\n'.join(failures)
                try:
                    self.output.write_text(json.dumps(self.result, indent=2), encoding='utf-8')
                except Exception as error:
                    failures.append(f'Diagnose konnte nicht geschrieben werden: {error}')
            if failures:
                QtWidgets.QMessageBox.warning(
                    parent, title, 'Test nicht erfolgreich abgeschlossen; diese Messung nicht '
                    'vergleichen.\n\n' + '\n'.join(failures) + f'\n\nErgebnisdatei: {self.output}')
                return
            labels = {'redraw': 'Neuzeichnen', 'zoom': 'Zoom', 'pan': 'Verschieben',
                      'edge_selection': 'Kantenauswahl per API',
                      'dimension_property_move': 'Maßposition per Eigenschaft'}
            rows = []
            for name, stats in self.result['summary'].items():
                if stats['count'] == self.repeats:
                    rows.append(f"{labels[name]}: {stats['median_ms']:.2f} ms "
                                f"(p95: {stats['p95_ms']:.2f} ms)")
                else:
                    rows.append(f'{labels[name]}: nicht vollständig gemessen '
                                '(z. B. kein Scrollbereich oder keine Bemaßung)')
            QtWidgets.QMessageBox.information(
                parent, title, '\n'.join(rows) + '\n\n' +
                ('Geometrie und Bemaßungen wurden nicht verändert; die Auswahl wurde wiederhergestellt. '
                 if use_existing else 'Dein Original wurde nicht bearbeitet. Die temporäre Testkopie wurde geschlossen. ') +
                'Kleinere Zeiten sind besser; '
                'dies misst keine FPS und kein tatsächliches Mausziehen.'
                f'\n\nErgebnis: {self.output}\n\nFür einen Vergleich dieselbe gespeicherte '
                'Zeichnung in beiden Versionen testen und die JSON-Dateien aufbewahren.')

    try:
        downloads = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DownloadLocation)
        output_dir = Path(downloads) if downloads else Path.home() / 'Downloads'
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / f'TechDraw-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}.json'
        checkpoint('initialize')
        try:
            import Part
            trace['occ'] = Part.OCC_VERSION
        except (ImportError, AttributeError):
            trace['occ'] = None
        progress = QtWidgets.QProgressDialog(
            'Temporäre Testkopie wird vorbereitet …', 'Abbrechen', 0, 66, parent)
        progress.setWindowTitle(title)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        saved_source = (bool(original.FileName) and Path(original.FileName).is_file()
                        and not Gui.getDocument(original_name).Modified)
        active_view = Gui.getDocument(original_name).activeView()
        active_page = active_view.getPage() if hasattr(active_view, 'getPage') else None
        use_existing = (selection_diagnostics and saved_source and active_page is not None
                        and active_page.Name == page_name)
        if use_existing:
            # Selection-only diagnostics do not change model properties or recompute.
            test_doc = original
            copy_path = Path(original.FileName)
            trace['copy_mode'] = 'existing-document'
            progress.setLabelText('Vorhandenes Blatt wird geprüft – keine erneute Dokumentkopie.')
        else:
            temporary = tempfile.TemporaryDirectory(prefix='techdraw-test-')
            copy_path = Path(temporary.name) / 'TechDrawTest.FCStd'
            if saved_source:
                # Preserve identical bytes/hashes for comparisons across FreeCAD versions.
                prepare('copy_saved_file', lambda: shutil.copy2(original.FileName, copy_path))
            else:
                # saveCopy includes unsaved edits without renaming/saving the original document.
                prepare('save_unsaved_snapshot', lambda: original.saveCopy(str(copy_path)))
            trace['copy_mode'] = 'saved-file' if saved_source else 'unsaved-snapshot'
            trace['fixture_sha256'] = hashlib.sha256(copy_path.read_bytes()).hexdigest()
            test_doc = prepare('open_copy', lambda: App.openDocument(str(copy_path)))
            copy_name = test_doc.Name
        trace['fixture_sha256'] = hashlib.sha256(copy_path.read_bytes()).hexdigest()
        trace['document_object_count'] = len(test_doc.Objects)
        trace['invalid_objects'] = [o.Name for o in test_doc.Objects if 'Invalid' in o.State]
        if not use_existing:
            prepare('recompute_copy', test_doc.recompute)
        test_page = test_doc.getObject(page_name)
        projected = next((v for v in test_page.Views
                          if v.isDerivedFrom('TechDraw::DrawViewPart')), None)
        timer = QtCore.QElapsedTimer()
        timer.start()
        last_snapshot = -1000
        while projected is not None:
            elapsed = timer.elapsed()
            if elapsed - last_snapshot >= 1000:
                trace['projection_state'] = projection_snapshot(test_page)
                preparation['wait_projection'] = elapsed
                checkpoint('wait_projection')
                last_snapshot = elapsed
            if progress.wasCanceled():
                trace['status'] = 'cancelled'
                trace['error'] = 'Vorbereitung vom Benutzer abgebrochen.'
                checkpoint('wait_projection')
                cleanup()
                checkpoint('cancelled')
                return None
            try:
                if not projected.getEdgeByIndex(1).isNull():
                    break
            except ValueError:
                pass
            if timer.elapsed() > 60000:
                raise RuntimeError(f'Die Testansicht {projected.Name} hat nach 60 Sekunden noch keine '
                                   'projizierte Kante. Die Vorbereitung wurde protokolliert.')
            loop = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(20, loop.quit)
            loop.exec_()
        preparation['wait_projection'] = timer.elapsed()
        trace['projection_state'] = projection_snapshot(test_page)
        if not use_existing:
            App.setActiveDocument(test_doc.Name)
            prepare('show_page', Gui.getDocument(test_doc.Name).getObject(page_name).show)
            prepare('initial_gui_update', Gui.updateGui)
        # Recomputing the disposable copy may mark it modified. The original and
        # the copied input bytes remain untouched; only this temporary GUI flag resets.
        if not use_existing:
            Gui.getDocument(copy_name).Modified = False
        runner = prepare('initialize_runner', lambda: InteractiveRunner(App, Gui, QtCore, QtWidgets,
                                   {'page': page_name, 'label': 'automatic-copy', 'output': str(output),
                                    'page_already_shown': True,
                                    'warmup': 1 if selection_diagnostics else 3,
                                    'repeats': 3 if selection_diagnostics else 10,
                                    'selection_diagnostics': selection_diagnostics}))
        runner.result['source_label'] = original.Label
        runner.result['freecad_home'] = App.getHomePath()
        runner.result['copy_mode'] = trace['copy_mode']
        trace['status'] = 'prepared'
        checkpoint('prepared')
        # Runner owns this same output after setup; cleanup must not overwrite it.
        preparing = False
        runner.result['preparation_diagnostic'] = dict(trace)
        runner.total_steps = len(runner.samples) * (runner.warmup + runner.repeats) + 1
        runner.completed_steps = 0
        progress.setMaximum(runner.total_steps)
        progress.setLabelText('Zeichnungsblatt wird getestet. Bitte währenddessen nicht bearbeiten.\n' +
                             ('Nur Kantenauswahl: 1 Aufwärmschritt und 3 Messschritte.' if selection_diagnostics else
                              'Gemessen werden Neuzeichnen, Zoom, Verschieben, Auswahl und Maßposition.'))
        App._techdraw_test_runner = runner.start()
        return runner
    except Exception as error:
        trace['status'] = 'failed'
        trace['error'] = f'{type(error).__name__}: {error}'
        trace['failed_stage'] = trace['stage']
        try:
            checkpoint(trace['stage'])  # Persist BEFORE cleanup can wait for workers.
        except OSError:
            pass
        try:
            cleanup()
        except Exception as cleanup_error:
            trace['cleanup_error'] = str(cleanup_error)
            error = RuntimeError(f'{error}\nAufräumen: {cleanup_error}')
        try:
            checkpoint('failed')
        except OSError:
            pass
        report_path = f'\n\nDiagnose: {output}' if output is not None and output.is_file() else ''
        QtWidgets.QMessageBox.critical(parent, title, f'Test konnte nicht gestartet werden:\n{error}{report_path}')
        return None
