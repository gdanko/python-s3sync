from multiprocessing.dummy import Pool as ThreadPool
from pprint import pprint
from s3sync.diff import Diff
from shutil import rmtree
from urllib.parse import urlparse
import boto3
import botocore
import os
import s3sync.exception as exception
import s3sync.utils as utils
import sys
import logging

# http://boto3.readthedocs.io/en/latest/reference/services/s3.html

# Disable boto3 logging
logging.getLogger("boto3").setLevel(logging.CRITICAL)
logging.getLogger("botocore").setLevel(logging.CRITICAL)

class Syncer(object):
	def __init__(self, **kwargs):
		if "source" in kwargs:
			self.source = kwargs["source"]
		else:
			raise exception.MissingConstructorParameter(classname=utils.classname(self), parameter="source")

		if "destination" in kwargs:
			self.destination = kwargs["destination"]
		else:
			raise exception.MissingConstructorParameter(classname=utils.classname(self), parameter="destination")

		if "profile" in kwargs:
			self.profile = kwargs["profile"]
		else:
			raise exception.MissingConstructorParameter(classname=utils.classname(self), parameter="profile")
		
		if "region" in kwargs:
			self.region = kwargs["region"]
		else:
			raise exception.MissingConstructorParameter(classname=utils.classname(self), parameter="region")

		if "max_threads" in kwargs:
			self.max_threads = kwargs["max_threads"]
		else:
			self.max_threads = 12

		self.pool = ThreadPool(self.max_threads)
		self.debug = kwargs["debug"] if ("debug" in kwargs and isinstance(kwargs["debug"], bool)) else False
		self.dryrun = kwargs["dryrun"] if ("dryrun" in kwargs and isinstance(kwargs["dryrun"], bool)) else False
		self.acl = kwargs["acl"] if "acl" in kwargs else "private"
		self.delete = kwargs["delete"] if ("delete" in kwargs and isinstance(kwargs["delete"], bool)) else False
		self.verify = kwargs["verify"] if ("verify" in kwargs and isinstance(kwargs["verify"], bool)) else True
		self.logger = utils.configure_logger(loggerid=utils.generate_random(), debug=self.debug)

		# Create an exception
		try:
			session = boto3.session.Session(profile_name=self.profile)
			boto3.setup_default_session(profile_name=self.profile)
		except botocore.exceptions.ProfileNotFound as e:
			self.logger.error("There was a problem with your AWS profile: {}".format(str(e)))
			sys.exit(1)

		self.s3 = boto3.client("s3", region_name=self.region)
		self.s3_resource = boto3.resource("s3", region_name=self.region)

		# Create an exception
		try:
			self.s3.list_buckets()
		except (botocore.exceptions.ClientError, botocore.exceptions.NoCredentialsError) as e:
			self.logger.error("AWS was not able to validate the provided access credentials.")
			sys.exit(1)

		self.init()
		
	def sync(self):
		self.s3diff.diff()
		self.s3diff.generate_sync_list()
		self.__sync_files()

	def init(self):
		self.s3diff = Diff(
			source=self.source,
			destination=self.destination,
			s3=self.s3,
			#include=self.include,
			#exclude=self.exclude,
			delete=self.delete,
			debug=self.debug,
		)
		self.s3diff.determine_types()
		if self.s3diff.source_type == "s3":
			self.source_bucket = self.s3diff.source_bucket

	def reverse(self):
		old_source = self.source
		old_destination = self.destination
		self.source = old_destination
		self.destination = old_source
		self.init()

	def __sync_files(self):
		if len(self.s3diff.sync_list) > 0:
			sync_output = []
			actions = {"copy": [], "download": [], "upload": [], "delete": []}

			for name, obj in self.s3diff.sync_list.items():
				action = obj["action"]
				actions[action].append(obj)

			if len(actions["copy"]) > 0:
				output = self.pool.map(self.__s3_to_s3, actions["copy"])
				sync_output += output

			if len(actions["download"]) > 0:
				output = self.pool.map(self.__s3_to_local, actions["download"])
				sync_output += output

			if len(actions["upload"]) > 0:
				output = self.pool.map(self.__local_to_s3, actions["upload"])
				sync_output += output

			if len(actions["delete"]) > 0:
				#output = self.pool.map(self.__delete_files, actions["delete"])
				#sync_output += output
				self.__delete_files(actions["delete"][0])

			#pprint(sync_output)

	def __s3_to_s3(self, obj):
		out = {"status": "success", "message": "successfully copied {} to {}".format(obj["source"], obj["destination"])}
		if self.dryrun == True:
			self.logger.dryrun(obj["message"])
			return out
		print(obj["message"])

		source = urlparse(obj["source"])
		source_bucket = source.netloc
		source_key = source.path.strip("/")

		destination = urlparse(obj["destination"])
		destination_bucket = destination.netloc
		destination_key = destination.path.strip("/")
		destination_file = "{}/{}".format(destination_bucket, destination_key)

		try:
			resp = self.s3_resource.Object(destination_bucket, destination_key).copy_from(CopySource={"Bucket": source_bucket, "Key": source_key})
		except Exception as e:
			out = {"status": "error", "message": "Failed to copy {} to {}: {}".format(obj["source"], obj["destination"], e)}
			return out

		if self.verify:
			source_md5sum = obj["md5sum"]
			destination_md5sum = resp["CopyObjectResult"]["ETag"].replace("\"", "")

			if source_md5sum == destination_md5sum:
				self.logger.debug("Source and destination md5sums matched for {}.".format(obj["source"]))
				return out
			else:
				self.logger.debug("Source and destination md5sum mismatch for {}.".format(obj["source"]))
				out = {"status": "error", "message": "Failed to copy {} to {}: md5sum mismatch.".format(obj["source"], obj["destination"])}
				return out
		else:
			return out

	def __s3_to_local(self, obj):
		out = {"status": "success", "message": "successfully copied {} to {}".format(obj["source"], obj["destination"])}
		if self.dryrun == True:
			self.logger.dryrun(obj["message"])
			return out
		print(obj["message"])

		source = urlparse(obj["source"])
		source_bucket = source.netloc
		source_key = source.path.strip("/")
		destination_directory = os.path.dirname(obj["destination"])

		try:
			utils.create_path(path=destination_directory)
		except Exception as e:
			out = {"status": "error", "message": "Failed to create the parent directory {}".format(destination_directory)}
			return out

		try:
			self.s3_resource.Bucket(source_bucket).download_file(source_key, obj["destination"])
		except Exception as e:
			out = {"status": "error", "message": "Failed to copy {} to {}: {}".format(source_key, obj["destination"], e)}
			return out

		if self.verify:
			source_md5sum = obj["md5sum"]
			destination_md5sum = utils.md5sum(obj["destination"])
			if source_md5sum == destination_md5sum:
				self.logger.debug("Source and destination md5sums matched for {}.".format(obj["source"]))
				return out
			else:
				self.logger.debug("Source and destination md5sum mismatch for {}.".format(obj["source"]))
				out = {"status": "error", "message": "Failed to copy {} to {}: md5sum mismatch.".format(obj["source"], obj["destination"])}
				return out
		else:
			return out

	def __local_to_s3(self, obj):
		out = {"status": "success", "message": "successfully copied {} to {}".format(obj["source"], obj["destination"])}
		if self.dryrun == True:
			self.logger.dryrun(obj["message"])
			return out
		print(obj["message"])

		destination = urlparse(obj["destination"])
		destination_bucket = destination.netloc
		destination_key = destination.path.strip("/")

		try:
			mime_type = utils.mime_type(obj["source"])
			resp = self.s3_resource.Object(destination_bucket, destination_key).put(
				ACL=self.acl,
				Body=open(obj["source"], "rb"),
				ContentType=mime_type,
			)
		except Exception as e:
			out = {"status": "error", "message": "Failed to copy {} to {}: {}".format(obj["source"], obj["destination"], e)}
			return out

		if self.verify:
			source_md5sum = obj["md5sum"]
			destination_md5sum = resp["ETag"].replace("\"", "")
			if source_md5sum == destination_md5sum:
				self.logger.debug("Source and destination md5sums matched for {}.".format(obj["source"]))
				return out
			else:
				self.logger.debug("Source and destination md5sum mismatch for {}.".format(obj["source"]))
				out = {"status": "error", "message": "Failed to copy {} to {}: md5sum mismatch.".format(obj["source"], obj["destination"])}
				return out
		else:
			return out

	def __delete_files(self, obj):
		item = "unknown"
		if "path" in obj:
			item = obj["path"]
		elif "bucket" in obj and "key" in obj:
			item = "s3://{}/{}".format(obj["bucket"], obj["key"])

		out = {"status": "success", "message": "successfully deleted {}.".format(item)}
		if self.dryrun == True:
			self.logger.dryrun(obj["message"])
			return out
		print(obj["message"])

		if "path" in obj:
			try:
				if os.file.isfile(obj["path"]):
					os.remove(obj["path"])
				elif os.file.isdir(obj["path"]):
					rmtree(obj["path"])
				return out
			except Exception as e:
				out = {"status": "error", "message": "Failed to delete {}.".format(obj["path"])}
				return out
		elif "bucket" in obj and "key" in obj:
			try:
				self.s3.delete_object(
					Bucket=obj["bucket"],
					Key=obj["key"],
				)
				return out
			except Exception as e:
				out = {"status": "error", "message": "Failed to delete {}: {}.".format(obj["path"], e)}
				return out
