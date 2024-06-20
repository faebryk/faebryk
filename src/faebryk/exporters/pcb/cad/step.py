# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
import re
import subprocess as sp
from pathlib import Path

logger = logging.getLogger(__name__)

"""
STEP file exporter using the kicad 8 cli


"""


def export_step(pcb_file: Path, path: Path):
    logger.info(f"Exporting step file to {path}")
    if not path.parent.exists():
        os.makedirs(path.parent)

    # check if kicad-cli 8 is installed
    try:
        sp.check_output("which kicad-cli", shell=True)
    except sp.CalledProcessError:
        raise Exception("kicad-cli is not installed")

    # check if kicad-cli is version 8
    try:
        version = sp.check_output("kicad-cli --version", shell=True).decode("utf-8")
        if not re.search(r"8\.\d+\.\d+", version):
            raise Exception(f"kicad-cli is not version 8.x.x but version {version}")
    except sp.CalledProcessError:
        raise Exception("Failed to check kicad-cli version")

    try:
        sp.check_output(
            f"kicad-cli pcb export step --force --no-dnp --subst-models --output {path} {pcb_file}",
            shell=True,
        )
    except sp.CalledProcessError:
        raise Exception("Failed to export step file")
