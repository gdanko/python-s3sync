from pprint import pprint
from urllib.parse import urlparse
import os
import pathlib
import re
import s3sync.exception as exception
import s3sync.utils as utils
import sys

class Diff(object):
	def __init__(self, **kwargs):
		self.common = {}
		self.source_list, self.destination_list = {}, {}
		self.source_only, self.destination_only = {}, {}
		self.source_md5_mismatch, self.destination_md5_mismatch = {}, {}
		self.sync_list = {}

		if "source" in kwargs:
			self.source = kwargs["source"]
		else:
			raise exception.MissingConstructorParameter(classname=utils.classname(self), parameter="source")

		if "destination" in kwargs:
			self.destination = kwargs["destination"]
		else:
			raise exception.MissingConstructorParameter(classname=utils.classname(self), parameter="destination")

		if "s3" in kwargs:
			self.s3 = kwargs["s3"]
		else:
			raise exception.MissingConstructorParameter(classname=utils.classname(self), parameter="s3")

		self.delete = kwargs["delete"] if ("delete" in kwargs and isinstance(kwargs["delete"], bool)) else False
		self.exclude = kwargs["exclude"] if "exclude" in kwargs else []
		self.include = kwargs["include"] if "include" in kwargs else []

	def determine_types(self):
		source = urlparse(self.source)
		# Source
		if source.scheme == "s3":
			self.source_type = "s3"
			self.source_bucket = source.netloc
			self.source_path = source.path.strip("/")
		else:
			self.source_type = "local"
			self.source_path = self.source

		# Destination
		destination = urlparse(self.destination)
		if destination.scheme == "s3":
			destination = urlparse(self.destination)
			self.destination_type = "s3"
			self.destination_bucket = destination.netloc
			self.destination_path = destination.path.strip("/")
		else:
			if os.path.isabs(self.destination) == False:
				self.destination = os.path.abspath(self.destination)
			self.destination_type = "local"
			self.destination_path = self.destination
			self.destination_root = os.path.dirname(self.destination_path)
			utils.create_path(path=self.destination_path)

		if self.source_type == "local" and self.destination_type == "local":
			raise exception.LocalToLocalSync()

	def diff(self):
		sys.stdout.write("building file list ... ")
		if self.source_type == "local":
			self.source_list = self.get_local_files(path=self.source_path)
		elif self.source_type == "s3":
			self.source_list = self.get_s3_files(bucket=self.source_bucket, path=self.source_path)

		if self.destination_type == "local":
			self.destination_list = self.get_local_files(path=self.destination_path)
		elif self.destination_type == "s3":
			self.destination_list = self.get_s3_files(bucket=self.destination_bucket, path=self.destination_path)

		for name, obj in self.source_list.items():
			if name in self.destination_list:
				if self.destination_list[name]["md5sum"] == self.source_list[name]["md5sum"]:
					self.common[name] = obj
				else:
					self.source_md5_mismatch[name] = obj
			else:
				self.source_only[name] = obj

		for name, obj in self.destination_list.items():
			if name in self.source_list:
				if self.source_list[name]["md5sum"] == self.destination_list[name]["md5sum"]:
					self.common[name] = obj
				else:
					self.destination_md5_mismatch[name] = obj
			else:
				self.destination_only[name] = obj

		print("done")

	def get_list_item(self, source_file):
		relative_path = os.path.relpath(source_file, self.source)
		item = {
			"source": source_file,
			"destination": os.path.join(self.destination, relative_path),
		}
		return item

	def generate_sync_list(self):
		to_sync = utils.merge_dicts(self.source_only, self.source_md5_mismatch)
		for name, obj in to_sync.items():
			if self.source_type == "s3" and self.destination_type == "s3":
				source_file = os.path.join(
					os.path.dirname(self.source),
					obj["key"]
				)
				item = self.get_list_item(source_file)
				item["action"] = "copy"
				item["message"] = "copy: {} to {}".format(item["source"], item["destination"])
				#self.sync_list[name] = item

			elif self.source_type == "s3" and self.destination_type == "local":
				source_file = os.path.join(
					os.path.dirname(self.source),
					obj["key"]
				)
				item = self.get_list_item(source_file)
				item["action"] = "download"
				item["message"] = "download: {} to {}".format(item["source"], item["destination"])
				#self.sync_list[name] = item

			elif self.source_type == "local" and self.destination_type == "s3":
				source_file = obj["path"]
				item = self.get_list_item(source_file)
				item["action"] = "upload"
				item["message"] = "upload: {} to {}".format(item["source"], item["destination"])
				#self.sync_list[name] = item

			item["md5sum"] = obj["md5sum"]
			item["size"] = obj["size"]
			self.sync_list[name] = item

		if self.delete == True:
			for name, obj in self.destination_only.items():
				if self.destination_type == "s3":
					self.sync_list[name] = {
						"action": "delete",
						"message": "delete: s3://{}/{}".format(self.destination_bucket, obj["key"]),
						"bucket": self.destination_bucket,
						"key": obj["key"],
					}

				elif self.destination_type == "local":
					self.sync_list[name] = {
						"action": "delete",
						"message": "delete: {}".format(obj["path"]),
						"path": obj["path"],
					}

	# Clone from ruby version
	#def is_excluded(filename):
	#	if len(self.exclude) <= 0:
	#		return False
	#	out = False
	#	for pattern in self.exclude:
	#		if out == True:
	#			return True

	def get_local_files(self, path=None):
		output = {}
		for root, folders, files in os.walk(path):
			for filename in folders + files:
				item = os.path.join(root, filename)
				if os.path.isfile(item):
					p1 = item
					p2 = os.path.dirname(path)
					key = os.path.relpath(p1, p2)
					stripped_key = pathlib.Path(key)
					stripped_key = str(pathlib.Path(*stripped_key.parts[1:]))
					statinfo = os.stat(item)

					if os.path.isfile(item):
						output[stripped_key] = {
							"path": item,
							"dirname": os.path.dirname(key),
							"filename": os.path.basename(key),
							"size": statinfo.st_size,
							"md5sum": utils.md5sum(item),
							#"exclude": is_excluded(os.path.basename(key))
						}
		return output

	def get_s3_files(self, bucket=None, path=None):
		output = {}
		try:
			resp = self.s3.list_objects_v2(Bucket=bucket, Prefix="{}/".format(path), MaxKeys=10000)
		except:
			print("Failed to get the list from s3")
			sys.exit(1)

		for file_obj in resp["Contents"]:
			key = file_obj["Key"]
			stripped_key = pathlib.Path(key)
			stripped_key = str(pathlib.Path(*stripped_key.parts[1:]))
			if not re.match("\/$", key) and file_obj["Size"] != 0:
				output[stripped_key] = {
					"dirname": os.path.dirname(key),
					"filename": os.path.basename(key),
					"key": "{}/{}".format(os.path.dirname(key), os.path.basename(key)),
					"size": file_obj["Size"],
					"md5sum": file_obj["ETag"].replace("\"", ""),
					#"exclude": is_excluded(os.path.basename(key))
				}

		return output
