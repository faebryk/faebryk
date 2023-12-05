# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from faebryk.core.graph import Graph
from faebryk.exporters.netlist.graph import attach_nets_and_kicad_info
from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
from faebryk.exporters.netlist.netlist import make_t2_netlist_from_graph

logger = logging.getLogger(__name__)


def write_netlist(graph: Graph, path: Path) -> bool:
    logger.info("Making T1")
    attach_nets_and_kicad_info(graph)
    logger.info("Making T2")
    t2 = make_t2_netlist_from_graph(graph)

    logger.info("Making Netlist")
    netlist = from_faebryk_t2_netlist(t2)

    if path.exists():
        old_netlist = path.read_text()
        # TODO this does not work!
        if old_netlist == netlist:
            logger.warning("Netlist did not change, not writing")
            return False
        backup_path = path.with_suffix(path.suffix + ".bak")
        logger.info(f"Backup old netlist at {backup_path}")
        backup_path.write_text(old_netlist)

    assert isinstance(netlist, str)
    logger.info("Writing Experiment netlist to {}".format(path.resolve()))
    path.write_text(netlist, encoding="utf-8")

    # TODO faebryk/kicad bug: net names cant be too long -> pcb file can't save

    return True
