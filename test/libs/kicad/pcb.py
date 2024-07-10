# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest
from pathlib import Path

from faebryk.libs.kicad.pcbsexp import (
    C_kicad_footprint_file,
    C_kicad_netlist_file,
    C_kicad_pcb_file,
    Project,
)
from faebryk.libs.kicad.sexp_parser import JSON_File, SEXP_File
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.util import find

TEST_DIR = find(
    Path(__file__).parents,
    lambda p: p.name == "test" and (p / "common/resources").is_dir(),
)
TEST_FILES = TEST_DIR / "common/resources"
PRJFILE = TEST_FILES / "test.kicad_pro"
PCBFILE = TEST_FILES / "test.kicad_pcb"
FPFILE = TEST_FILES / "test.kicad_mod"
NETFILE = TEST_FILES / "test_e.net"


class TestPCB(unittest.TestCase):
    def test_project(self):
        p = Project.loads(PRJFILE)
        self.assertEqual(p.pcbnew.last_paths.netlist, "../../faebryk/faebryk.net")

    def test_parser(self):
        pcb = C_kicad_pcb_file.loads(PCBFILE)
        fp = C_kicad_footprint_file.loads(FPFILE)
        netlist = C_kicad_netlist_file.loads(NETFILE)

        self.assertEqual(
            [f.name for f in pcb.kicad_pcb.footprints],
            ["lcsc:LED0603-RD-YELLOW", "lcsc:R0402", "lcsc:BAT-TH_BS-02-A1AJ010"],
        )
        self.assertFalse(pcb.kicad_pcb.setup.pcbplotparams.usegerberextensions)

        padtype = pcb.C_kicad_pcb.C_pcb_footprint.C_pad.E_type
        self.assertEqual(
            [(p.name, p.type) for p in fp.footprint.pads],
            [
                ("", padtype.smd),
                ("", padtype.smd),
                ("1", padtype.smd),
                ("2", padtype.smd),
            ],
        )

        self.assertEqual(
            [(c.ref, c.value) for c in netlist.export.components.comps][:10],
            [
                ("C1", "10uF"),
                ("C2", "10uF"),
                ("C3", "10uF"),
                ("C4", "10uF"),
                ("C5", "22uF"),
                ("C6", "100nF"),
                ("C7", "100nF"),
                ("C8", "10uF"),
                ("C9", "100nF"),
                ("C10", "100nF"),
            ],
        )

    def test_dump_load_equality(self):
        def test_reload(path: Path, parser: type[SEXP_File | JSON_File]):
            loaded = parser.loads(path)
            dump = loaded.dumps()
            loaded_dump = parser.loads(dump)
            self.assertEqual(loaded, loaded_dump)

        for parser, file in [
            (C_kicad_pcb_file, PCBFILE),
            (C_kicad_footprint_file, FPFILE),
            (C_kicad_netlist_file, NETFILE),
            (Project, PRJFILE),
        ]:
            test_reload(file, parser)


if __name__ == "__main__":
    setup_basic_logging()
    unittest.main()
