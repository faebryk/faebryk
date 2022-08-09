# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest
import logging
import os

logger = logging.getLogger("test")


class TestImportSchematicKicad(unittest.TestCase):
    def test_sch_eq(self):
        with open(os.path.join(os.path.dirname(__file__), "../../../common/resources/test.kicad_sch"), "r") as f:
            test_sch = f.read() 

        from faebryk.importers.netlist.kicad.schematic_kicad import to_faebryk_t2_netlist

        t2 = to_faebryk_t2_netlist(test_sch)

        #import pprint
        #pprint.pprint(t2, indent=4)

        # TODO actually test for equality with handbuilt netlist




if __name__ == "__main__":
    unittest.main()
