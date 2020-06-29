#!/usr/bin/env python3

import subprocess
from pprint import pprint
import re
import sys
import os


def find_package_name(stdout):
	match = re.search('^(copying files to|making hard links in) (.+)\.\.\.', stdout, flags=re.MULTILINE)

	if not match:
		raise RuntimeError('Package name not found in:\n' + stdout)

	return match.group(2)

def find_wheel_name(stdout):
	match = re.search('creating \'.*(dist.*\.whl)\' and adding', stdout, flags=re.MULTILINE)

	if not match:
		raise RuntimeError('Wheel name not found in:\n' + stdout)

	return match.group(1)

def sanitize_output(output):
	return output.decode("utf-8")

def build_package(package_dir, sdist, wheel):
	command = [
		"python3",
		"setup.py",
		"sdist",
		"--formats",
		"gztar",
		#"zip",
	]
	if wheel == True:
		command.append("bdist_wheel")

	process = subprocess.Popen(
		command,
		shell=False,
		cwd=package_dir,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
	)
	stdout, stderr = process.communicate()
	stdout = sanitize_output(stdout)
	stderr = sanitize_output(stderr)
	rc = process.wait()
	if rc != 0:
		print("non-zero return code")
		print(error)
		sys.exit(1)

	files = []
	package_name = find_package_name(stdout)
	wheel_name = find_wheel_name(stdout)

	if sdist:
		files.append(
			os.path.join(
				package_dir,
				"dist",
				package_name + ".tar.gz",
			)
		)

	if wheel:
		files.append(
			os.path.join(
				package_dir,
				"dist",
				os.path.basename(
					wheel_name
				),
			)
		)

	return package_name, files


sdist = True
wheel = True
package_dir = "/Users/gdanko/git/python-idps"

package_name, files = build_package(package_dir, sdist, wheel)
print(package_name)
pprint(files)

