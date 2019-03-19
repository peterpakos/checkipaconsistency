# -*- coding: utf-8 -*-

import re
from setuptools import setup

version_file = "checkipaconsistency/__version__.py"
verstrline = open(version_file, "rt").read()

match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", verstrline, re.M)
if match:
    version_string = match.group(1)
else:
    raise RuntimeError('Unable to find version string in %s.' % (version_file,))

setup(version=version_string, options = {'bdist_rpm':{'post_install': 'post_install_script', 'requires': 'python-pip, python-devel, openldap-devel'}})
