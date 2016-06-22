# Copyright 2016 Sam Creasey, sammy@sammy.net.  All rights reserved.
#
# TODO sammy find the right GPL3 preamble for this

import datetime
import os.path

from PySide import QtCore, QtGui

import ui_sync_dialog
import ui_sync_widget

class _SyncWidget(QtGui.QWidget):
    def __init__(self, parent, log):
        self._parent = parent
        QtGui.QWidget.__init__(self)
        self._ui = ui_sync_widget.Ui_Form()
        self._ui.setupUi(self)
        self.log = log
        self._ui.fileName.setText(os.path.basename(log.filename))
        dt = datetime.datetime.utcfromtimestamp(self.log.times()[0])
        self._ui.startTime.setText('%04d-%02d-%02d %02d:%02d:%02.3f' % (
            dt.year, dt.month, dt.day,
            dt.hour, dt.minute, dt.second + dt.microsecond / 1e6))
        self._ui.duration.setText('%.3f' % (
            self.log.times()[-1] - self.log.times()[0]))
        self.update_start_value()
        self._ui.startOffset.valueChanged.connect(
            self._start_offset_changed)

    def _start_offset_changed(self, value):
        self.log.update_relative_time(self.log.times()[0] - value);
        self._parent.time_changed.emit()

    def update_start_value(self):
        self._ui.startOffset.setValue(
            self.log.times()[0] - self.log.relative_start_time)

class SyncDialog(QtGui.QDialog):
    time_changed = QtCore.Signal()

    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        self._ui = ui_sync_dialog.Ui_Dialog()
        self._ui.setupUi(self)
        self._ui.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(
            self._handle_apply_trigger)
        self.setWindowModality(QtCore.Qt.NonModal)
        self._log_widgets = dict()

    def add_log(self, log):
        log_widget = _SyncWidget(self, log)
        self._log_widgets[log] = log_widget
        self._ui.verticalLayout.insertWidget(
            len(self._log_widgets) - 1, log_widget)

        # If this is the first log added, populate the trigger
        # selection box.
        if len(self._log_widgets) == 1:
            self._ui.eventBox.clear()
            for item in log.records.itervalues():
                self._ui.eventBox.addItem(item.name)

    def _handle_apply_trigger(self):
        if not self._ui.eventBox.currentText():
            return
        self.apply_trigger(self._ui.eventBox.currentText(),
                           self._ui.triggerSpinBox.value())

    def apply_trigger(self, field_name, value):
        for log_widget in self._log_widgets.itervalues():
            log = log_widget.log
            for index, logged_data in enumerate(log.all(field_name)):
                if logged_data > value:
                    log.update_relative_time(log.times()[index])
                    log_widget.update_start_value()
                    break
        self.time_changed.emit()
