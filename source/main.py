#!/bin/env python

# Copyright (c) 2021 ITENG
# SPDX-License-Identifier: MIT
import sys

from sexp.sexp import gensexp
from sexp.test.sexptest import test_sexp


def main(argc, argv):
    print("faebryk dev v0.0")

    test_sexp()




if __name__ == "__main__":
    main(len(sys.argv), sys.argv)