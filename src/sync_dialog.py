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
        self._log = log
        self._ui.fileName.setText(os.path.basename(log.filename))
        dt = datetime.datetime.utcfromtimestamp(self._log.times()[0])
        self._ui.startTime.setText('%04d-%02d-%02d %02d:%02d:%02.3f' % (
            dt.year, dt.month, dt.day,
            dt.hour, dt.minute, dt.second + dt.microsecond / 1e6))
        self._ui.duration.setText('%.3f' % (
            self._log.times()[-1] - self._log.times()[0]))
        self._ui.startOffset.setValue(
            self._log.relative_start_time - self._log.times()[0])
        self._ui.startOffset.valueChanged.connect(
            self._start_offset_changed)

    def _start_offset_changed(self, value):
        self._log.update_relative_time(self._log.times()[0] - value);
        self._parent.time_changed.emit()


class SyncDialog(QtGui.QDialog):
    time_changed = QtCore.Signal()

    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        self._ui = ui_sync_dialog.Ui_Dialog()
        self._ui.setupUi(self)
        self.setWindowModality(QtCore.Qt.NonModal)
        self._log_widgets = dict()

    def add_log(self, log):
        log_widget = _SyncWidget(self, log)
        self._log_widgets[log] = log_widget
        self._ui.verticalLayout.insertWidget(
            len(self._log_widgets) - 1, log_widget)
