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

from __future__ import division
import os
import sys

from python_qt_binding import loadUi
from python_qt_binding.QtCore import Qt, QTimer, Signal, Slot, QSize, QRectF, QSizeF, Property
from python_qt_binding.QtGui import QIcon, QFont, QFontMetrics, QTextDocument, QTextOption, QPen, QPainter, QColor, QTextCursor, QSortFilterProxyModel
from python_qt_binding.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QPlainTextEdit, QListWidget, QCompleter
from python_qt_binding.QtWidgets import QStyledItemDelegate, QItemDelegate, QPushButton, QLineEdit, QTextEdit
from python_qt_binding.QtWidgets import QSlider, QAbstractItemView, QListWidgetItem, QStyleOptionViewItem
from python_qt_binding.QtWidgets import QHeaderView, QMenu, QTreeWidgetItem, QWidget, QAbstractItemView


import roslib
import rospkg
import rospy
from rospy.exceptions import ROSException

from .topic_info import TopicInfo

from dyn_tune.srv import ListAvailableFunctions
from dyn_tune.msg import Function, Task



import topic_widget as topic_widget
from .topic_widget import TreeWidgetItem

from dyn_tune import function

import dyn_tune.function

import syntax
import re
import numpy as np

class FuncEditorDelegate(QStyledItemDelegate):

	def __init__(self, parent = None):
		super(QStyledItemDelegate, self).__init__(parent)
		self.block = False
		self.editor = None


	def createEditor(self, parent, option, index):        
		editor = QTextEdit(parent)
		highlight = syntax.PythonHighlighter(editor.document())

		font = QFont("Courier")
		font.setFamily("Courier");
		font.setStyleHint(QFont.Monospace);
		font.setFixedPitch(True);
		font.setPointSize(10);
		editor.setFont(font)

		tab_stop = 4;  # 4 characters
		metrics = QFontMetrics(font)
		editor.setTabStopWidth(tab_stop * metrics.width(' '));

		return editor

	def setModelData(self, editor, model, index):
		index.model().setData(index, editor.toPlainText(), Qt.EditRole)
		self.editor = None
		self.block = False
		pass

	def setEditorData(self, editor, index):
		if self.block:
			return
		self.block = True
		editor.setPlainText(index.data(Qt.EditRole))

		def text_changed():
			editor.blockSignals(True)
			index.model().setData(index, editor.toPlainText(), Qt.EditRole)
			print "text changed"
			print editor.toHtml()

			editor.blockSignals(False)

		editor.textChanged.connect(text_changed)

		self.editor = editor
		self.last_index = index

		doc = editor.document()
		cursor = QTextCursor(doc);
		cursor.movePosition(QTextCursor.End);
		editor.setTextCursor(cursor);


	def sizeHint(self, option, index):
		item = self.parent().item(index.row())
		doc = QTextDocument()

		font = QFont("Courier")
		font.setFamily("Courier");
		font.setStyleHint(QFont.Monospace);
		font.setFixedPitch(True);
		font.setPointSize(self.parent().font().pointSize());
		doc.setDefaultFont(font)

		text = index.data(Qt.EditRole)	
		text = text.replace("\t", ''.join([' '] * 4))
		
		doc.setPlainText(text)
		doc.setDefaultStyleSheet("background-color: red;")
		
		return QSize(doc.size().width(), doc.size().height())


	def paint(self, painter, option, index):

		is_dark = True

		item = self.parent().item(index.row())

		if item.faulty:
			pen = QPen(QColor(255, 117, 117), 3)
			painter.setPen(pen)
			painter.drawRect(option.rect)
		elif item == self.parent().currentItem():
			pen = QPen(Qt.white, 3)
			painter.setPen(pen)
			painter.drawRect(option.rect)
		

		if not item.has_script:
			painter.fillRect(option.rect, QColor(153, 153, 153))		
		else:
			painter.fillRect(option.rect, Qt.white)
			is_dark = False

		doc = QTextDocument()
		highlight = syntax.PythonHighlighter(doc, is_dark = is_dark)

		font = QFont("Courier")
		font.setFamily("Courier");
		font.setStyleHint(QFont.Monospace);
		font.setFixedPitch(True);
		font.setPointSize(self.parent().font().pointSize())
		doc.setDefaultFont(font)


		text = index.data(Qt.EditRole)	
		text = text.replace("\t", ''.join([' '] * 4))

		doc.setPlainText(text)
		doc.setDefaultStyleSheet("background-color: red;")

		painter.translate(option.rect.topLeft())
		doc.drawContents(painter)
		painter.resetTransform()



class FuncWidget(QWidget):
	"""
	main class inherits from the ui window class.

	You can specify the topics that the topic pane.

	FuncWidget.start must be called in order to update topic pane.
	"""

	SELECT_BY_NAME = 0
	SELECT_BY_MSGTYPE = 1

	_column_names = ['topic', 'type', 'value', 'checkbox']

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
		super(FuncWidget, self).__init__()

		rp = rospkg.RosPack()
		ui_file = os.path.join(rp.get_path('rqt_dyn_tune'), 'resource', 'FuncWidget.ui')
		loadUi(ui_file, self)
		
		self._plugin = plugin
		self.list_available_functions = rospy.ServiceProxy('/list_available_functions', ListAvailableFunctions)
		self.functions = function.load_functions()
		self._select_topic_type = select_topic_type
		self.topics_tree_widget = self.widget_topic.topics_tree_widget

		self.execs = {}
		self.values = {}
		self.items = {}

		


		self.hLayout_0.setStretchFactor(self.vLayout_0, 5)
		self.hLayout_0.setStretchFactor(self.gridLayout, 2)


		@Slot(dict)
		def selection_changed(data):
			self.func_list.clear()
			funcs = self.list_available_functions(self.widget_topic.get_selected_types()).functions			

			for func in funcs:
				item = QListWidgetItem()				
				item.setData(Qt.UserRole, func)
				item.setText(func + "(...)")
				item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
				self.func_list.addItem(item)

			self.block_label.setText("")


		self.add_button.clicked.connect(self.add_button_clicked)
		self.add_script.clicked.connect(self.add_script_clicked)

		self.widget_topic.topicsRefreshed.connect(self.topics_refreshed)        
		self.widget_topic.selectionChanged.connect(selection_changed)
		
		self.widget_topic.selectionChanged.emit([])


		delegate = FuncEditorDelegate(self.block_list)
		font = QFont("Monospace")

		self.block_list.setFont(font)
		self.block_list.setItemDelegate(delegate)
		self.block_list.setContentsMargins(100,10,10,100)
		self.block_list.setWordWrap(True)
		self.block_list.setTextElideMode(Qt.ElideNone)		
		self.block_list.setSelectionMode(QAbstractItemView.SingleSelection)
		self.block_list.setDragEnabled(True)
		self.block_list.viewport().setAcceptDrops(True)
		self.block_list.setDropIndicatorShown(True)
		self.block_list.setDragDropMode(QAbstractItemView.InternalMove)
		self.block_list.setMouseTracking(True)
		self.block_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
		self.block_list.setSpacing(3)

		self.block_list.addItem( ListBlockItem("\"\"\"\n" \
												+ "# Add your own python script here! You could \n" \
												+ "# access the variables defined by the previous \n" \
												+ "# blocks. To access observable values use \n" \
												+ "# vars()['value_name'] or locals()['value_name'] \n" \
												+ "\"\"\"") )


		self.func_list.setAlternatingRowColors(True)
		self.func_list.itemSelectionChanged.connect(self.func_list_changed)
		self.func_ret.setAutoFillBackground(True)

		completer = QCompleter(self.block_list.model())
		completer = QCompleter(["bob", "bobby", "bud", "charles", "charlie"], self.func_ret)
		self.func_ret.setCompleter(completer)
		self.func_ret.setEditable(True)

		# add a filter model to filter matching items
		self.pFilterModel = QSortFilterProxyModel(self.func_ret)
		self.pFilterModel.setFilterCaseSensitivity(Qt.CaseInsensitive)
		self.pFilterModel.setSourceModel(self.widget_topic.topics_tree_widget.model())

		# add a completer, which uses the filter model
		self.completer = QCompleter(self.pFilterModel, self)
		# always show all (filtered) completions
		self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)

		self.func_ret.setCompleter(self.completer)

		# connect signals
		def filter(text):
			print "Edited: ", text, "type: ", type(text)
			self.pFilterModel.setFilterFixedString(str(text))

		def on_completer_activated(text):
			if text:
				index = self.func_ret.findText(str(text))
				self.func_ret.setCurrentIndex(index)

		self.func_ret.lineEdit().textEdited[unicode].connect(filter)
		self.completer.activated.connect(on_completer_activated)


		def block_label_clicked(*arg):
			# print "BLOCK LABEL CLICKED"
			self.assign_var.setFocus()
			self.assign_var.selectAll()

		self.block_label.clicked.connect(block_label_clicked)
		# self.block_label.setLineWrapMode(QTextEdit.WidgetWidth)


		def assign_var_text_changed(text = None):
			if text == None:
				text = self.assign_var.text()
			font = self.assign_var.font()
			fm = QFontMetrics(font);
			pixelsWide = fm.width(text);
			# pixelsHigh = fm.height();
			self.assign_var.setFixedSize(pixelsWide + 10, self.assign_var.height())

			text = self.assign_var.text()
			text = text.replace(" ", "")
			self.assign_var.setText(text)

		self.assign_var.textChanged.connect(assign_var_text_changed)
		self.assign_var.returnPressed.connect(self.add_button_clicked)



	def func_list_changed(self, *_):


		args = self.widget_topic.get_selected()
		func = self.func_list.selectedItems()

		if func and args:
			func = func[0].data(Qt.UserRole)		
			first = " = {0}( ".format(func)
			joint = ', '
			second = "{0} )".format(joint.join(args))

			self.block_label.setText(first + second)
			self.assign_var.setFocus()
			self.assign_var.selectAll()

		else:
			self.block_label.setText("")




	def add_script_clicked(self, checked = False):	
		self.block_list.insertItem(self.block_list.currentRow() + 1, ListBlockItem())

	def add_button_clicked(self, checked = False):

		args = self.widget_topic.get_selected()
		func = self.func_list.selectedItems()
		retvar = self.assign_var.text()

		if args and func and retvar != '' and retvar != None:
			func = func[0].data(Qt.UserRole)
			print "there is items: ", args, func
			

			first = "{0} = {1}( ".format(retvar, func)
			spcs = len(first)
			joint = ',\n' + ''.join([' '] * spcs)
			second = "{0} )".format(joint.join(args))

			item = ListBlockItem((first + second), 
									func = self.functions[func], 
									args = args, 
									retvar = retvar, 
									has_script = False ) 

			font = QFont("Courier")
			font.setFamily("Courier");
			font.setStyleHint(QFont.Monospace);
			font.setFixedPitch(True);
			font.setPointSize(10);
			item.setFont(font)

			self.widget_topic.clear_selection()
			self.block_label.setText("")
			self.block_list.addItem(item)
			self.func_ret.setCurrentText(retvar)
	

	def resolve_type(self, msg):
		if hasattr(msg, '_type') and type(msg) != type:
			return msg._type

		if hasattr(msg, 'dtype') and type(msg.dtype.name) == str:
			return str(msg.dtype.name) + '[]'

		return type(msg).__name__


	def create_function_msg(self, name = "objective", desc = 'A new objective function'):
		func = Function()
		func.name = name

		blocks = [ self.block_list.item(index) for index in xrange(self.block_list.count()) ]

		for block in blocks:
			
			task = Task()
			task.has_script = block.has_script
			task.script = block.data(Qt.EditRole)
			
			if block.func != None:
				task.function = block.func.__name__
				task.args = block.args
				task.return_var = block.retvar

			func.tasks.append(task)

		func.return_var = self.func_ret.currentText()
		func.return_type = "*"
		func.arg_types = "[\"*\", []]"
		func.description = desc

		return func


	def topics_refreshed(self, values = {}):

		DUPLICATE_FACTOR = 10

		values =  { key:np.array([value] * DUPLICATE_FACTOR) for key, value in values.items() }

		items = [ self.block_list.item(index) for index in xrange(self.block_list.count()) ]

		print self.block_list.count()
		print "=========== EXECUTING ==========="
		count = 0
		for item in items:
			print ">> block #%d" % count 
			count += 1
			values.update( item.execute(values) )
			print "_________________________________"
		print "================================="

		_values = values.copy()

		for key in _values:
			if re.match("__.*__",key):
				del values[key]

		self.values = values

		# print values

		topic_widget = self.widget_topic

		for key, value in self.values.items():
			if key not in topic_widget._tree_items:
				topic_widget._tree_items[key] = TreeWidgetItem(topic_widget._toggle_monitoring, key, self.topics_tree_widget, is_topic = False)
			
			_item = topic_widget._tree_items[key]
			_item.setText(topic_widget._column_index['topic'], key)
			_item.setText(topic_widget._column_index['type'], self.resolve_type(value))
			_item.setText(topic_widget._column_index['value'], repr(value))
			_item.setData(topic_widget._column_index['value'], Qt.UserRole, value)


		for key, item in topic_widget._tree_items.items():
			if key not in self.values:				
				
				topic_widget.unselect(key)
				topic_widget.remove(key)

				print self.values
				print "deleting", key

	def start(self):
		# self.widget_topic.start()
		pass

	def shutdown_plugin(self):
		self.widget_topic.shutdown_plugin()

	# TODO(Enhancement) Save/Restore tree expansion state
	def save_settings(self, plugin_settings, instance_settings):
		print "do no saving"
		pass
		# header_state = self.topics_tree_widget.header().saveState()
		# instance_settings.set_value('tree_widget_header_state', header_state)

	def restore_settings(self, pluggin_settings, instance_settings):
		print "do no restoring"
		pass
		# if instance_settings.contains('tree_widget_header_state'):
		#     header_state = instance_settings.value('tree_widget_header_state')
		#     if not self.topics_tree_widget.header().restoreState(header_state):
		#         rospy.logwarn("rqt_dyn_tune: Failed to restore header state.")

class ListBlockItem(QListWidgetItem):

	DEFAULT_TEXT = "\"\"\" Write your own python script here !!! \"\"\"\n"

	def __init__(self, text = None, 
						parent = None, func = None, args = [],
						 retvar = '', has_script = True):

		self.darkness = Property(bool, ListBlockItem.isDark, ListBlockItem.setDark)

		if text == None:
			text = ListBlockItem.DEFAULT_TEXT
		
		super(QListWidgetItem, self).__init__(text, parent)

		self.func = func
		self.args = args
		self.retvar = retvar
		self.has_script = has_script

		self.setFlags(	
						Qt.ItemIsDragEnabled | 
						Qt.ItemIsEnabled | 
						Qt.ItemIsSelectable | 
						# Qt.ItemIsUserCheckable |
						(Qt.ItemIsEditable if has_script else Qt.ItemIsEnabled) )


		self.faulty = False
		self.setData(Qt.UserRole, False)

		

	def setDark(self, is_dark):
		self.is_dark = is_dark

	def isDark(self):
		return self.is_dark

	def execute(self, values):

		try:
			if self.func != None:
				values.update({self.retvar:self.func(*self.args, **values)})

			if self.has_script:
				script = self.data(Qt.EditRole)
				exec(script, values, values)


			print "block executed successfullly"
			self.faulty = False
			self.setData(Qt.UserRole, False)
		except:
			print "block is faulty"

			import traceback
			traceback.print_exc()
			self.faulty = True
			self.setData(Qt.UserRole, True)
			
			pass

		return values
	   

	def setData(self, role, value):
		super(ListBlockItem, self).setData(role, value)


class StyledLabel(QLabel):

	clicked = Signal(name='clicked')

	def __init__(self, parent = None, flags = 0):
		super(QLabel, self).__init__(parent=parent)
		self.size =  None # QSize(0., 0.)
		self.is_resizable = True

	def mousePressEvent(self, event):
		self.clicked.emit()

	def sizeHint(self):
		if not self.is_resizable:
			return super(QLabel, self).sizeHint()

		doc = QTextDocument()

		font = self.font()
		font.setStyleHint(QFont.Monospace);
		font.setFixedPitch(True);
		doc.setDefaultFont(font)

		text = self.text()
		doc.setPlainText(text)

		size = QSize(doc.size().width(), doc.size().height())

		if size != None:			
			return size

		return super(QLabel, self).sizeHint()

	def paintEvent(self, event):
		painter = QPainter(self)

		doc = QTextDocument()
		highlight = syntax.PythonHighlighter(doc, is_dark = True, default = ['white'])

		font = self.font()
		font.setStyleHint(QFont.Monospace);
		font.setFixedPitch(True);
		doc.setDefaultFont(font)
		self.width = event.rect().width()
		text = self.text()

		doc.setPlainText(text)

		painter.translate(0., event.rect().center().y() - doc.size().height()/2.)
		doc.drawContents(painter, QRectF(event.rect()))
		painter.resetTransform()

		self.size = doc.size()

