import sys
import os
import rospy
import rospkg

from qt_gui.plugin import Plugin
from python_qt_binding import loadUi
from python_qt_binding.QtWidgets import QWidget, QTreeWidgetItem, QFileDialog, QHBoxLayout

from python_qt_binding.QtCore import Qt, QTimer, Signal, Slot, QRegExp, pyqtSignal, QSize

from python_qt_binding.QtGui import QIcon, QFont, QFontMetrics, QPalette, QBrush
from python_qt_binding.QtGui import QIcon, QFont, QFontMetrics, QTextDocument, QTextOption, QPen, QPainter, QColor, QTextCursor

import syntax

from dyn_tune.msg import Experiment
from dyn_tune.srv import *

from rqt_bag.bag_widget import BagWidget
from .func_widget import StyledLabel

import json

import argparse

from rqt_bag.player import Player
from rosgraph_msgs.msg import Log

from dyn_tune import function

python_pkg_path = os.path.join(rospkg.RosPack().get_path('dyn_tune'), 'src', 'dyn_tune')

if python_pkg_path not in sys.path:
    sys.path.insert(0, python_pkg_path)



class MyPlayer(Player):
    def create_publisher(self, topic, msg, prefix = "/GROUND_TRUTH"):
        try:
            try:
                self._publishers[topic] = rospy.Publisher(prefix + topic, type(msg), queue_size=100)
            except TypeError:
                self._publishers[topic] = rospy.Publisher(prefix + topic, type(msg))
            return True
        except Exception as ex:
            # Any errors, stop listening/publishing to this topic
            rospy.logerr('Error creating publisher on topic %s for type %s. \nError text: %s' % (prefix + topic, str(type(msg)), str(ex)))
            if topic != CLOCK_TOPIC:
                self.stop_publishing(topic)
            return False

class MyBagWidget(BagWidget):
    def __init__(self, context, publish_clock = ""):
        print type(context)
        args = self._parse_args(context.argv())
        super(MyBagWidget, self).__init__(context, args.clock)

        self._timeline._player = MyPlayer(self._timeline)
        self.config_timeline_frame()
        self.graphics_view.setBackgroundBrush(QBrush(QColor(127,127,127)))

        slabel = StyledLabel(self)      
        layout = self.horizontalLayout
        self.horizontalLayout.takeAt(0)
        last = self.horizontalLayout.count() - 1
        self.horizontalLayout.takeAt(last)
        self.horizontalLayout.insertWidget(-1, slabel, 1)

        self.filename = ''


    def sizeHint(self):
        TOPIC_HEIGHT = 27
        PADDING = 60 + 75
        height = TOPIC_HEIGHT * len(self._timeline._get_topics()) + PADDING
        return QSize(0, height)

    def _parse_args(self, argv):
        parser = argparse.ArgumentParser(prog='rqt_bag', add_help=False)
        MyBagWidget.add_arguments(parser)
        return parser.parse_args(argv)

    @staticmethod
    def _isfile(parser, arg):
        if os.path.isfile(arg):
            return arg
        else:
            parser.error("Bag file %s does not exist" % ( arg ))

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group('Options for rqt_bag plugin')
        group.add_argument('--clock', action='store_true', help='publish the clock time')
        group.add_argument('bagfiles', type=lambda x: MyBagWidget._isfile(parser, x),
                           nargs='*', default=[], help='Bagfiles to load')

    def _handle_load_clicked(self):
        filename = QFileDialog.getOpenFileName(self, self.tr('Load from File'), '.', self.tr('Bag files {.bag} (*.bag)'))
        
        if filename[0] != '':
            self.filename = filename[0]
            self.load_bag(filename[0])
            self._timeline.set_publishing_state(True)


    def config_timeline_frame(_self):
        self = _self._timeline._timeline_frame

        # Background Rendering
        self._bag_end_color = QColor(76,76,76) # QColor(0, 0, 0, 25)  # color of background of timeline before first message and after last
        self._history_background_color_alternate = QColor(179, 179, 179, 90)
        self._history_background_color =  QColor(204, 204, 204, 102)

        # Timeline Division Rendering
        # Possible time intervals used between divisions
        # 1ms, 5ms, 10ms, 50ms, 100ms, 500ms
        # 1s, 5s, 15s, 30s
        # 1m, 2m, 5m, 10m, 15m, 30m
        # 1h, 2h, 3h, 6h, 12h
        # 1d, 7d
        self._sec_divisions = [0.001, 0.005, 0.01, 0.05, 0.1, 0.5,
                               1, 5, 15, 30,
                               1 * 60, 2 * 60, 5 * 60, 10 * 60, 15 * 60, 30 * 60,
                               1 * 60 * 60, 2 * 60 * 60, 3 * 60 * 60, 6 * 60 * 60, 12 * 60 * 60,
                               1 * 60 * 60 * 24, 7 * 60 * 60 * 24]
        self._minor_spacing = 15
        self._major_spacing = 50
        self._major_divisions_label_indent = 3  # padding in px between line and label
        self._major_division_pen = QPen(QBrush(QColor(76,76,76)), 0, Qt.DashLine)
        self._minor_division_pen = QPen(QBrush(QColor(76, 76, 76, 75)), 0, Qt.DashLine)
        self._minor_division_tick_pen = QPen(QBrush(QColor(128, 128, 128, 128)), 0)

        # Topic Rendering
        self.topics = []
        self._topics_by_datatype = {}
        self._topic_font_height = None
        self._topic_name_sizes = None
        self._topic_name_spacing = 30  # minimum pixels between end of topic name and start of history
        self._topic_font_size = 11
        self._topic_font = QFont("courier new")
        self._topic_font.setPointSize(self._topic_font_size)
        self._topic_font.setBold(False)
        self._topic_vertical_padding = 10
        self._topic_name_max_percent = 25.0  # percentage of the horiz space that can be used for topic display

        # Time Rendering
        self._time_tick_height = 5
        self._time_font_height = None
        self._time_font_size = 10.0
        self._time_font = QFont("courier new")
        self._time_font.setPointSize(self._time_font_size)
        self._time_font.setBold(False)

        # Defaults
        self._default_brush = QBrush(Qt.black, Qt.SolidPattern)
        self._default_pen = QPen(QColor(240, 240, 240))
        self._default_datatype_color = QColor(255, 180, 125, 75) # QColor(0, 0, 102, 204)
        self._datatype_colors = {
            'sensor_msgs/CameraInfo': QColor(0, 0, 77, 204),
            'sensor_msgs/Image': QColor(0, 77, 77, 204),
            'sensor_msgs/LaserScan': QColor(153, 0, 0, 204),
            'pr2_msgs/LaserScannerSignal': QColor(153, 0, 0, 204),
            'pr2_mechanism_msgs/MechanismState': QColor(0, 153, 0, 204),
            'tf/tfMessage': QColor(0, 153, 0, 204),
        }
        self._default_msg_combine_px = 1.0  # minimum number of pixels allowed between two bag messages before they are combined
        self._active_message_line_width = 3

        # Selected Region Rendering
        self._selected_region_color = QColor(0, 179, 0, 42)
        self._selected_region_outline_top_color =  QColor(0.0, 77, 0.0, 102)
        self._selected_region_outline_ends_color = QColor(0.0, 77, 0.0, 204)
        self._selected_left = None
        self._selected_right = None
        self._selection_handle_width = 3.0

        # Playhead Rendering
        self._playhead = None  # timestamp of the playhead
        self._paused = False
        self._playhead_pointer_size = (6, 6)
        self._playhead_line_width = 1
        self._playhead_color = QColor(255, 255, 255, 191)

        # Zoom
        self._zoom_sensitivity = 0.005
        self._min_zoom_speed = 0.5
        self._max_zoom_speed = 2.0
        self._min_zoom = 0.0001  # max zoom out (in px/s)
        self._max_zoom = 50000.0  # max zoom in  (in px/s)

        # Timeline boundries
        self._start_stamp = None  # earliest of all stamps
        self._end_stamp = None  # latest of all stamps
        self._stamp_left = None  # earliest currently visible timestamp on the timeline
        self._stamp_right = None  # latest currently visible timestamp on the timeline
        self._history_top = 30
        self._history_left = 0
        self._history_width = 0
        self._history_bottom = 0
        self._history_bounds = {}
        self._margin_left = 30
        self._margin_right = 20
        self._margin_bottom = 20


class DynTuneUI(Plugin):

    loggerUpdate = Signal(str, name='loggerUpdate')

    def __init__(self, context):
        super(DynTuneUI, self).__init__(context)
        
        # Give QObjects reasonable names
        self.setObjectName('dyn_tune_plugin')

        # Process standalone plugin command-line arguments
        from argparse import ArgumentParser
        parser = ArgumentParser()
        # Add argument(s) to the parser.
        parser.add_argument("-q", "--quiet", action="store_true",
                            dest="quiet",
                            help="Put plugin in silent mode")
        args, unknowns = parser.parse_known_args(context.argv())
        if not args.quiet:
            print 'arguments: ', args
            print 'unknowns: ', unknowns

        # Create QWidget
        self._widget = QWidget()
        self._bag_widget = MyBagWidget(context)

        # Get path to UI file which should be in the "resource" folder of this package
        ui_file = os.path.join(rospkg.RosPack().get_path('rqt_dyn_tune'), 'resource', 'DynTune.ui')
        # Extend the widget with all attributes and children from UI file
        loadUi(ui_file, self._widget)
        # Give QObjects reasonable names
        self._widget.setObjectName('DynTuneUI')

        self._widget.vLayout.insertWidget(1, self._bag_widget, 0)
        self._widget.vLayout.setStretchFactor(self._widget.hLayout, 1)
        self._widget.vLayout.setStretchFactor(self._widget._widget_func, 1)

        # Show _widget.windowTitle on left-top of each plugin (when 
        # it's set in _widget). This is useful when you open multiple 
        # plugins at once. Also if you open multiple instances of your 
        # plugin at once, these lines add number to make it easy to 
        # tell from pane to pane.
        # if context.serial_number() > 1:
        #     self._widget.setWindowTitle(self._widget.windowTitle() + (' (%d)' % context.serial_number()))
        # Add widget to the user interface
        context.add_widget(self._widget)
        
        index = self._widget._widget_values._column_names.index("checkbox")
        self._widget._widget_values.topics_tree_widget.hideColumn(index)
        self._widget._widget_values.topics_tree_widget.model().setHeaderData(0, Qt.Horizontal,"value");

        self._widget._widget_func.start()
        self._widget._widget_values.start()
        self._widget._widget_param.start()

        rospy.Subscriber("/rosout", Log, self.logger_update)
        self.loggerUpdate.connect(self.logger_update_slot)


        css_file = os.path.join(rospkg.RosPack().get_path('rqt_dyn_tune'), 'src', 'rqt_dyn_tune', 'css', 'selector.css')
        with open(css_file, "r") as fh:
            csstext = fh.read()
            self._widget._widget_func.setStyleSheet(csstext)
            self._widget._widget_values.setStyleSheet(csstext)
            self._widget._widget_param.setStyleSheet(csstext)


        css_file = os.path.join(rospkg.RosPack().get_path('rqt_dyn_tune'), 'src', 'rqt_dyn_tune', 'css', 'bag.css')
        with open(css_file, "r") as fh:
            csstext = fh.read()
            self._bag_widget.setStyleSheet(csstext)


        css_file = os.path.join(rospkg.RosPack().get_path('rqt_dyn_tune'), 'src', 'rqt_dyn_tune', 'css', 'plugin.css')
        with open(css_file, "r") as fh:
            csstext = fh.read()
            self._widget.setStyleSheet(csstext)



        self._widget.tune_btn.clicked.connect(self.tune_clicked)

        @Slot()
        def topics_refreshed():
            topic_widget = self._widget._widget_values
            values = topic_widget.get_selected_values()
            self._widget._widget_func.topics_refreshed(values)
            

        self._widget._widget_values.topicsRefreshed.connect(topics_refreshed)

    
    def logger_update(self, msg):
        if msg.name == "/dyn_tune_backbone":
            self.loggerUpdate.emit(msg.msg)

    @Slot(str)
    def logger_update_slot(self, msg):
        self._widget.logger.append(msg)

    def tune_clicked(self):
        srv = self.creat_optimize_srv()
        print srv
        self.optimize = rospy.ServiceProxy('/optimize', Optimize)
        result = self.optimize(srv)
        print result
        pass

    
    def create_experiment_msg(self, name = "experiment_0"):
        exp = Experiment()
        params_dict = self._widget._widget_param.get_selected()
        exp.parameters = json.dumps(params_dict)
        exp.objective = self._widget._widget_func.create_function_msg()

        return exp

    def creat_optimize_srv(self):
        opt = OptimizeRequest()

        opt.observation_values = self._widget._widget_values.get_selected()
        opt.start_signals =  "{}"
        opt.end_signals =  "{}"
        opt.src_bag = self._bag_widget.filename
        opt.dst_bag = "_simulation.bag"

        opt.src_topic = "/.*"
        opt.dst_topic = ""

        exp = self.create_experiment_msg()
        opt.experiments.append(exp)

        return opt


        # opt.src.


    def shutdown_plugin(self):
        # TODO unregister all publishers here
        pass

    def save_settings(self, plugin_settings, instance_settings):
        # TODO save intrinsic configuration, usually using:
        # instance_settings.set_value(k, v)
        pass

    def restore_settings(self, plugin_settings, instance_settings):
        # TODO restore intrinsic configuration, usually using:
        # v = instance_settings.value(k)
        pass

        # def trigger_configuration(self):
        # Comment in to signal that the plugin has a way to configure
        # This will enable a setting button (gear icon) in each dock widget title bar
        # Usually used to open a modal configuration dialog
