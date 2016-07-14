#!/usr/bin/env python

# Copyright 2015 Josh Pieper, jjp@pobox.com.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import datetime
import os
import sys
import time

import matplotlib

matplotlib.use('Qt4Agg')
matplotlib.rcParams['backend.qt4'] = 'PySide'

from matplotlib.backends import backend_qt4agg
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

import PySide.QtCore as QtCore
import PySide.QtGui as QtGui

SCRIPT_PATH=os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(SCRIPT_PATH, '../python'))
sys.path.append(os.path.join(SCRIPT_PATH, 'build-x86_64'))
import ui_tplot_main_window

import course_map_dialog
import rc_data
import sync_dialog

AXES = ['Left', 'Right', '3', '4']

LEGEND_LOC = {
    'Left': 2,
    'Right': 1,
    '3': 7,
    '4': 4
    }

ALL_LOGS_STR = 'All'

class BoolGuard(object):
    def __init__(self):
        self.value = False

    def __enter__(self):
        self.value = True

    def __exit__(self, type, value, traceback):
        self.value = False

    def active(self):
        return self.value


def _make_timestamp_getter(all_data):
    if len(all_data) == 0:
        return lambda x: 0.0
    sample = all_data[0]

    # If any children have a timestamp field, use the first one we can
    # find.
    def find_child(prefix, value):
        if hasattr(value, 'timestamp'):
            return lambda x: _get_data(x, prefix + 'timestamp')
        if not hasattr(value, '_fields'):
            return None
        for child in value._fields:
            result = find_child(prefix + child + '.', getattr(value, child))
            if result:
                return result
        return None

    return find_child('', sample)


def _clear_tree_widget(item):
    item.setText(1, '')
    for i in range(item.childCount()):
        child = item.child(i)
        _clear_tree_widget(child)


def _set_tree_widget_data(item, records, index,
                          required_size=0):
    if item.childCount() < required_size:
        for i in range(item.childCount(), required_size):
            subitem = QtGui.QTreeWidgetItem(item)
            subitem.setText(0, str(i))
    for i in range(item.childCount()):
        child = item.child(i)
        name = child.text(0)

        field = records[name]
        child.setText(1, str(field.records[index].value))


def _get_data(value, name):
    fields = name.split('.')
    for field in fields:
        if isinstance(value, list):
            value = value[int(field)]
        else:
            value = getattr(value, field)
    return value


class Tplot(QtGui.QMainWindow):
    def __init__(self):
        super(Tplot, self).__init__()

        self.ui = ui_tplot_main_window.Ui_TplotMainWindow()
        self.ui.setupUi(self)

        self.figure = matplotlib.figure.Figure()
        self.canvas = FigureCanvas(self.figure)

        self.canvas.mpl_connect('motion_notify_event', self.handle_mouse)
        self.canvas.mpl_connect('key_press_event', self.handle_key_press)
        self.canvas.mpl_connect('key_release_event', self.handle_key_release)

        # Make QT drawing not be super slow.  See:
        # https://github.com/matplotlib/matplotlib/issues/2559/
        def draw():
            FigureCanvas.draw(self.canvas)
            self.canvas.repaint()

        self.canvas.draw = draw

        self.left_axis = self.figure.add_subplot(111)
        self.left_axis.tplot_name = 'Left'

        self.axes = {
            'Left' : self.left_axis,
            }

        layout = QtGui.QVBoxLayout(self.ui.plotFrame)
        layout.addWidget(self.canvas, 1)

        self.toolbar = backend_qt4agg.NavigationToolbar2QT(self.canvas, self)
        self.addToolBar(self.toolbar)

        self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.canvas.setFocus()

        self.logs = dict()
        self.COLORS = 'rgbcmyk'
        self.next_color = 0
        self.lines = list()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.handle_timeout)

        self.time_start = None
        self.time_end = None
        self.time_current = None

        self.ui.recordCombo.currentIndexChanged.connect(
            self.handle_record_combo)
        self.ui.addPlotButton.clicked.connect(self.handle_add_plot_button)
        self.ui.removeButton.clicked.connect(self.handle_remove_button)
        self.ui.treeWidget.itemExpanded.connect(self.handle_item_expanded)
        self.tree_items = []
        self.ui.treeWidget.header().setResizeMode(
            QtGui.QHeaderView.ResizeToContents)
        self.ui.timeSlider.valueChanged.connect(self.handle_time_slider)
        self._updating_slider = BoolGuard()

        self._sync_dialog = sync_dialog.SyncDialog(self)

        self.ui.fastReverseButton.clicked.connect(
            self.handle_fast_reverse_button)
        self.ui.stepBackButton.clicked.connect(
            self.handle_step_back_button)
        self.ui.playReverseButton.clicked.connect(
            self.handle_play_reverse_button)
        self.ui.stopButton.clicked.connect(self.handle_stop_button)
        self.ui.playButton.clicked.connect(self.handle_play_button)
        self.ui.stepForwardButton.clicked.connect(
            self.handle_step_forward_button)
        self.ui.fastForwardButton.clicked.connect(
            self.handle_fast_forward_button)
        self.ui.actionSynchronize.triggered.connect(self._sync_dialog.show)
        self._sync_dialog.time_changed.connect(self.handle_sync_changed)
        self.ui.action_Quit.triggered.connect(self.close)
        self.ui.action_Open.triggered.connect(self.open_dialog)

        self._course_map_dialog = course_map_dialog.CourseMapDialog(self)
        self._course_map_dialog.time_slider_changed.connect(
            self.update_time)
        self.ui.actionCourse_Map.triggered.connect(
            self._course_map_dialog.show)

    def open_dialog(self):
        directory = ""
        if len(self.logs):
            directory = os.path.dirname(self.logs.values()[-1].filename)
        filename = QtGui.QFileDialog.getOpenFileName(
            self, "Open log file", directory)
        if filename and filename[0]:
            self.open(filename[0])

    def open(self, filename):
        try:
            maybe_log = rc_data.RcData(filename)
        except Exception as e:
            QtGui.QMessageBox.warning(self, 'Could not open log',
                                      'Error: ' + str(e))
            return

        log_name = os.path.basename(filename)
        self.logs[log_name] = maybe_log

        # Add the magic "all logs" item for the first log opened.
        if len(self.logs) == 1:
            self.ui.recordCombo.addItem(ALL_LOGS_STR)

        self.ui.recordCombo.addItem(log_name)
        self._sync_dialog.add_log(maybe_log)
        self._course_map_dialog.add_log(log_name, maybe_log)

        item = QtGui.QTreeWidgetItem()
        item.setText(0, log_name)
        self.ui.treeWidget.addTopLevelItem(item)
        self.tree_items.append(item)
        for name in self.logs[log_name].records.keys():
            sub_item = QtGui.QTreeWidgetItem(item)
            sub_item.setText(0, name)

    def open_sync_dialog(self):
        if self._sync_dialog is None:
            self._sync_dialog = sync_dialog.SyncDialog()

    def handle_record_combo(self):
        record = self.ui.recordCombo.currentText()
        if record == ALL_LOGS_STR:
            # This assumes that all logs have the same fields, which
            # seems likely.
            record = self.logs.keys()[0]

        self.ui.xCombo.clear()
        self.ui.yCombo.clear()

        log = self.logs[record]
        default_x = None
        index = [0, None]

        def add_item(index, element):
            name = element.name
            self.ui.xCombo.addItem(name)
            self.ui.yCombo.addItem(name)

            if (name == rc_data.RELATIVE_TIME_FIELD or
                name == rc_data.RELATIVE_DISTANCE_FIELD):
                index[1] = index[0]

            index[0] += 1

        for item in log.records.itervalues():
            add_item(index, item)
        default_x = index[1]

        if default_x:
            self.ui.xCombo.setCurrentIndex(default_x)

    def handle_add_plot_button(self):
        record = self.ui.recordCombo.currentText()
        xname = self.ui.xCombo.currentText()
        yname = self.ui.yCombo.currentText()

        if record == ALL_LOGS_STR:
            for record_name in self.logs.iterkeys():
                self.add_plot(record_name, xname, yname)
        else:
            self.add_plot(record, xname, yname)

    def add_plot(self, record, xname, yname):
        log = self.logs[record]
        xdata = log.all(xname)
        ydata = log.all(yname)

        line = matplotlib.lines.Line2D(xdata, ydata)
        line.tplot_record_name = record
        line.tplot_has_timestamp = True
        line.tplot_xname = xname
        line.tplot_yname = yname
        label = self.make_label(record, xname, yname)
        line.set_label(label)
        line.set_color(self.COLORS[self.next_color])
        self.next_color = (self.next_color + 1) % len(self.COLORS)
        self.lines.append(line)

        axis = self.get_current_axis()

        axis.add_line(line)
        axis.relim()
        axis.autoscale_view()
        axis.legend(loc=LEGEND_LOC[axis.tplot_name])

        self.ui.plotsCombo.addItem(label, line)
        self.ui.plotsCombo.setCurrentIndex(self.ui.plotsCombo.count() - 1)

        self.canvas.draw()

    def make_label(self, record, xname, yname):
        if xname == 'timestamp':
            return '%s.%s' % (record, yname)
        return '%s %s vs. %s' % (record, yname, xname)

    def get_current_axis(self):
        requested = self.ui.axisCombo.currentText()
        maybe_result = self.axes.get(requested, None)
        if maybe_result:
            return maybe_result

        result = self.left_axis.twinx()
        self.axes[requested] = result
        result.tplot_name = requested

        return result

    def get_all_axes(self):
        return self.axes.values()

    def handle_remove_button(self):
        index = self.ui.plotsCombo.currentIndex()
        if index < 0:
            return
        line = self.ui.plotsCombo.itemData(index)
        if hasattr(line, 'tplot_marker'):
            line.tplot_marker.remove()
        line.remove()
        self.ui.plotsCombo.removeItem(index)

        self.canvas.draw()

    def handle_item_expanded(self):
        self.update_timeline()

    def handle_sync_changed(self):
        for line in self.lines:
            if (line.tplot_xname == rc_data.RELATIVE_TIME_FIELD or
                line.tplot_xname == rc_data.RELATIVE_DISTANCE_FIELD):
                line.set_xdata(
                    self.logs[line.tplot_record_name].all(line.tplot_xname))
            if (line.tplot_yname == rc_data.RELATIVE_TIME_FIELD or
                line.tplot_yname == rc_data.RELATIVE_DISTANCE_FIELD):
                line.set_ydata(
                    self.logs[line.tplot_record_name].all(line.tplot_yname))
        self.update_timeline()
        self.canvas.draw()
        self._course_map_dialog.update_sync()

    def update_timeline(self):
        if self.time_start is not None:
            return

        # Look through all of the logs and find the minimum and
        # maximum timestamp of each.
        for name, log in self.logs.iteritems():
            these_times = log.relative_times()
            if len(these_times) == 0:
                continue
            this_min = min(these_times)
            this_max = max(these_times)

            if self.time_start is None or this_min < self.time_start:
                self.time_start = this_min
            if self.time_end is None or this_max > self.time_end:
                self.time_end = this_max

        self.time_current = self.time_start
        self.update_time(self.time_current, update_slider=False)

    def handle_mouse(self, event):
        if not event.inaxes:
            return
        self.statusBar().showMessage('%f,%f' % (event.xdata, event.ydata))

    def handle_key_press(self, event):
        if event.key not in ['1', '2', '3', '4']:
            return
        index = ord(event.key) - ord('1')
        for key, value in self.axes.iteritems():
            if key == AXES[index]:
                value.set_navigate(True)
            else:
                value.set_navigate(False)

    def handle_key_release(self, event):
        if event.key not in ['1', '2', '3', '4']:
            return
        for key, value in self.axes.iteritems():
            value.set_navigate(True)

    def update_time(self, new_time, update_slider=True):
        new_time = max(self.time_start, min(self.time_end, new_time))
        self.time_current = new_time

        # Update the tree view.
        self.update_tree_view(new_time)

        # Update dots on the plot.
        self.update_plot_dots(new_time)

        # Update the text fields.
        # TODO sammy find some reasonable way to display something here.
        # dt = datetime.datetime.utcfromtimestamp(new_time)
        # self.ui.clockEdit.setText('%04d-%02d-%02d %02d:%02d:%02.3f' % (
        #         dt.year, dt.month, dt.day,
        #         dt.hour, dt.minute, dt.second + dt.microsecond / 1e6))
        self.ui.elapsedEdit.setText('%.3f' % (new_time))

        self._course_map_dialog.update_time(new_time)

        if update_slider:
            with self._updating_slider:
                elapsed = new_time - self.time_start
                total_time = self.time_end - self.time_start
                self.ui.timeSlider.setValue(
                    int(1000 * elapsed / total_time))

    def handle_time_slider(self):
        if self._updating_slider.active():
            return

        if self.time_end is None or self.time_start is None:
            return

        total_time = self.time_end - self.time_start
        current = self.ui.timeSlider.value() / 1000.0
        self.update_time(self.time_start + current * total_time,
                         update_slider=False)

    def update_tree_view(self, time):
        for item in self.tree_items:
            name = item.text(0)
            log = self.logs[name]
            this_time_index = log.relative_index(time)
            if this_time_index is None:
                _clear_tree_widget(item)
            else:
                _set_tree_widget_data(item, log.records, this_time_index)

    def update_plot_dots(self, new_time):
        updated = False
        for axis in self.get_all_axes():
            for line in axis.lines:
                if not hasattr(line, 'tplot_record_name'):
                    continue
                if not hasattr(line, 'tplot_has_timestamp'):
                    continue

                log = self.logs[line.tplot_record_name]
                this_time_index = log.relative_index(new_time)
                if this_time_index is None:
                    continue

                if not hasattr(line, 'tplot_marker'):
                    line.tplot_marker = matplotlib.lines.Line2D([], [])
                    line.tplot_marker.set_marker('o')
                    line.tplot_marker.set_color(line._color)
                    self.left_axis.add_line(line.tplot_marker)

                updated = True
                xdata = log.value_at(line.tplot_xname, this_time_index)
                ydata = log.value_at(line.tplot_yname, this_time_index)
                line.tplot_marker.set_data(xdata, ydata)

        if updated:
            self.canvas.draw()


    def handle_fast_reverse_button(self):
        self.play_start(-self.ui.fastReverseSpin.value())

    def handle_step_back_button(self):
        self.play_stop()
        self.update_time(self.time_current - self.ui.stepBackSpin.value())

    def handle_play_reverse_button(self):
        self.play_start(-1.0)

    def handle_stop_button(self):
        self.play_stop()

    def handle_play_button(self):
        self.play_start(1.0)

    def handle_step_forward_button(self):
        self.play_stop()
        self.update_time(self.time_current + self.ui.stepForwardSpin.value())

    def handle_fast_forward_button(self):
        self.play_start(self.ui.fastForwardSpin.value())

    def play_stop(self):
        self.speed = None
        self.last_time = None
        self.timer.stop()

    def play_start(self, speed):
        self.speed = speed
        self.last_time = time.time()
        self.timer.start(100)

    def handle_timeout(self):
        if self.time_current is None:
            self.update_timeline()
        assert self.last_time is not None
        this_time = time.time()
        delta_t = this_time - self.last_time
        self.last_time = this_time

        self.update_time(self.time_current + delta_t * self.speed)


def main():
    parser = argparse.ArgumentParser(description="Plot data from RaceCapture")
    parser.add_argument("logfiles", nargs="*", help="Logfiles to add to plot")
    parser.add_argument("--sync", nargs=2, metavar=('name', 'value'),
                        help="Channel name and value to use for "
                        "synchronization trigger")
    args = parser.parse_args(sys.argv[1:])

    app = QtGui.QApplication(sys.argv)
    app.setApplicationName('tplot')

    tplot = Tplot()
    tplot.show()

    for filename in args.logfiles:
        tplot.open(filename)

    if args.sync is not None:
        tplot._sync_dialog.apply_trigger(args.sync[0], float(args.sync[1]))

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
