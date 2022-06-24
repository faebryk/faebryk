# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

logger = logging.getLogger("library")

from faebryk.library.core import (
    Component,
    ComponentTrait,
    Footprint,
    FootprintTrait,
    Interface,
    InterfaceTrait,
)


class has_type_description(ComponentTrait):
    def get_type_description(self) -> str:
        raise NotImplementedError(type(self))


class has_defined_type_description(has_type_description):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value

    def get_type_description(self) -> str:
        return self.value


class has_interfaces(ComponentTrait):
    def get_interfaces(self) -> list[Interface]:
        return self.get_obj().IFs.get_all()

    def set_interface_comp(self):
        for i in self.get_interfaces():
            i.set_component(self.get_obj())


class has_interfaces_list(has_interfaces):
    def __init__(self) -> None:
        assert False, "deprecated"

    # def get_interfaces(self) -> list[Interface]:
    #    return self.get_obj().IFs.unnamed


class has_defined_interfaces(has_interfaces):
    def __init__(self, interfaces: list[Interface]) -> None:
        super().__init__()
        self.interfaces = interfaces

    def get_interfaces(self) -> list[Interface]:
        from faebryk.library.util import get_all_interfaces

        return get_all_interfaces(self.interfaces)


class contructable_from_component(ComponentTrait):
    def from_comp(self, comp: Component):
        raise NotImplementedError()


class has_footprint(ComponentTrait):
    def get_footprint(self) -> FootprintTrait:
        raise NotImplementedError()


class has_defined_footprint(has_footprint):
    def __init__(self, fp: Footprint) -> None:
        super().__init__()
        self.fp = fp

    def get_footprint(self) -> Footprint:
        return self.fp


class has_footprint_pinmap(ComponentTrait):
    def get_pin_map(self):
        raise NotImplementedError()


class has_defined_footprint_pinmap(has_footprint_pinmap):
    def __init__(self, pin_map) -> None:
        super().__init__()
        self.pin_map = pin_map

    def get_pin_map(self):
        return self.pin_map


class has_symmetric_footprint_pinmap(has_footprint_pinmap):
    def get_pin_map(self):
        ifs = self.get_obj().get_trait(has_interfaces).get_interfaces()
        return {k + 1: v for k, v in enumerate(ifs)}


class can_bridge(ComponentTrait):
    def bridge(self, _in, out):
        _in.connect(self.get_in())
        out.connect(self.get_out())

    def get_in(self):
        raise NotImplementedError(type(self))

    def get_out(self):
        raise NotImplementedError(type(self))


class can_bridge_defined(can_bridge):
    def __init__(self, in_if: Interface, out_if: Interface) -> None:
        super().__init__()

        self.get_in = lambda: in_if
        self.get_out = lambda: out_if
