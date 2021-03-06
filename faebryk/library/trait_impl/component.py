# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

logger = logging.getLogger("library")

from faebryk.library.core import (
    Footprint,
    Interface,
)
from faebryk.library.traits.component import *


class has_defined_type_description(has_type_description.impl()):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value

    def get_type_description(self) -> str:
        return self.value


class has_defined_footprint(has_footprint.impl()):
    def __init__(self, fp: Footprint) -> None:
        super().__init__()
        self.fp = fp

    def get_footprint(self) -> Footprint:
        return self.fp


class has_defined_footprint_pinmap(has_footprint_pinmap.impl()):
    def __init__(self, pin_map) -> None:
        super().__init__()
        self.pin_map = pin_map

    def get_pin_map(self):
        return self.pin_map


class has_symmetric_footprint_pinmap(has_footprint_pinmap.impl()):
    def get_pin_map(self):
        from faebryk.library.util import get_all_interfaces

        #TODO not sure if thats needed/desired
        # get all (nested) interfaces
        ifs = get_all_interfaces(self.get_obj().IFs.get_all())
        return {k + 1: v for k, v in enumerate(ifs)}


class can_bridge_defined(can_bridge.impl()):
    def __init__(self, in_if: Interface, out_if: Interface) -> None:
        super().__init__()

        self.get_in = lambda: in_if
        self.get_out = lambda: out_if
