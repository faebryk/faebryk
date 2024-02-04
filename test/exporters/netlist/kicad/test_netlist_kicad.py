# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import unittest

from faebryk.core.core import Module
from faebryk.core.graph import Graph
from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
from faebryk.exporters.netlist.netlist import make_t2_netlist_from_graph
from faebryk.library.can_attach_to_footprint_symmetrically import (
    can_attach_to_footprint_symmetrically,
)
from faebryk.library.Electrical import Electrical
from faebryk.library.has_defined_kicad_ref import has_defined_kicad_ref
from faebryk.library.has_kicad_footprint_equal_ifs_defined import (
    has_kicad_footprint_equal_ifs_defined,
)
from faebryk.library.has_overriden_name_defined import has_overriden_name_defined
from faebryk.library.has_simple_value_representation_defined import (
    has_simple_value_representation_defined,
)
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


# Netlists --------------------------------------------------------------------
def test_netlist_graph():
    from faebryk.core.core import Footprint

    # component definition
    gnd = Electrical()
    vcc = Electrical()
    resistor1 = Module()
    resistor2 = Module()

    # name
    resistor1.add_trait(has_defined_kicad_ref("R1"))
    resistor2.add_trait(has_defined_kicad_ref("R2"))
    resistor1.add_trait(has_overriden_name_defined("R1"))
    resistor2.add_trait(has_overriden_name_defined("R2"))

    class _RIFs(Module.IFS()):
        unnamed = times(2, Electrical)

    for r in [resistor1, resistor2]:
        # value
        r.add_trait(has_simple_value_representation_defined("R"))
        # interfaces
        r.IFs = _RIFs(r)
        # footprint
        fp = Footprint()
        fp.add_trait(
            has_kicad_footprint_equal_ifs_defined("Resistor_SMD:R_0805_2012Metric")
        )
        r.add_trait(can_attach_to_footprint_symmetrically()).attach(fp)

    assert isinstance(resistor1.IFs, _RIFs)
    assert isinstance(resistor2.IFs, _RIFs)
    resistor1.IFs.unnamed[0].connect(vcc)
    resistor1.IFs.unnamed[1].connect(gnd)
    resistor2.IFs.unnamed[0].connect(resistor1.IFs.unnamed[0])
    resistor2.IFs.unnamed[1].connect(resistor1.IFs.unnamed[1])

    # net naming
    net_wrappers = []
    for i in [gnd, vcc]:
        wrap = Module()
        wrap.IFs.to_wrap = i
        wrap.add_trait(has_defined_kicad_ref("+3V3" if i == vcc else "GND"))
        wrap.add_trait(has_overriden_name_defined("+3V3" if i == vcc else "GND"))
        wrap.add_trait(can_attach_to_footprint_symmetrically())
        net_wrappers.append(wrap)

    # Make netlist
    comps = [
        resistor1,
        resistor2,
        *net_wrappers,
    ]
    netlist = from_faebryk_t2_netlist(make_t2_netlist_from_graph(Graph(comps)))

    _, netlist_t2 = test_netlist_t2()
    success = netlist == netlist_t2
    if not success:
        logger.error("Graph != T2")
        logger.error("T2: %s", netlist_t2)
        logger.error("Graph: %s", netlist)

    return success, netlist


def test_netlist_t2():
    from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
    from faebryk.exporters.netlist.netlist import Component, Net, Vertex

    # t2_netlist = [(properties, vertices=[comp=(name, value, properties), pin)])]

    resistor1 = Component(
        name="R1",
        value="R",
        properties={
            "footprint": "Resistor_SMD:R_0805_2012Metric",
        },
    )

    resistor2 = Component(
        name="R2",
        value="R",
        properties={
            "footprint": "Resistor_SMD:R_0805_2012Metric",
        },
    )

    netlist = [
        Net(
            properties={
                "name": "GND",
            },
            vertices=[
                Vertex(
                    component=resistor1,
                    pin="2",
                ),
                Vertex(
                    component=resistor2,
                    pin="2",
                ),
            ],
        ),
        Net(
            properties={
                "name": "+3V3",
            },
            vertices=[
                Vertex(
                    component=resistor1,
                    pin="1",
                ),
                Vertex(
                    component=resistor2,
                    pin="1",
                ),
            ],
        ),
    ]
    logger.debug("T2 netlist:", netlist)

    kicad_net = from_faebryk_t2_netlist(netlist)
    kicad_net_manu = _test_netlist_manu()

    success = kicad_net == kicad_net_manu
    if not success:
        logger.error("T2 != Manu")
        logger.error(kicad_net_manu)

    return success, netlist


def _test_netlist_manu():
    import itertools

    import faebryk.libs.kicad.sexp as sexp
    from faebryk.exporters.netlist.kicad.netlist_kicad import (
        _defaulted_comp,
        _defaulted_netlist,
        _gen_net,
        _gen_node,
    )

    # Footprint pins are just referenced by number through netlist of symbol
    # We only need
    #   - components
    #       - ref
    #       - value (for silk)
    #       - footprint
    #       - tstamp (uuid gen)
    #   - nets
    #       - code (uuid gen)
    #       - name
    #       - nodes
    #           - ref (comp)
    #           - pin (of footprint)
    # Careful comps need distinct timestamps
    tstamp = itertools.count(1)

    resistor_comp = _defaulted_comp(
        ref="R1",
        value="R",
        footprint="Resistor_SMD:R_0805_2012Metric",
        tstamp=next(tstamp),
        fields=[],
        properties={},
    )
    resistor_comp2 = _defaulted_comp(
        ref="R2",
        value="R",
        footprint="Resistor_SMD:R_0805_2012Metric",
        tstamp=next(tstamp),
        fields=[],
        properties={},
    )

    device_nets = [
        _gen_net(
            code=1,
            name="+3V3",
            nodes=[
                _gen_node(
                    ref="R1",
                    pin="1",
                ),
                _gen_node(
                    ref="R2",
                    pin="1",
                ),
            ],
        ),
        _gen_net(
            code=2,
            name="GND",
            nodes=[
                _gen_node(
                    ref="R1",
                    pin="2",
                ),
                _gen_node(
                    ref="R2",
                    pin="2",
                ),
            ],
        ),
    ]

    netlist = _defaulted_netlist(
        components=[resistor_comp, resistor_comp2],
        nets=[*device_nets],
    )

    sexpnet = sexp.gensexp(netlist)

    return sexpnet


class TestNetlist(unittest.TestCase):
    def test_netlist(self):
        ok, _ = test_netlist_t2()
        self.assertTrue(ok)

        ok, _ = test_netlist_graph()
        self.assertTrue(ok)
