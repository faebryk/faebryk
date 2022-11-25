# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

logger = logging.getLogger("library")

from faebryk.library.core import Interface
from faebryk.library.library.interfaces import InterfaceNode
from faebryk.library.traits.component import (
    can_bridge,
    has_overriden_name,
    has_type_description,
)


class has_defined_type_description(has_type_description.impl()):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value

    def get_type_description(self) -> str:
        return self.value


class can_bridge_defined(can_bridge.impl()):
    def __init__(
        self, in_if: Interface | InterfaceNode, out_if: Interface | InterfaceNode
    ) -> None:
        super().__init__()

        self.get_in = lambda: in_if
        self.get_out = lambda: out_if


class has_overriden_name_defined(has_overriden_name.impl()):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    def get_name(self):
        return self.name
