import hashlib
import logging
import os
import random
import s3sync.exception as exception
import sys

def generate_random(length=8):
	return "".join(random.choice("0123456789abcdef") for x in range(length))

def configure_logger(loggerid=None, debug=False):
	if loggers.get(loggerid):
		return loggers.get(loggerid)
	else:
		level = logging.DEBUG if debug == True else logging.INFO

		logger = logging.getLogger(loggerid)
		handler = logging.StreamHandler()
		formatter = logging.Formatter("%(levelname)s %(message)s")
		handler.setFormatter(formatter)
		logger.addHandler(handler)
		logger.setLevel(level)
		logger.propagate = False
		loggers[loggerid] = logger
	return logger

def classname(c):
	try:
		module = c.__class__.__module__
		name = c.__class__.__name__
		return "{}.{}".format(module, name)
	except:
		print("need a 'not a class' exception")
		sys.exit(1)

def create_path(path=None):
	try:
		os.makedirs(path)
	except OSError as e:
		if e.errno == 17:
			pass
		else:
			raise exception.MkdirError(path=path, message=e)

def merge_dicts(d1, d2):
	output = d1.copy()
	output.update(d2)
	return output

def md5sum(path):
	md5 = hashlib.md5()
	with open(path, "rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			md5.update(chunk)
	return md5.hexdigest()

loggers = {}