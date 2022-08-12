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
        from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist

        t2 = to_faebryk_t2_netlist(test_sch)

        print("-"*80)
        import pprint
        pprint.pprint(t2, indent=4)
        
        netlist = from_faebryk_t2_netlist(t2)
        print("-"*80)
        import pprint
        pprint.pprint(netlist, indent=4)

        from pathlib import Path
        path = Path("./build/faebryk.net")
        logger.info("Writing Experiment netlist to {}".format(path.absolute()))
        path.write_text(netlist)

        # TODO actually test for equality with handbuilt netlist






if __name__ == "__main__":
    unittest.main()
