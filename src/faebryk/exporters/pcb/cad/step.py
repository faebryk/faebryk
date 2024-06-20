# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
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
    try:
        sp.check_output(
            f"kicad-cli pcb export step --force --no-dnp --subst-models --output {path} {pcb_file}",
            shell=True,
        )
    except sp.CalledProcessError:
        raise Exception("Failed to export step file")
