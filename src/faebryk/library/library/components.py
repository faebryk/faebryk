# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import List
from faebryk.library.library.electronic.base.nand import NAND

from faebryk.library.trait_impl.component import (
    has_defined_footprint,
    has_defined_type_description,
    has_symmetric_footprint_pinmap,
)
from faebryk.library.traits.component import (
    contructable_from_component,
    has_footprint_pinmap,
)
from faebryk.library.traits.interface import contructable_from_interface_list
from faebryk.libs.util import consume_iterator


from faebryk.library.core import Component, ComponentTrait
from faebryk.library.library.interfaces import Electrical, Power
from faebryk.library.util import times

logger = logging.getLogger("library")


class PJ398SM(Component):
    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("Connector"))

    def _setup_interfaces(self):
        class _IFs(Component.InterfacesCls()):
            tip = Electrical()
            sleeve = Electrical()
            switch = Electrical()

        self.IFs = _IFs(self)


class CD4011(Component):
    class constructable_from_nands(ComponentTrait):
        def from_nands(self, nands: List[NAND]):
            raise NotImplementedError

    def _setup_traits(self):
        class _constructable_from_component(contructable_from_component.impl()):
            @staticmethod
            def from_comp(comp: Component) -> CD4011:
                c = CD4011.__new__(CD4011)
                c._init_from_comp(comp)
                return c

        class _constructable_from_nands(self.constructable_from_nands.impl()):
            @staticmethod
            def from_nands(nands: list[NAND]) -> CD4011:
                c = CD4011.__new__(CD4011)
                c._init_from_nands(nands)
                return c

        self.add_trait(_constructable_from_component())
        self.add_trait(_constructable_from_nands())
        self.add_trait(has_defined_type_description("cd4011"))

    def _setup_nands(self):
        class _CMPs(Component.ComponentsCls()):
            nands = times(4, lambda: NAND(input_cnt=2))

        self.CMPs = _CMPs(self)

        for n in self.CMPs.nands:
            n.add_trait(has_symmetric_footprint_pinmap())

    def _setup_interfaces(self):
        nand_inout_interfaces = [
            i for n in self.CMPs.nands for i in [n.IFs.output, *n.IFs.inputs]
        ]

        class _IFs(Component.InterfacesCls()):
            power = Power()
            in_outs = times(len(nand_inout_interfaces), Electrical)

        self.IFs = _IFs(self)

    def _setup_internal_connections(self):
        self.connection_map = {}

        it = iter(self.IFs.in_outs)
        for n in self.CMPs.nands:
            n.IFs.power.connect(self.IFs.power)
            target = next(it)
            target.connect(n.IFs.output)
            self.connection_map[n.IFs.output] = target

            for i in n.IFs.inputs:
                target = next(it)
                target.connect(i)
                self.connection_map[i] = target

        # TODO
        # assert(len(self.interfaces) == 14)

    def __new__(cls):
        self = super().__new__(cls)

        CD4011._setup_traits(self)
        return self

    def __init__(self):
        super().__init__()

        # setup
        self._setup_nands()
        self._setup_interfaces()
        self._setup_internal_connections()

    def _init_from_comp(self, comp: Component):
        super().__init__()

        # checks
        interfaces = comp.IFs.get_all()
        assert len(interfaces) == len(self.IFs.get_all())
        assert len([i for i in interfaces if type(i) is not Electrical]) == 0

        it = iter(interfaces)

        # setup
        self.IFs.power = (
            Power().get_trait(contructable_from_interface_list).from_interfaces(it)
        )
        self._setup_nands()
        self.IFs.in_outs = list(
            consume_iterator(
                Electrical()
                .get_trait(contructable_from_interface_list)
                .from_interfaces,
                it,
            )
        )
        self._setup_internal_connections()

    def _init_from_nands(self, nands: list[NAND]):
        super().__init__()

        # checks
        assert len(nands) <= 4
        cd_nands = list(nands)
        cd_nands += times(4 - len(cd_nands), lambda: NAND(input_cnt=2))

        for nand in cd_nands:
            assert len(nand.IFs.inputs) == 2

        # setup
        self.CMPs.nands = cd_nands
        self._setup_interfaces()
        self._setup_internal_connections()


class TI_CD4011BE(CD4011):
    def __init__(self):
        super().__init__()

    def __new__(cls):
        self = super().__new__(cls)

        TI_CD4011BE._setup_traits(self)
        return self

    def _setup_traits(self):
        from faebryk.library.library.footprints import DIP

        self.add_trait(
            has_defined_footprint(DIP(pin_cnt=14, spacing_mm=7.62, long_pads=False))
        )

        class _has_footprint_pinmap(has_footprint_pinmap.impl()):
            def get_pin_map(self):
                component = self.get_obj()
                return {
                    7: component.IFs.power.IFs.lv,
                    14: component.IFs.power.IFs.hv,
                    3: component.connection_map[component.CMPs.nands[0].IFs.output],
                    4: component.connection_map[component.CMPs.nands[1].IFs.output],
                    11: component.connection_map[component.CMPs.nands[2].IFs.output],
                    10: component.connection_map[component.CMPs.nands[3].IFs.output],
                    1: component.connection_map[component.CMPs.nands[0].IFs.inputs[0]],
                    2: component.connection_map[component.CMPs.nands[0].IFs.inputs[1]],
                    5: component.connection_map[component.CMPs.nands[1].IFs.inputs[0]],
                    6: component.connection_map[component.CMPs.nands[1].IFs.inputs[1]],
                    12: component.connection_map[component.CMPs.nands[2].IFs.inputs[0]],
                    13: component.connection_map[component.CMPs.nands[2].IFs.inputs[1]],
                    9: component.connection_map[component.CMPs.nands[3].IFs.inputs[0]],
                    8: component.connection_map[component.CMPs.nands[3].IFs.inputs[1]],
                }

        self.add_trait(_has_footprint_pinmap())
