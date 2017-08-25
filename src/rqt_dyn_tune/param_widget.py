#!/usr/bin/env python

# Copyright (c) 2011, Dorian Scholz, TU Darmstadt
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above
#     copyright notice, this list of conditions and the following
#     disclaimer in the documentation and/or other materials provided
#     with the distribution.
#   * Neither the name of the TU Darmstadt nor the names of its
#     contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os

from python_qt_binding import loadUi
from python_qt_binding.QtCore import Qt, QTimer, Signal, Slot, QRegExp, pyqtSignal
from python_qt_binding.QtGui import QIcon, QRegExpValidator
from python_qt_binding.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QStyledItemDelegate, QPushButton, QLineEdit
from python_qt_binding.QtWidgets import QHeaderView, QMenu, QTreeWidgetItem, QWidget, QSlider, QAbstractItemView


import roslib
import rospkg
import rospy
from rospy.exceptions import ROSException

from .topic_info import TopicInfo

import dynamic_reconfigure
import dynamic_reconfigure.client


global CHECK_COLUMN
CHECK_COLUMN = 5


class EditorDelegate(QStyledItemDelegate):

    def __init__(self, parent = None):
        super(QStyledItemDelegate, self).__init__(parent)
        print "constructor"

    _column_names = ['topic', 'type', 'min', 'value', 'max', 'checkbox']

    def createEditor(self, parent, option, index):

        print option

        print index.column()
        indices = [2, 3, 4]
        if index.column() not in indices:
            return None



        print "create_edit"

        if index.column() == 3:
                
            widget = QWidget(parent)

            slider = QSlider(Qt.Horizontal, widget)


            text_edit = QLineEdit(widget)
            text_edit.setFocus()
            text_edit.selectAll()

            text_edit.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

            hbox = QVBoxLayout()

            # slider.setMinimumWidth(400)

            # hbox.setMargin(0);
            hbox.setContentsMargins(2,1,2,1);

            # min_label = QLabel("min")
            # max_label = QLabel("max")
            # vbox.addWidget(min_label)
            
            
            hbox.addWidget(slider)
            hbox.addWidget(text_edit)
            # vbox.addWidget(max_label)

            
            widget.setLayout(hbox)
            # widget.setMinimumWidth(400)

            slider.setMinimumHeight(32)
            text_edit.setMinimumHeight(36)

            widget.setMinimumHeight(80)
            widget.setAutoFillBackground(True)
            widget.setStyleSheet(".QWidget { background:rgb(200, 200, 200); margin:0px; border:1px solid rgb(170, 170, 170); }")
            # parent.setMinimumWidth(300)

            row = index.row()
            imin = index.sibling(row, self._column_names.index("min"))
            imax = index.sibling(row, self._column_names.index("max"))

            

            smin = index.model().data(imin, Qt.EditRole)
            smax = index.model().data(imax, Qt.EditRole)         

            fmin = 0
            fmax = 100

            def isFloat(s):
                try: 
                    float(s)
                    return True
                except:
                    return False

            if isFloat(smin):
                fmin = float(smin)

            if isFloat(smax):
                fmax = float(smax)

            print fmin, fmax

            slider.setMinimum(int(fmin * 100))
            slider.setMaximum(int(fmax * 100))

            slider.setMouseTracking(True)

            @Slot(int)
            def sliderValueChanged(value):
                text_edit.setText(str(float(value)/100.))
                print "slider value changed to %d" % value

                text_edit.setFocus()
                text_edit.selectAll()
                pass

            @Slot()
            def sliderDown():
                print "slider pressed"



            @Slot()
            def sliderUp():
                print "slider released"

            @Slot()
            def editingFinished():
                text = text_edit.text()

                value = float(text)
                nvalue = value
                nvalue = min(nvalue, fmax)
                nvalue = max(nvalue, fmin)
                # print "nvalue is", nvalue

                if value != nvalue:
                    text_edit.setText(str(nvalue))                

                svalue = int(nvalue*100)

                print "text changed to %s" % text
                print "nvalue is", nvalue
                print "svalue is %d" % svalue

                slider.blockSignals(True)
                slider.setSliderPosition(svalue)
                slider.blockSignals(False)
                pass



            @Slot(str)
            def lineEditTextChanged(text):
                # text_edit.setText(str(value))                

                # slider.setSliderDown(True)

                # slider.sliderPressed.emit()
                print "setSliderDown"

                if not isFloat(text):
                    return

                

                value = float(text)
                nvalue = value
                # nvalue = min(nvalue, fmax)
                # nvalue = max(nvalue, fmin)
                # print "nvalue is", nvalue

                if value != nvalue:
                    text_edit.setText(str(nvalue))

                svalue = int(nvalue*100)

                print "text changed to %s" % text
                print "nvalue is", nvalue
                print "svalue is %d" % svalue

                slider.blockSignals(True)
                slider.setSliderPosition(svalue)
                slider.blockSignals(False)

                
                pass

            slider.valueChanged.connect(sliderValueChanged)

            slider.sliderPressed.connect(sliderDown)

            slider.sliderReleased.connect(sliderUp)

            text_edit.textChanged.connect(lineEditTextChanged)
            text_edit.editingFinished.connect(editingFinished)


            

            text_edit.selectAll()
            text_edit.setFocus()

            rx = QRegExp("^-?([1-9]\d*|0)(\.\d*)?$")
            v = QRegExpValidator(rx)
            text_edit.setValidator(v)

            widget.setFocusProxy(text_edit)
            
            edt = widget
        else:
            edt = QLineEdit(parent)

            if index.column() == 2:
                edt.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            elif index.column() == 4:
                edt.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            rx = QRegExp("^-?([1-9]\d*|0)(\.\d*)?$")
            v = QRegExpValidator(rx);
            edt.setValidator(v)
        # edt.setInputMask("#00000000")
        return edt    

    def setModelData(self, editor, model, index):
        if index.column() == self._column_names.index("value"):
            text_edit = editor.findChild(QLineEdit)        
            value = text_edit.text()
        else:
            value = editor.text()        

        model.setData(index, value, Qt.EditRole)
        model.setData(index, value, Qt.UserRole)

        row = index.row()
        imin = index.sibling(row, self._column_names.index("min"))
        imax = index.sibling(row, self._column_names.index("max"))
        ival = index.sibling(row, self._column_names.index("value"))

        vmin = imin.data(Qt.EditRole)
        vmax = imax.data(Qt.EditRole)
        val = ival.data(Qt.EditRole)

        def tryFloat(s):
            try: 
                return float(s)
            except:
                return None

        vmin = tryFloat(vmin)
        vmax = tryFloat(vmax)
        val = tryFloat(val)

        # vmin = int(float(vmin))
        # vmax = int(float(vmax))
        # val = int(float(val))

        print vmin, val, vmax

        if index.column() == self._column_names.index("min"):
            if vmin != None and (vmax==None or vmax<vmin):
                model.setData(imax, str(vmin))
                model.setData(imax, str(vmin), Qt.UserRole)
            
            if vmin != None and (val==None or val<vmin):
                model.setData(ival, str(vmin))
                model.setData(ival, str(vmin), Qt.UserRole)

        if index.column() == self._column_names.index("max"):
            if vmax != None and (vmin==None or vmax<vmin):
                model.setData(imin, str(vmax))
                model.setData(imin, str(vmax), Qt.UserRole)

            if vmax != None and (val==None or vmax<val):
                model.setData(ival, str(vmax))
                model.setData(ival, str(vmax), Qt.UserRole)

        if index.column() == self._column_names.index("value") and val != None:
            if vmax == None:
                model.setData(imax, str(val))
                model.setData(imax, str(val), Qt.UserRole)
            if vmin == None:
                model.setData(imin, str(val))
                model.setData(imin, str(val), Qt.UserRole)



        print "data"

    def setEditorData(self, editor, index):

        value = index.model().data(index, Qt.EditRole)
        # value = index.data(Qt.EditRole)
        print "edit_data ", value
        # editor.setText(value)

        if index.column() == 3:
            slider = editor.findChild(QSlider)        
            slider.setSliderDown(True)
            # slider.grabMouse()

            text_edit = editor.findChild(QLineEdit)        
            text_edit.setText(value)
            text_edit.selectAll()
            text_edit.setFocus()
            print("Focus")
        else:
            editor.setText(value)

    
        

class ParamWidget(QWidget):
    """
    main class inherits from the ui window class.

    You can specify the topics that the topic pane.

    ParamWidget.start must be called in order to update topic pane.
    """

    SELECT_BY_NAME = 0
    SELECT_BY_MSGTYPE = 1

    # _column_names = ['topic', 'type', 'bandwidth', 'rate', 'value', 'checkbox']
    _column_names = ['topic', 'type', 'min', 'value', 'max', 'checkbox']

    selectionChanged = pyqtSignal(dict, name='selectionChanged')


    def keyPressEvent(self, event):
        # super(QWidget, self).keyPressEvent(event)
        event.ignore()
        print "key pressed"
        return



        current = self.topics_tree_widget.currentItem()
        column = self.topics_tree_widget.currentColumn()

        if event.key() == Qt.Key_Right:
            self.topics_tree_widget.setCurrentItem(current, column+1)
            print "right is pressed"
            event.ignore()
            return

        if event.key() == Qt.Key_Left:
            self.topics_tree_widget.setCurrentItem(current, column-1)
            print "left is pressed"
            return


        # event.accept()

    def keyReleaseEvent(self, event):
        print "key released"
        event.ignore()
        return 
        current = self.topics_tree_widget.currentItem()
        column = self.topics_tree_widget.currentColumn()

        

        # print "current is ", current, " at ", column
        # self.topics_tree_widget.editItem(current, column)

        print event.key()
        event.accept()


        # if event.key() == Qt.Key_Escape:
        #     self.close()

    def __init__(self, plugin=None, selected_topics=None, select_topic_type=SELECT_BY_NAME):
        """
        @type selected_topics: list of tuples.
        @param selected_topics: [($NAME_TOPIC$, $TYPE_TOPIC$), ...]
        @type select_topic_type: int
        @param select_topic_type: Can specify either the name of topics or by
                                  the type of topic, to filter the topics to
                                  show. If 'select_topic_type' argument is
                                  None, this arg shouldn't be meaningful.
        """
        super(ParamWidget, self).__init__()

        self._select_topic_type = select_topic_type

        self.setFocusPolicy(Qt.StrongFocus)



        rp = rospkg.RosPack()
        ui_file = os.path.join(rp.get_path('rqt_dyn_tune'), 'resource', 'ParamWidget.ui')
        loadUi(ui_file, self)
        self._plugin = plugin
        self.topics_tree_widget.sortByColumn(0, Qt.AscendingOrder)
        header = self.topics_tree_widget.header()
        try:
            setSectionResizeMode = header.setSectionResizeMode  # Qt5
        except AttributeError:
            setSectionResizeMode = header.setResizeMode  # Qt4
        setSectionResizeMode(QHeaderView.ResizeToContents)
        header.customContextMenuRequested.connect(self.handle_header_view_customContextMenuRequested)
        header.setContextMenuPolicy(Qt.CustomContextMenu)

        # for i in range(len(self._column_names)):
        #     setSectionResizeMode(i, QHeaderView.Stretch)

        header.setStretchLastSection(False)
        setSectionResizeMode(0, QHeaderView.Stretch)
        setSectionResizeMode(self._column_names.index("value"), QHeaderView.Stretch)
        setSectionResizeMode(self._column_names.index("checkbox"), QHeaderView.Fixed)

        # Whether to get all topics or only the topics that are set in advance.
        # Can be also set by the setter method "set_selected_topics".
        self._selected_topics = selected_topics

        self._selected_items = []

        self._current_topic_list = []
        self._topics = {}
        self._tree_items = {}
        self._column_index = {}
        for column_name in self._column_names:
            self._column_index[column_name] = len(self._column_index)

        self.topics_tree_widget.itemExpanded.connect(self.expanded)
        self.topics_tree_widget.itemCollapsed.connect(self.collapsed)

        self.topics_tree_widget.itemChanged.connect(self.itemChanged)

        self.topics_tree_widget.setAlternatingRowColors(True)

        delegate = EditorDelegate()
        self.topics_tree_widget.setItemDelegate(delegate)
        # self.topics_tree_widget.setItemDelegateForColumn(1, delegate)

        # print(self.topics_tree_widget.itemDelegate())
        # print(self.topics_tree_widget.itemDelegate(3))
        # print(self.topics_tree_widget.itemDelegateForColumn(1))

        
        self.topics_tree_widget.setEditTriggers(QAbstractItemView.AnyKeyPressed | QAbstractItemView.DoubleClicked  )

        
        @Slot(QTreeWidgetItem, int)
        def currentChanged(current, column):
            # column = self.topics_tree_widget.currentColumn()
            print "current is ", current, " at ", column
            # print "previous is ", previous,

            # self.topics_tree_widget.editItem(current, column)

        # self.topics_tree_widget.currentItemChanged.connect(currentChanged)
        # self.topics_tree_widget.itemActivated.connect(currentChanged)

        hitem = self.topics_tree_widget.headerItem()
        hitem.setTextAlignment(self._column_names.index("min"), Qt.AlignRight | Qt.AlignVCenter)
        hitem.setTextAlignment(self._column_names.index("max"), Qt.AlignLeft | Qt.AlignVCenter)
        hitem.setTextAlignment(self._column_names.index("value"), Qt.AlignHCenter | Qt.AlignVCenter)
        hitem.setTextAlignment(self._column_names.index("type"), Qt.AlignHCenter | Qt.AlignVCenter)



        # self.refresh_topics()

        # init and start update timer
        self._timer_refresh_topics = QTimer(self)
        self._timer_refresh_topics.timeout.connect(self.refresh_topics)


        # @Slot()
        # def test():
        #     print "@@@@@@@@@@@@@@@@@@@@@@@@@@2 data changed @@@@@@@@@@@@@@@@@@@@@@2222@@@@@@@"

        # self.topics_tree_widget.model().dataChanged.connect(test)

        

        # print dir(self.selectionChanged)

        @Slot(dict)
        def selection_changed(data):
            print "#\n#\n#\nthe selcted items are:", data, "\n\n"

        self.selectionChanged.connect(selection_changed)


    def set_topic_specifier(self, specifier):
        self._select_topic_type = specifier

    def start(self):
        """
        This method needs to be called to start updating topic pane.
        """
        self._timer_refresh_topics.start(1000)

    @Slot('QTreeWidgetItem', int)
    def itemChanged(self, item, column):
        # print "<<<<<<<<<<<<<<<<<<<<<<<<<< item changed >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
        selected = self.get_selected()
        if item._topic_name in selected and self._column_names[column] in ["min", "max", "value"]:
            self.selectionChanged.emit(selected)

    @Slot('QTreeWidgetItem')
    def expanded(self, item):

        name = item.data(0, Qt.UserRole)

        if not isinstance(item, TreeWidgetItem) or not item._is_topic:
            return

        print "expanded", name
        self._topics[item._topic_name]['info'].start_monitoring()


    @Slot('QTreeWidgetItem')
    def collapsed(self, item):

        name = item.data(0, Qt.UserRole)

        if not isinstance(item, TreeWidgetItem) or not item._is_topic:
            return

        print "collapsed", name
        self._topics[item._topic_name]['info'].stop_monitoring()

    _items_param = {}

    def get_desc(self, item):
        desc = {}
        if item._topic_name in self._current_params:
            desc = self._current_params[item._topic_name]

        vmin = item.data(self._column_names.index("min"), Qt.EditRole)
        vmax = item.data(self._column_names.index("max"), Qt.EditRole)
        val = item.data(self._column_names.index("value"), Qt.EditRole)

        def tryFloat(s):
            try: 
                return float(s)
            except:
                return None

        vmin = tryFloat(vmin)
        vmax = tryFloat(vmax)
        val = tryFloat(val)

        desc["min"] = vmin
        desc["max"] = vmax
        desc["default"] = val

        return desc

    def get_selected(self):
        # param_name:desc
        return {param:self.get_desc(self._tree_items[param]) for param in self._selected_items if param in self._current_params}
        pass


    def insert_param(self, param_name, param_desc, parent = None):
        if parent == None:
            parent = self.topics_tree_widget

        pnames = param_name.split("/")        

        print pnames
        
        ns = ""
        item = parent
        for name in pnames:
            if name == "":
                continue

            _name = "/" + name 
            ns = ns + _name

            if ns not in self._tree_items:
                # print ">>>> ",  ns
                _item = TreeWidgetItem(self._toggle_monitoring, ns, item)
                _item.setText(self._column_index['topic'], _name)
                _item.setData(0, Qt.UserRole, "name_space")

                _item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsTristate)

                self._tree_items[ns] = _item 
                # _item.setText(self._column_index['type'], type_name)
                # _item.setData(0, Qt.UserRole, name_space)

            item = self._tree_items[ns]

        item.setFlags(Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable )

        item.setData(self._column_index['min'], Qt.EditRole, str(param_desc["min"]))
        item.setData(self._column_index['max'], Qt.EditRole, str(param_desc["max"]))
        item.setData(self._column_index['value'], Qt.EditRole, str(param_desc["default"]))
        item.setData(self._column_index['type'], Qt.EditRole, str(param_desc["type"]))

        self._items_param[item] = param_name


        print param_name, " added"
        pass

    _current_params = {}

    # TODO: implement the delete mechanism
    def delete_param(self, param_name, parent = None):
        pass


    @Slot()
    def refresh_topics(self):
        """
        refresh tree view items
        """
        # print "is refreshing"

        nodes = dynamic_reconfigure.find_reconfigure_services()
        # dparams = []
        dparams = {}
        for node in nodes:
            client = dynamic_reconfigure.client.Client(node, timeout=3)
            gdesc = client.get_group_descriptions()
            for pdesc in gdesc["parameters"]:
                param = node + "/" + pdesc["name"]
                dparams[param] = pdesc

        # dparams = dparams.items()

        for param, desc in self._current_params.items():
            if param not in dparams:
                del self._current_params[param]
                # TODO: delete the tree widget item

        for param, desc in dparams.items():
            if param not in self._current_params:
                self._current_params[param] = desc
                self.insert_param(param, desc)


        # print self._current_params

        # print self._tree_items

        # dparams = rospy.get_published_topics()

        # print self._items_param

        # selected_dict = { self._selected_items[index] : index for index in range(len(self._selected_items)) }
        # print selected_dict
        # print self._selected_items
        # print self.get_selected()

        return 


        try:
            if self._selected_topics is None:
                topic_list = dparams
                if topic_list is None:
                    rospy.logerr('Not even a single published topic found. Check network configuration')
                    return
        except IOError as e:
            rospy.logerr("Communication with rosmaster failed: {0}".format(e.strerror))
            return

        if self._current_topic_list != topic_list:
            self._current_topic_list = topic_list

            print "is updating"

            # start new topic dict
            new_topics = {}

            for topic_name, topic_type in topic_list:
                # if topic is new or has changed its type
                if topic_name not in self._topics or \
                   self._topics[topic_name]['type'] != topic_type:
                    # create new TopicInfo
                    topic_info = TopicInfo(topic_name, topic_type)
                    message_instance = None
                    if topic_info.message_class is not None:
                        message_instance = topic_info.message_class()
                    # add it to the dict and tree view
                    topic_item = self._recursive_create_widget_items(self.topics_tree_widget, topic_name, topic_type, message_instance)
                    new_topics[topic_name] = {
                       'item': topic_item,
                       'info': topic_info,
                       'type': topic_type,
                    }
                else:
                    # if topic has been seen before, copy it to new dict and
                    # remove it from the old one
                    new_topics[topic_name] = self._topics[topic_name]
                    del self._topics[topic_name]

            # clean up old topics
            for topic_name in self._topics.keys():
                self._topics[topic_name]['info'].stop_monitoring()
                index = self.topics_tree_widget.indexOfTopLevelItem(
                                           self._topics[topic_name]['item'])
                self.topics_tree_widget.takeTopLevelItem(index)
                del self._topics[topic_name]

            # switch to new topic dict
            self._topics = new_topics



        # self._update_topics_data()

    def _update_topics_data(self):

        selected_dict = { self._selected_items[index] : index for index in range(len(self._selected_items)) }
        print selected_dict


        for topic in self._topics.values():
            topic_info = topic['info']
            if topic_info.monitoring:
                # update rate
                rate, _, _, _ = topic_info.get_hz()
                rate_text = '%1.2f' % rate if rate != None else 'unknown'

                # update bandwidth
                bytes_per_s, _, _, _ = topic_info.get_bw()
                if bytes_per_s is None:
                    bandwidth_text = 'unknown'
                elif bytes_per_s < 1000:
                    bandwidth_text = '%.2fB/s' % bytes_per_s
                elif bytes_per_s < 1000000:
                    bandwidth_text = '%.2fKB/s' % (bytes_per_s / 1000.)
                else:
                    bandwidth_text = '%.2fMB/s' % (bytes_per_s / 1000000.)

                # update values
                value_text = ''
                self.update_value(topic_info._topic_name, topic_info.last_message)

            else:
                rate_text = ''
                bandwidth_text = ''
                value_text = 'not monitored' if topic_info.error is None else topic_info.error

            # self._tree_items[topic_info._topic_name].setText(self._column_index['rate'], rate_text)
            # self._tree_items[topic_info._topic_name].setText(self._column_index['bandwidth'], bandwidth_text)
            self._tree_items[topic_info._topic_name].setText(self._column_index['value'], value_text)

    def update_value(self, topic_name, message):
        if hasattr(message, '__slots__') and hasattr(message, '_slot_types'):
            for slot_name in message.__slots__:
                self.update_value(topic_name + '/' + slot_name, getattr(message, slot_name))

        elif type(message) in (list, tuple) and (len(message) > 0) and hasattr(message[0], '__slots__'):

            for index, slot in enumerate(message):
                if topic_name + '[%d]' % index in self._tree_items:
                    self.update_value(topic_name + '[%d]' % index, slot)
                else:
                    base_type_str, _ = self._extract_array_info(self._tree_items[topic_name].text(self._column_index['type']))
                    self._recursive_create_widget_items(self._tree_items[topic_name], topic_name + '[%d]' % index, base_type_str, slot)
            # remove obsolete children
            if len(message) < self._tree_items[topic_name].childCount():
                for i in range(len(message), self._tree_items[topic_name].childCount()):
                    item_topic_name = topic_name + '[%d]' % i
                    self._recursive_delete_widget_items(self._tree_items[item_topic_name])
        else:
            if topic_name in self._tree_items:
                self._tree_items[topic_name].setText(self._column_index['value'], repr(message))

    def _extract_array_info(self, type_str):
        array_size = None
        if '[' in type_str and type_str[-1] == ']':
            type_str, array_size_str = type_str.split('[', 1)
            array_size_str = array_size_str[:-1]
            if len(array_size_str) > 0:
                array_size = int(array_size_str)
            else:
                array_size = 0

        return type_str, array_size

    def _recursive_create_widget_items(self, parent, topic_name, type_name, message):
        if parent is self.topics_tree_widget:
            # show full topic name with preceding namespace on toplevel item
            topic_text = topic_name
            # item = TreeWidgetItem(self._toggle_monitoring, topic_name, parent)


            _item = parent
            topic_names = topic_name.split('/')
            name_space = ""
            for name in topic_names:
                if name == "":
                    continue
                _name = "/" + name
                name_space = name_space + _name
                if name_space not in self._tree_items:
                    print ">>>"+name_space

                    is_topic = False

                    if name_space == topic_name:
                        is_topic = True


                    _item = TreeWidgetItem(self._toggle_monitoring, name_space, _item, is_topic = is_topic)
                    _item.setText(self._column_index['topic'], _name)
                    _item.setText(self._column_index['type'], type_name)
                    _item.setData(0, Qt.UserRole, name_space)

                    self._tree_items[name_space] = _item




                _item = self._tree_items[name_space]

            item = _item



        else:
            topic_text = topic_name.split('/')[-1]
            if '[' in topic_text:
                topic_text = topic_text[topic_text.index('['):]


            item = TreeWidgetItem(self._toggle_monitoring, topic_name, parent)
            # item = QTreeWidgetItem(parent)
            # item.setCheckState(0, Qt.Unchecked)

            item.setText(self._column_index['topic'], topic_text)
            item.setText(self._column_index['type'], type_name)
            item.setData(0, Qt.UserRole, topic_name)
            self._tree_items[topic_name] = item


        
        if hasattr(message, '__slots__') and hasattr(message, '_slot_types'):
            for slot_name, type_name in zip(message.__slots__, message._slot_types):
                self._recursive_create_widget_items(item, topic_name + '/' + slot_name, type_name, getattr(message, slot_name))

        else:
            base_type_str, array_size = self._extract_array_info(type_name)
            try:
                base_instance = roslib.message.get_message_class(base_type_str)()
            except (ValueError, TypeError):
                base_instance = None
            if array_size is not None and hasattr(base_instance, '__slots__'):
                for index in range(array_size):
                    self._recursive_create_widget_items(item, topic_name + '[%d]' % index, base_type_str, base_instance)
        return item



    def _toggle_monitoring(self, topic_name):
        item = self._tree_items[topic_name]
        if item.checkState(CHECK_COLUMN):
            print "start %s" % topic_name
            if topic_name not in self._selected_items and topic_name in self._current_params:
                self._selected_items.append(topic_name)
                # item.setText(CHECK_COLUMN, str(self._selected_items.index(topic_name)))
            # self._topics[topic_name]['info'].start_monitoring()
        else:
            print "stop %s" % topic_name
            if topic_name in self._selected_items:
                self._selected_items.remove(topic_name)
            item.setText(CHECK_COLUMN,'')

        # sel = self._selected_items
        # for i in range(len(sel)):
        #     if sel[i] in self._current_params:
        #         _item = self._tree_items[sel[i]]
        #         _item.setText(CHECK_COLUMN, '{%d}' % i )

        self.selectionChanged.emit(self.get_selected())

            # self._topics[topic_name]['info'].stop_monitoring()
        

    def _recursive_delete_widget_items(self, item):
        def _recursive_remove_items_from_tree(item):
            for index in reversed(range(item.childCount())):
                _recursive_remove_items_from_tree(item.child(index))
            topic_name = item.data(0, Qt.UserRole)
            del self._tree_items[topic_name]
        _recursive_remove_items_from_tree(item)
        item.parent().removeChild(item)

    @Slot('QPoint')
    def handle_header_view_customContextMenuRequested(self, pos):
        header = self.topics_tree_widget.header()

        # show context menu
        menu = QMenu(self)
        action_toggle_auto_resize = menu.addAction('Toggle Auto-Resize')
        action = menu.exec_(header.mapToGlobal(pos))

        # evaluate user action
        if action is action_toggle_auto_resize:
            if header.resizeMode(0) == QHeaderView.ResizeToContents:
                header.setResizeMode(QHeaderView.Interactive)
            else:
                header.setResizeMode(QHeaderView.ResizeToContents)

    @Slot('QPoint')
    def on_topics_tree_widget_customContextMenuRequested(self, pos):
        item = self.topics_tree_widget.itemAt(pos)
        if item is None:
            return

        # show context menu
        menu = QMenu(self)
        action_item_expand = menu.addAction(QIcon.fromTheme('zoom-in'), 'Expand All Children')
        action_item_collapse = menu.addAction(QIcon.fromTheme('zoom-out'), 'Collapse All Children')
        action = menu.exec_(self.topics_tree_widget.mapToGlobal(pos))

        # evaluate user action
        if action in (action_item_expand, action_item_collapse):
            expanded = (action is action_item_expand)

            def recursive_set_expanded(item):
                item.setExpanded(expanded)
                for index in range(item.childCount()):
                    recursive_set_expanded(item.child(index))
            recursive_set_expanded(item)

    def shutdown_plugin(self):
        for topic in self._topics.values():
            topic['info'].stop_monitoring()
        self._timer_refresh_topics.stop()

    def set_selected_topics(self, selected_topics):
        """
        @param selected_topics: list of tuple. [(topic_name, topic_type)]
        @type selected_topics: []
        """
        rospy.logdebug('set_selected_topics topics={}'.format(
                                                         len(selected_topics)))
        self._selected_topics = selected_topics

    # TODO(Enhancement) Save/Restore tree expansion state
    def save_settings(self, plugin_settings, instance_settings):
        header_state = self.topics_tree_widget.header().saveState()
        instance_settings.set_value('tree_widget_header_state', header_state)

    def restore_settings(self, pluggin_settings, instance_settings):
        if instance_settings.contains('tree_widget_header_state'):
            header_state = instance_settings.value('tree_widget_header_state')
            if not self.topics_tree_widget.header().restoreState(header_state):
                rospy.logwarn("rqt_dyn_tune: Failed to restore header state.")








class TreeWidgetItem(QTreeWidgetItem):

    _column_names = ['topic', 'type', 'min', 'value', 'max', 'checkbox']

    def flags(self, index):
        print "checking flags"
        if index == 1:
            return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled
        else:
            return QtCore.Qt.ItemIsEnabled



    def __init__(self, check_state_changed_callback, topic_name, parent=None, is_topic = False):
        super(TreeWidgetItem, self).__init__(parent)
        self._check_state_changed_callback = check_state_changed_callback
        self._topic_name = topic_name
        self.setCheckState(CHECK_COLUMN, Qt.Unchecked)
        self._is_topic = is_topic
        
        self._slider = QSlider(Qt.Horizontal)
        self._hbox = QHBoxLayout()
        self._min_label = QLabel("min")
        self._max_label = QLabel("max")
        self._hbox.addWidget(self._min_label)
        self._hbox.addWidget(self._slider)
        self._hbox.addWidget(self._max_label)

        tree = self.treeWidget()
        widget = QWidget()
        widget.setLayout(self._hbox)
        # tree.setItemWidget(self, 3, widget)        

        self.setTextAlignment(self._column_names.index("min"), Qt.AlignRight | Qt.AlignVCenter)
        self.setTextAlignment(self._column_names.index("max"), Qt.AlignLeft | Qt.AlignVCenter)
        self.setTextAlignment(self._column_names.index("value"), Qt.AlignHCenter | Qt.AlignVCenter)
        self.setTextAlignment(self._column_names.index("type"), Qt.AlignHCenter | Qt.AlignVCenter)

        self.setFlags(Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable )

        self._slider.valueChanged.connect(self.sliderValueChanged)



    @Slot(int)
    def sliderValueChanged(self, value):
        self.setText(2, str(value))
        print "value changed to %d" % value
        pass



        # print(topic_name)

    def setData(self, column, role, value):
        if role == Qt.CheckStateRole:
            state = self.checkState(column)
            # if state:
            #     item.setAutoFillBackground
        
        # if state:
        #     super(TreeWidgetItem, self).setData(column, Qt.UserRole, self._selected_items.index(self._topic_name))    

        super(TreeWidgetItem, self).setData(column, role, value)

        if role == Qt.CheckStateRole and state != self.checkState(column):
            self._check_state_changed_callback(self._topic_name)



