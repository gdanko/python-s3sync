#!/usr/bin/env python3

import os
import sys
import s3sync.sync as sync
from pprint import pprint


syncer = sync.Syncer(
	#source="/Users/gdanko/pypi",
	#destination="s3://automation-patterns-pypi",
	#source="s3://automation-patterns-repo/gem-repo",
	#destination="/Users/gdanko/.s3gem/s3-us-west-2.amazonaws.com/automation-patterns-repo/pypi",
	#destination="s3://automation-patterns-repo/pypi",
	
	#source="/Users/gdanko/.s3gem/s3-us-west-2.amazonaws.com/automation-patterns-repo/gem-repo",
	#destination="s3://automation-patterns-repo/pypi",

	##source="s3://automation-patterns-pypi",
	#destination="/Users/gdanko/.s3pypi/s3-us-west-2.amazonaws.com/automation-patterns-pypi",
	#source="/Users/gdanko/.s3pypi/s3-us-west-2.amazonaws.com/automation-patterns-pypi",
	#destination="s3://automation-patterns-pypi",
        source="s3://automation-patterns-pypi",
        destination="/Users/gdanko/.s3pypi/s3-us-west-2.amazonaws.com/automation-patterns-pypi",

	region="us-west-2",
	profile="default",
	acl="public-read",
	delete=True,
	debug=False,
	#dryrun=True,
	verify=True,
)

#pprint(syncer.s3diff.sync_list)
syncer.sync()
#syncer.s3diff.diff()