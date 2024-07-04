# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging

import faebryk.library._F as F
import typer
from faebryk.core.core import Module
from faebryk.exporters.pcb.layout.extrude import LayoutExtrude
from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy
from faebryk.library.Electrical import Electrical
from faebryk.library.has_pcb_layout_defined import has_pcb_layout_defined
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.has_pcb_position_defined import has_pcb_position_defined
from faebryk.library.has_pcb_routing_strategy_greedy_direct_line import (
    has_pcb_routing_strategy_greedy_direct_line,
)
from faebryk.libs.experiments.buildutil import (
    tag_and_export_module_to_netlist,
)
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class ResistorArray(Module):
    def __init__(self, count: int):
        super().__init__()

        class _IFs(Module.IFS()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)

        class _NODES(Module.NODES()):
            resistors = times(count, F.Resistor)

        self.NODEs = _NODES(self)

        for resistor in self.NODEs.resistors:
            resistor.PARAMs.resistance.merge(F.Constant(1000))
            resistor.IFs.unnamed[0].connect(self.IFs.unnamed[0])
            resistor.IFs.unnamed[1].connect(self.IFs.unnamed[1])

        self.add_trait(
            has_pcb_layout_defined(
                LayoutTypeHierarchy(
                    layouts=[
                        LayoutTypeHierarchy.Level(
                            mod_type=F.Resistor,
                            layout=LayoutExtrude((0, 10)),
                        ),
                    ]
                )
            )
        )


class App(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODES(Module.NODES()):
            arrays = times(2, lambda: ResistorArray(4))

        self.NODEs = _NODES(self)

        self.NODEs.arrays[0].IFs.unnamed[1].connect(self.NODEs.arrays[1].IFs.unnamed[0])

        # Layout
        Point = has_pcb_position.Point
        L = has_pcb_position.layer_type

        layout = LayoutTypeHierarchy(
            layouts=[
                LayoutTypeHierarchy.Level(
                    mod_type=ResistorArray,
                    layout=LayoutExtrude((10, 0)),
                ),
            ]
        )
        self.add_trait(has_pcb_layout_defined(layout))
        self.add_trait(has_pcb_position_defined(Point((20, 20, 0, L.TOP_LAYER))))

        self.add_trait(
            has_pcb_routing_strategy_greedy_direct_line(
                has_pcb_routing_strategy_greedy_direct_line.Topology.STAR
            )
        )


def main():
    logger.info("Building app")
    app = App()

    logger.info("Export")
    tag_and_export_module_to_netlist(app, pcb_transform=True)


if __name__ == "__main__":
    setup_basic_logging()
    logger.info("Running experiment")

    typer.run(main)
