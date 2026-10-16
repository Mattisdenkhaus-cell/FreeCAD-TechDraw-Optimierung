"""Interactive entry point for the standalone TechDraw test macro."""
from datetime import datetime
from pathlib import Path

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
    doc = App.ActiveDocument
    if doc is None or not doc.FileName or Gui.activeDocument().Modified:
        QtWidgets.QMessageBox.information(
            parent, title, 'Bitte zuerst eine gespeicherte, unveränderte Kopie deiner '
            'Zeichnung öffnen und die Berechnung abwarten.')
        return None
    pages = [obj for obj in doc.Objects if obj.TypeId == 'TechDraw::DrawPage']
    if not pages:
        QtWidgets.QMessageBox.information(parent, title, 'Das Dokument enthält keine TechDraw-Seite.')
        return None
    names = [f'{page.Label} ({page.Name})' for page in pages]
    chosen, ok = QtWidgets.QInputDialog.getItem(parent, title, 'Welche Seite testen?', names, 0, False)
    if not ok:
        return None
    page = pages[names.index(chosen)]
    label, ok = QtWidgets.QInputDialog.getItem(
        parent, title, 'Welche Version testest du gerade? Diese Angabe kennzeichnet die Messung.',
        ['Optimiert', 'Original'], 0, False)
    if not ok:
        return None
    suggested = str(Path(doc.FileName).with_name(
        f'TechDraw-{label}-{datetime.now():%Y%m%d-%H%M%S}.json'))
    output, _ = QtWidgets.QFileDialog.getSaveFileName(
        parent, 'Messergebnis speichern unter', suggested, 'JSON (*.json)')
    if not output:
        return None
    if not output.lower().endswith('.json'):
        output += '.json'
    QtWidgets.QMessageBox.information(
        parent, title, 'Der Test startet jetzt mit 10 Messungen je Aktion. '
        'Währenddessen bitte nicht klicken, bearbeiten oder das Dokument schließen. '
        'Die Zeichnungsdatei wird nicht gespeichert. Maßposition, Zoom und Auswahl '
        'werden nach dem Test wiederhergestellt. Bei großen Zeichnungen kann das dauern.')

    class InteractiveRunner(Runner):
        def finish(self):
            if self.finished:
                return
            try:
                super().finish()
            except Exception as error:
                QtWidgets.QMessageBox.critical(parent, title, f'Ergebnis konnte nicht geschrieben werden:\n{error}')
                return
            errors = [self.result[key] for key in ('error', 'restore_error') if self.result.get(key)]
            if errors:
                QtWidgets.QMessageBox.warning(
                    parent, title, 'Test fehlgeschlagen; diese Messung nicht vergleichen. '
                    'Die Testkopie ohne Speichern schließen.\n\n' + '\n'.join(errors)
                    + f'\n\nDetails: {self.output}')
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
                parent, title, '\n'.join(rows) + '\n\nKleinere Zeiten sind besser. '
                'Dies misst keine FPS und kein tatsächliches Mausziehen. '
                f'\n\nErgebnis: {self.output}\n\nFür einen Vergleich dieselbe Datei '
                'mit gleichem Fenster, Zoom und Einstellungen in der anderen Version testen.')

    try:
        runner = InteractiveRunner(App, Gui, QtCore, QtWidgets,
                                   {'page': page.Name, 'label': label, 'output': output,
                                    'warmup': 3, 'repeats': 10})
        App._techdraw_test_runner = runner.start()
        return runner
    except Exception as error:
        QtWidgets.QMessageBox.critical(parent, title, f'Test konnte nicht gestartet werden:\n{error}')
        return None
