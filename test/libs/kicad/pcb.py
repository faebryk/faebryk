# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest
from pathlib import Path

import faebryk.libs.examples.buildutil as B
import typer
from faebryk.libs.kicad.pcbsexp import (
    C_kicad_footprint_file,
    C_kicad_netlist_file,
    C_kicad_pcb_file,
    Project,
)
from faebryk.libs.logging import setup_basic_logging
from rich.traceback import install

EXAMPLE_FILES = Path(B.__file__).parent / "resources/example"
PRJFILE = EXAMPLE_FILES / "example.kicad_pro"
# PCBFILE = EXAMPLE_FILES / "example.kicad_pcb"
PCBFILE = Path("build/kicad/source/example.kicad_pcb")
FPFILE = Path(
    "/usr/share/kicad/footprints/LED_SMD.pretty/LED_0201_0603Metric.kicad_mod"
)
NETFILE = Path(".local/test.net")


class TestPCB(unittest.TestCase):
    def test_project(self):
        p = Project.load(PRJFILE)
        self.assertEqual(p.pcbnew.last_paths.netlist, "../../faebryk/faebryk.net")

    def test_parser(self):
        install(
            width=500,
            extra_lines=3,
            theme=None,
            word_wrap=True,
            show_locals=True,
            locals_max_length=10,
            locals_max_string=1000,
            locals_max_depth=3,
            locals_hide_dunder=True,
            locals_hide_sunder=True,
            locals_overflow="fold",
            indent_guides=True,
            suppress=(),
            max_frames=10,
        )

        # from faebryk.libs.kicad.sexp_parser import logger
        # import logging
        # logger.setLevel(logging.DEBUG)

        out = C_kicad_pcb_file.loads(PCBFILE)

        print(out.kicad_pcb.layers[0])
        print([f.name for f in out.kicad_pcb.footprints])

        out = C_kicad_footprint_file.loads(FPFILE)
        print([(p.name, p.type) for p in out.footprint.pads])

        out = C_kicad_netlist_file.loads(NETFILE)
        print([(c.ref, c.value) for c in out.export.components.comps][:10])


if __name__ == "__main__":
    setup_basic_logging()
    # unittest.main()
    typer.run(TestPCB().test_parser)
