# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
import subprocess as sp
import tempfile
from pathlib import Path
from zipfile import ZipFile

logger = logging.getLogger(__name__)


def _check_kicad_cli() -> None:
    """Check if kicad-cli 8 is installed and of correct version"""
    try:
        sp.check_output("which kicad-cli", shell=True)
    except sp.CalledProcessError:
        raise Exception("kicad-cli is not installed")

    # check if kicad-cli is version 8+
    try:
        version = sp.check_output("kicad-cli --version", shell=True).decode("utf-8")
        if not int(version.split()[0]) >= 8:
            raise Exception(
                f"kicad-cli is not version 8.x.x or higher but version {version}"
            )
    except sp.CalledProcessError:
        raise Exception("Failed to check kicad-cli version")


def _check_parent_dir(file: Path, is_dir: bool = False) -> None:
    """Check if parent directory exists, create it if it doesn't"""
    if is_dir:
        if not file.exists():
            os.makedirs(file)
            return
    if not file.parent.exists():
        os.makedirs(file.parent)
        return


def export_step(pcb_file: Path, step_file: Path) -> None:
    """
    3D PCBA STEP file export using the kicad-cli
    """

    _check_kicad_cli()

    logger.info(f"Exporting step file to {step_file}")
    _check_parent_dir(step_file)

    try:
        sp.check_output(
            [
                "kicad-cli",
                "pcb",
                "export",
                "step",
                "--force",
                "--no-dnp",
                "--subst-models",
                "--output",
                f"{step_file.absolute()}",
                f"{pcb_file}",
            ],
            shell=False,
        )
    except sp.CalledProcessError:
        raise Exception("Failed to export step file")


def export_dxf(pcb_file: Path, dxf_file: Path) -> None:
    """
    PCB outline export using the kicad-cli
    """

    _check_kicad_cli()

    logger.info(f"Exporting dxf file to {dxf_file}")
    _check_parent_dir(dxf_file)

    try:
        try:
            sp.check_output(
                [
                    "kicad-cli",
                    "pcb",
                    "export",
                    "dxf",
                    "--exclude-refdes",
                    "--exclude-value",
                    "--output-units",
                    "mm",
                    "--layers",
                    "Edge.Cuts",
                    "--output",
                    f"{dxf_file}",
                    f"{pcb_file}",
                ],
                shell=False,
            )
        except sp.CalledProcessError:
            raise Exception("Failed to export dxf file")
    except sp.CalledProcessError:
        raise Exception("Failed to export dxf file")


def export_glb(pcb_file: Path, glb_file: Path) -> None:
    """
    3D PCBA GLB file export using the kicad-cli
    """

    _check_kicad_cli()

    logger.info(f"Exporting glb file to {glb_file}")
    _check_parent_dir(glb_file)

    try:
        sp.check_output(
            [
                "kicad-cli",
                "pcb",
                "export",
                "glb",
                "--force",
                "--include-tracks",
                "--include-zones",
                "--grid-origin",
                "--subst-models",
                "--no-dnp",
                "--output",
                f"{glb_file.absolute()}",
                f"{pcb_file}",
            ],
            shell=False,
        )
    except sp.CalledProcessError:
        raise Exception("Failed to export glb file")


def export_svg(pcb_file: Path, svg_file: Path, flip_board: bool = False) -> None:
    """
    2D PCBA SVG file export using the kicad-cli
    """

    _check_kicad_cli()

    logger.info(f"Exporting svg file to {svg_file}")
    _check_parent_dir(svg_file)

    try:
        sp.check_output(
            [
                "kicad-cli",
                "pcb",
                "export",
                "svg",
                "--layers",
                f"{'\"F.Cu,F.Paste,F.SilkS,F.Mask,Edge.Cuts\"' if not flip_board else '\"B.Cu,B.Paste,B.SilkS,B.Mask,Edge.Cuts\"'}",
                "--page-size-mode",
                "2"  # Fit PSB to page
                "--exclude-drawing-sheet",
                "--output",
                f"{svg_file}",
                f"{pcb_file}",
            ],
            shell=False,
        )
    except sp.CalledProcessError:
        raise Exception("Failed to export svg file")


def export_gerber(pcb_file: Path, gerber_zip_file: Path) -> None:
    """
    Gerber export using the kicad-cli
    """

    _check_kicad_cli()

    logger.info(f"Exporting gerber files to {gerber_zip_file}")
    gerber_dir = gerber_zip_file.parent
    _check_parent_dir(gerber_dir, is_dir=True)

    # Create a temporary folder to export the gerber and drill files to
    with tempfile.TemporaryDirectory(dir=gerber_dir) as temp_dir:
        try:
            sp.check_output(
                [
                    "kicad-cli",
                    "pcb",
                    "export",
                    "gerbers",
                    "--layers",
                    "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,F.CrtYd,B.CrtYd,F.Fab,B.Fab,Edge.Cuts",
                    "--output",
                    f"{temp_dir}",
                    f"{pcb_file}",
                ],
                shell=False,
            )
        except sp.CalledProcessError:
            raise Exception("Failed to export gerber files")

        try:
            sp.check_output(
                [
                    "kicad-cli",
                    "pcb",
                    "export",
                    "drill",
                    "--format",
                    "excellon",
                    "--excellon-separate-th",
                    "--generate-map",
                    "--map-format",
                    "gerberx2",
                    "--output",
                    f"{temp_dir}",
                    f"{pcb_file}",
                ],
                shell=False,
            )
        except sp.CalledProcessError:
            raise Exception("Failed to export drill files")

        # Zip the gerber files
        with ZipFile(gerber_zip_file, "w") as zipf:
            for file in Path(temp_dir).iterdir():
                if file.is_file():
                    zipf.write(file, arcname=file.name)


def export_pick_and_place(pcb_file: Path, pick_and_place_file: Path) -> None:
    """
    Pick and place export using the kicad-cli
    """

    _check_kicad_cli()

    logger.info(f"Exporting pick and place file to {pick_and_place_file}")
    _check_parent_dir(pick_and_place_file)

    try:
        sp.check_output(
            [
                "kicad-cli",
                "pcb",
                "export",
                "pos",
                "--side",
                "both",
                "--format",
                "csv",
                "--units",
                "mm",
                "--exclude-dnp",
                "--output",
                f"{pick_and_place_file}",
                f"{pcb_file}",
            ],
            shell=False,
        )
    except sp.CalledProcessError:
        raise Exception("Failed to export pick and place file")
