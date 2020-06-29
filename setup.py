import os
from setuptools import setup, find_packages

def read(fname):
	return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
	name = "s3sync",
	version = "0.1.3",
	author = "Gary Danko",
	author_email = "gary_danko@intuit.com",
	url = "https://github.intuit.com/gdanko/python-s3sync",
	license = "GPLv3",
	description = "A Python package which facilitates fast and intelligent syncing between s3 > s3, s3 > local, and local > s3",
	packages = ["s3sync"],
	package_dir = {"s3sync": "s3sync"},
	install_requires = ["boto3", "botocore"],

	# See https://pypi.python.org/pypi?%3Aaction=list_classifiers
	classifiers = [
		"Development Status :: 4 - Beta",
		"Environment :: Console",
		"Intended Audience :: System Administrators",
		"License :: Other/Proprietary License",
		"Operating System :: POSIX :: Other",
		"Programming Language :: Python :: 3",
		"Programming Language :: Python :: 3.3",
		"Programming Language :: Python :: 3.4",
		"Programming Language :: Python :: 3.5"
	]
)
