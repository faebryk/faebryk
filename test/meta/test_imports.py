# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from modulefinder import Module
from subprocess import CalledProcessError
import unittest
import logging

logger = logging.getLogger("test")

class TestImports(unittest.TestCase):
    def test_imports(self):
        import glob
        import subprocess

        folders = ["samples", "faebryk"]
        files = [file for i in folders for file in glob.glob("{}/**/*.py".format(i), recursive=True)]
        print(files)
        print("=======")
        for file in files:
            print(file)
            print("--------")
            try:
                imports = [x.strip() for x in subprocess.check_output(["grep", "import ", file]).splitlines()]
            except CalledProcessError:
                #TODO check if 1, then just nothing found
                continue

            for imp in imports:
                exec(imp)

