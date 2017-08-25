# syntax.py

import sys

from python_qt_binding.QtCore import QRegExp, Qt
from python_qt_binding.QtGui import QColor, QTextCharFormat, QFont, QSyntaxHighlighter

def format(color, style=''):
	"""Return a QTextCharFormat with the given attributes.
	"""
	_color = QColor()
	if type(color) == QColor:
		_color = color
	else:
		_color.setNamedColor(color)

	_format = QTextCharFormat()
	_format.setForeground(_color)
	if 'bold' in style:
		_format.setFontWeight(QFont.Bold)
	if 'italic' in style:
		_format.setFontItalic(True)

	return _format

reformat = format


# Syntax styles that can be shared by all languages
BRIGHT_STYLES = {
	'defaults': format('black'),
	'keyword': format('blue'),
	'operator': format('red'),
	'brace': format('black'),
	'defclass': format('black', 'bold'),
	'string': format('darkmagenta'),
	'string2': format('green'),
	'comment': format('darkGray', 'italic'),
	'self': format('black', 'italic'),
	'numbers': format('brown'),
}

DARK_STYLES = {
	'defaults': format('white'),
	'keyword': format('lightBlue', 'bold'),
	'operator': format('orange'),
	'brace': format('white'),
	'defclass': format('lightGreen', 'bold'),
	'string': format('darkmagenta'),
	'string2': format('green'),
	'comment': format('darkGray', 'italic'),
	'self': format('white', 'italic'),
	'numbers': format('brown'),
}


class PythonHighlighter (QSyntaxHighlighter):
	"""Syntax highlighter for the Python language.
	"""

	# defaults
	defaults = [
		':', '\.'
	]

	# Python keywords
	keywords = [
		'and', 'assert', 'break', 'class', 'continue', 'def',
		'del', 'elif', 'else', 'except', 'exec', 'finally',
		'for', 'from', 'global', 'if', 'import', 'in',
		'is', 'lambda', 'not', 'or', 'pass', 'print',
		'raise', 'return', 'try', 'while', 'yield',
		'None', 'True', 'False', 'str', 'as'
	]

	# Python operators
	operators = [
		'=',
		# Comparison
		'==', '!=', '<', '<=', '>', '>=',
		# Arithmetic
		'\+', '-', '\*', '/', '//', '\%', '\*\*',
		# In-place
		'\+=', '-=', '\*=', '/=', '\%=',
		# Bitwise
		'\^', '\|', '\&', '\~', '>>', '<<',
	]

	# Python braces
	braces = [
		'\{', '\}', '\(', '\)', '\[', '\]',
	]
	def __init__(self, document, is_dark = False, default = None):
		QSyntaxHighlighter.__init__(self, document)

		def contents_changed():
			self.highlightBlock("document.toPlainText()")

		document.contentsChanged.connect(contents_changed)

		self.is_dark = is_dark
		self.default = default

		global reformat

		if is_dark:
			STYLES = DARK_STYLES
		else:
			STYLES = BRIGHT_STYLES

		if default != None:
			STYLES['defaults'] = reformat(*default)

		# Multi-line strings (expression, flag, style)
		# FIXME: The triple-quotes in these two lines will mess up the
		# syntax highlighting from this point onward
		self.tri_single = (QRegExp("'''"), 1, STYLES['string2'])
		self.tri_double = (QRegExp('"""'), 2, STYLES['string2'])

		rules = []

		rules += [(r'%s' % w, 0, STYLES['defaults'])
			for w in PythonHighlighter.defaults]						
		# Keyword, operator, and brace rules
		rules += [(r'\b%s\b' % w, 0, STYLES['keyword'])
			for w in PythonHighlighter.keywords]
		rules += [(r'%s' % o, 0, STYLES['operator'])
			for o in PythonHighlighter.operators]
		rules += [(r'%s' % b, 0, STYLES['brace'])
			for b in PythonHighlighter.braces]

		# All other rules
		rules += [
			# 'self'
			(r'\bself\b', 0, STYLES['self']),

			# Double-quoted string, possibly containing escape sequences
			(r'"[^"\\]*(\\.[^"\\]*)*"', 0, STYLES['string']),
			# Single-quoted string, possibly containing escape sequences
			(r"'[^'\\]*(\\.[^'\\]*)*'", 0, STYLES['string']),

			# 'def' followed by an identifier
			(r'\bdef\b\s*(\w+)', 1, STYLES['defclass']),
			# 'class' followed by an identifier
			(r'\bclass\b\s*(\w+)', 1, STYLES['defclass']),

			# From '#' until a newline
			(r'#[^\n]*', 0, STYLES['comment']),

			# Numeric literals
			(r'\b[+-]?[0-9]+[lL]?\b', 0, STYLES['numbers']),
			(r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', 0, STYLES['numbers']),
			(r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', 0, STYLES['numbers']),
		]

		# Build a QRegExp for each pattern
		self.rules = [(QRegExp(pat), index, fmt)
			for (pat, index, fmt) in rules]



	def highlightBlock(self, text):
		"""Apply syntax highlighting to the given block of text.
		"""
		# print "&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&7"

		global reformat
		
		if self.is_dark:
			STYLES = DARK_STYLES
		else:
			STYLES = BRIGHT_STYLES

		if self.default != None:
			STYLES['defaults'] = reformat(*self.default)

		# Do other syntax formatting
		self.setFormat( 0, len(text), STYLES['defaults'])


		for expression, nth, format in self.rules:
			index = expression.indexIn(text, 0)

			while index >= 0:
				# We actually want the index of the nth match
				index = expression.pos(nth)
				# length = expression.cap(nth).length()
				length = len(expression.cap(nth))
				self.setFormat(index, length, format)
				index = expression.indexIn(text, index + length)

		self.setCurrentBlockState(0)

		# Do multi-line strings
		in_multiline = self.match_multiline(text, *self.tri_single)
		if not in_multiline:
			in_multiline = self.match_multiline(text, *self.tri_double)


	def match_multiline(self, text, delimiter, in_state, style):
		"""Do highlighting of multi-line strings. ``delimiter`` should be a
		``QRegExp`` for triple-single-quotes or triple-double-quotes, and
		``in_state`` should be a unique integer to represent the corresponding
		state changes when inside those strings. Returns True if we're still
		inside a multi-line string when this function is finished.
		"""
		# If inside triple-single quotes, start at 0
		if self.previousBlockState() == in_state:
			start = 0
			add = 0
		# Otherwise, look for the delimiter on this line
		else:
			start = delimiter.indexIn(text)
			# Move past this match
			add = delimiter.matchedLength()

		# As long as there's a delimiter match on this line...
		while start >= 0:
			# Look for the ending delimiter
			end = delimiter.indexIn(text, start + add)
			# Ending delimiter on this line?
			if end >= add:
				length = end - start + add + delimiter.matchedLength()
				self.setCurrentBlockState(0)
			# No; multi-line string
			else:
				self.setCurrentBlockState(in_state)
				length = len(text) - start + add
			# Apply formatting
			self.setFormat(start, length, style)
			# Look for the next match
			start = delimiter.indexIn(text, start + length)

		# Return True if still inside a multi-line string, False otherwise
		if self.currentBlockState() == in_state:
			return True
		else:
			return False