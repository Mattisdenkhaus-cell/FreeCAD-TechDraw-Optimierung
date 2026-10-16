"""Run the selected page in an automatic temporary copy of the open document."""
from datetime import datetime
from pathlib import Path
import shutil
import tempfile
import uuid

from techdraw_bench import Runner


def start_interactive():
    import FreeCAD as App
    import FreeCADGui as Gui
    from PySide import QtCore, QtWidgets

    parent = Gui.getMainWindow()
    title = 'TechDraw-Test'
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
        parent, title, 'Zeichnungsblatt auswählen – Test läuft in einer automatischen Kopie:',
        names, 0, False)
    if not ok:
        return None
    page_name = pages[names.index(chosen)].Name
    original_name = original.Name
    selection = [(s.DocumentName, s.ObjectName, tuple(s.SubElementNames))
                 for s in Gui.Selection.getSelectionEx()]
    temporary = None
    copy_doc = None
    copy_name = None
    progress = None

    def cleanup():
        # Only the document opened by this invocation may be discarded.
        if copy_name is not None and copy_name in App.listDocuments():
            Gui.getDocument(copy_name).Modified = False
            App.closeDocument(copy_name)
        if original_name in App.listDocuments():
            App.setActiveDocument(original_name)
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
            # This document is disposable. Avoid cross-document undo transactions;
            # closing it discards all temporary dimension changes after the run.
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
            try:
                cleanup()
            except Exception as error:
                failures.append(f'Temporäre Testkopie konnte nicht aufgeräumt werden: {error}')
                if progress is not None:
                    progress.close()
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
                parent, title, '\n'.join(rows) + '\n\nDein Original wurde nicht bearbeitet. '
                'Die temporäre Testkopie wurde geschlossen. Kleinere Zeiten sind besser; '
                'dies misst keine FPS und kein tatsächliches Mausziehen.'
                f'\n\nErgebnis: {self.output}\n\nFür einen Vergleich dieselbe gespeicherte '
                'Zeichnung in beiden Versionen testen und die JSON-Dateien aufbewahren.')

    try:
        progress = QtWidgets.QProgressDialog(
            'Temporäre Testkopie wird vorbereitet …', 'Abbrechen', 0, 66, parent)
        progress.setWindowTitle(title)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        temporary = tempfile.TemporaryDirectory(prefix='techdraw-test-')
        copy_path = Path(temporary.name) / 'TechDrawTest.FCStd'
        saved_source = (bool(original.FileName) and Path(original.FileName).is_file()
                        and not Gui.getDocument(original_name).Modified)
        if saved_source:
            # Preserve identical bytes/hashes for comparisons across FreeCAD versions.
            shutil.copy2(original.FileName, copy_path)
        else:
            # saveCopy includes unsaved edits without renaming/saving the original document.
            original.saveCopy(str(copy_path))
        copy_doc = App.openDocument(str(copy_path))
        copy_name = copy_doc.Name
        copy_doc.recompute()
        copy_page = copy_doc.getObject(page_name)
        projected = next((v for v in copy_page.Views
                          if v.isDerivedFrom('TechDraw::DrawViewPart')), None)
        timer = QtCore.QElapsedTimer()
        timer.start()
        while projected is not None:
            if progress.wasCanceled():
                cleanup()
                return None
            try:
                if not projected.getEdgeByIndex(1).isNull():
                    break
            except ValueError:
                pass
            if timer.elapsed() > 60000:
                raise RuntimeError('Die Testansicht hat nach 60 Sekunden noch keine projizierte Kante.')
            loop = QtCore.QEventLoop()
            QtCore.QTimer.singleShot(20, loop.quit)
            loop.exec_()
        App.setActiveDocument(copy_name)
        Gui.getDocument(copy_name).getObject(page_name).show()
        Gui.updateGui()
        # Recomputing the disposable copy may mark it modified. The original and
        # the copied input bytes remain untouched; only this temporary GUI flag resets.
        Gui.getDocument(copy_name).Modified = False
        documents = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)
        output_dir = Path(documents or App.getUserAppDataDir()) / 'TechDrawTests'
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / f'TechDraw-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}.json'
        runner = InteractiveRunner(App, Gui, QtCore, QtWidgets,
                                   {'page': page_name, 'label': 'automatic-copy', 'output': str(output),
                                    'warmup': 3, 'repeats': 10})
        runner.result['source_label'] = original.Label
        runner.result['freecad_home'] = App.getHomePath()
        runner.result['copy_mode'] = 'saved-file' if saved_source else 'unsaved-snapshot'
        runner.total_steps = 5 * (runner.warmup + runner.repeats) + 1
        runner.completed_steps = 0
        progress.setMaximum(runner.total_steps)
        progress.setLabelText('Zeichnungsblatt wird getestet. Bitte währenddessen nicht bearbeiten.\n'
                              'Gemessen werden Neuzeichnen, Zoom, Verschieben, Auswahl und Maßposition.')
        App._techdraw_test_runner = runner.start()
        return runner
    except Exception as error:
        try:
            cleanup()
        except Exception as cleanup_error:
            error = RuntimeError(f'{error}\nAufräumen: {cleanup_error}')
        QtWidgets.QMessageBox.critical(parent, title, f'Test konnte nicht gestartet werden:\n{error}')
        return None
