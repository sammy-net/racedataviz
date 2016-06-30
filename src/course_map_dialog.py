# Copyright 2016 Sam Creasey, sammy@sammy.net.  All rights reserved.
#
# TODO sammy find the right GPL3 preamble for this

import matplotlib

matplotlib.use('Qt4Agg')
matplotlib.rcParams['backend.qt4'] = 'PySide'

from matplotlib.backends import backend_qt4agg
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

from PySide import QtCore, QtGui

import course_gdal
import ui_course_map_dialog

class _LogMapData(object):
    def __init__(self, log_name, log, color):
        self.log = log
        self.utm_data = None
        self.line = matplotlib.lines.Line2D([], [])
        self.line.set_label(log_name)
        self.line.set_color(color)
        self.marker = matplotlib.lines.Line2D([], [])
        self.marker.set_marker('o')
        self.marker.set_color(self.line._color)
        self.bounds = ((0, 0), (0, 0))
        self.update_line_data()

    def update_line_data(self):
        self.utm_data = self.log.get_utm_data()
        xdata = [utm[1] for utm in self.utm_data if utm[0] >= 0.]
        ydata = [utm[2] for utm in self.utm_data if utm[0] >= 0.]
        self.line.set_xdata(xdata)
        self.line.set_ydata(ydata)
        self.bounds = ((min(xdata), min(ydata)), (max(xdata), max(ydata)))

    def update_marker(self, new_time):
        time_index = self.log.relative_index(new_time)
        xdata = self.utm_data[time_index][1]
        ydata = self.utm_data[time_index][2]
        self.marker.set_data(xdata, ydata)


class CourseMapDialog(QtGui.QDialog):
    """Implements a dialog box to display course maps."""

    time_slider_changed = QtCore.Signal(float)

    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        self._ui = ui_course_map_dialog.Ui_Dialog()
        self._ui.setupUi(self)

        params = matplotlib.figure.SubplotParams(0, 0, 1, 1, 0, 0)
        self._figure = matplotlib.figure.Figure(subplotpars=params)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.mpl_connect('motion_notify_event', self._handle_mouse)
        self._canvas.mpl_connect('scroll_event', self._handle_scroll)
        self._canvas.mpl_connect('button_release_event',
                                 self._handle_mouse_release)
        self._mouse_start = None

        # Make QT drawing not be super slow.  See:
        # https://github.com/matplotlib/matplotlib/issues/2559/
        def draw():
            FigureCanvas.draw(self._canvas)
            self._canvas.repaint()

        self._canvas.draw = draw
        self._plot = self._figure.add_subplot(111)

        self._gdal_source = course_gdal.GdalSource()
        self._gdal = None

        layout = QtGui.QVBoxLayout(self._ui.mapFrame)
        layout.addWidget(self._canvas, 1)

        self._log_data = dict()

        # TODO sammy make COLORS a project wide config
        self._COLORS = 'rgbcmyk'
        self._next_color = 0
        self._bounds = ((0, 0), (0, 0))
        self._time_current = 0
        self._total_time = 0
        self._ui.timeSlider.valueChanged.connect(self._handle_time_slider)

    def add_log(self, log_name, log):
        log_data = _LogMapData(log_name, log, self._COLORS[self._next_color])
        self._log_data[log_name] = log_data
        self._next_color = (self._next_color + 1) % len(self._COLORS)

        if self._gdal is None:
            self._gdal = self._gdal_source.get_gdal(
                log_data.utm_data[0][1], log_data.utm_data[0][2])
            if self._gdal is not None:
                self._plot.imshow(self._gdal.image, extent=self._gdal.extent)

        self._plot.add_line(log_data.line)
        self._plot.add_line(log_data.marker)
        self._plot.legend(loc=2)
        self._update_scale()

    def update_sync(self):
        for log_data in self._log_data.itervalues():
            log_data.update_line_data()
            log_data.update_marker(self._time_current)

        self._update_scale()

    def _update_scale(self):
        self._plot.relim()
        minx = 1e10
        miny = 1e10
        maxx = -1e10
        maxy = -1e10
        max_time = 0

        for log_data in self._log_data.itervalues():
            bounds = log_data.bounds
            minx = min(minx, bounds[0][0])
            miny = min(miny, bounds[0][1])
            maxx = max(maxx, bounds[1][0])
            maxy = max(maxy, bounds[1][1])
            max_time = max(max_time, log_data.utm_data[-1][0])
        self._total_time = max_time

        x_size = maxx - minx
        y_size = maxy - miny
        xy_delta = x_size - y_size
        if xy_delta > 0:
            miny -= xy_delta / 2
            maxy += xy_delta / 2
        else:
            minx += xy_delta / 2
            maxx -= xy_delta / 2

        self._bounds = ((minx, miny), (maxx, maxy))
        self._plot.set_xlim(left=minx, right=maxx)
        self._plot.set_ylim(bottom=miny, top=maxy)
        self._canvas.draw()

    def _handle_mouse(self, event):
        if not event.inaxes or event.button != 1:
            return

        if self._mouse_start is None:
            self._mouse_start = event
            return

        # Handle a pan event.  What we want is for the point (data)
        # where the mouse was originally clicked to stay under the
        # pointer.
        (width, height) = self._canvas.get_width_height()
        px_x = (self._bounds[1][0] - self._bounds[0][0]) / width
        px_y = (self._bounds[1][1] - self._bounds[0][1]) / height
        x_change = (self._mouse_start.x - event.x) * px_x
        y_change = (self._mouse_start.y - event.y) * px_y
        self._plot.set_xlim(left=self._bounds[0][0] + x_change,
                            right=self._bounds[1][0] + x_change)
        self._plot.set_ylim(bottom=self._bounds[0][1] + y_change,
                            top=self._bounds[1][1] + y_change)
        self._canvas.draw()

    def _update_bounds(self):
        xlim = self._plot.get_xlim()
        ylim = self._plot.get_ylim()
        self._bounds = ((xlim[0], ylim[0]), (xlim[1], ylim[1]))

    def _handle_mouse_release(self, event):
        if event.button != 1:
            return
        self._mouse_start = None
        self._update_bounds()

    def _handle_scroll(self, event):
        # Determine the relative offset of the clicked position to the
        # center of the frame so that we can keep the data under the
        # cursor.
        (width, height) = self._canvas.get_width_height()
        x_off = float(width - event.x) / width
        y_off = float(height - event.y) / height
        x_scale = (self._bounds[1][0] - self._bounds[0][0]) * (event.step / 10.)
        y_scale = (self._bounds[1][1] - self._bounds[0][1]) * (event.step / 10.)

        # Check if we've tried to zoom to far and would invert our axes
        new_xlim = (self._bounds[0][0] + (x_scale * (1. - x_off)),
                    self._bounds[1][0] - (x_scale * x_off))
        new_ylim = (self._bounds[0][1] + (y_scale * (1. - y_off)),
                    self._bounds[1][1] - (y_scale * y_off))
        if (new_xlim[1] <= new_xlim[0]) or (new_ylim[1] <= new_ylim[0]):
            return

        self._plot.set_xlim(left=new_xlim[0], right=new_xlim[1])
        self._plot.set_ylim(bottom=new_ylim[0], top=new_ylim[1])
        self._update_bounds()
        self._canvas.draw()

    def update_time(self, new_time, update_slider=True):
        # Bound the time to our useful range.
        new_time = max(0, min(new_time, self._total_time))
        self._time_current = new_time
        for log_data in self._log_data.itervalues():
            log_data.update_marker(new_time)
        self._canvas.draw()
        self._ui.elapsedTime.setText(str(new_time))

        # if update_slider:
        #     self._ui.timeSlider.setValue(1000 * (new_time / self._total_time))

    def _handle_time_slider(self):
        if self._total_time == 0:
            return
        current = self._ui.timeSlider.value() / 1000.
        self.update_time(current * self._total_time, update_slider=False)
        self.time_slider_changed.emit(self._time_current)


# TODO sammy add removing a log
