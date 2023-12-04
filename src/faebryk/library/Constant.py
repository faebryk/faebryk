# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import typing

from faebryk.core.core import Parameter
from faebryk.library.is_representable_by_single_value_defined import (
    is_representable_by_single_value_defined,
)


class Constant(Parameter):
    def __init__(self, value: typing.Any) -> None:
        super().__init__()
        self.value = value
        self.add_trait(is_representable_by_single_value_defined(self.value))

    def __repr__(self):
        return f"{type(self).__name__}({self.value!r})@{id(self):#x}"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Constant):
            return False

        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)
