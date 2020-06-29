class MissingConstructorParameter(Exception):
	def __init__(self, classname=None, parameter=None):
		self.classname = classname
		self.parameter = parameter
		return

	def __str__(self):
		self.error = "The required \"{}\" parameter is missing from the {} constructor.".format(self.parameter, self.classname)
		return self.error

class LocalToLocalSync(Exception):
	def __init__(self):
		return

	def __str__(self):
		self.error = "You are trying to sync local to local with this module. Try rsync."
		return self.error

class FileReadError(Exception):
	def __init__(self, path=None, message=None):
		self.path = path
		self.message = message
		return

	def __str__(self):
		self.error = "An error occurred while reading the file \"{}\": {}".format(path, message)
		return self.error

class FileReadError(Exception):
	def __init__(self, path=None, message=None):
		self.path = path
		self.message = message
		return

	def __str__(self):
		self.error = "An error occurred while writing the file \"{}\": {}".format(path, message)
		return self.error

class FileCopyError(Exception):
	def __init__(self, src=None, dest=None, message=None):
		self.src = src
		self.dest = dest
		self.message = message
		return

	def __str__(self):
		self.error = "An error occurred while copying the file \"{}\" to \"{}\": {}".format(src, dest, message)
		return self.error

class MkdirError(Exception):
	def __init__(self, path=None, message=None):
		self.path = path
		self.message = message
		return

	def __str__(self):
		self.error = "An error occurred while creating the directory \"{}\": {}".format(path, message)
		return self.error