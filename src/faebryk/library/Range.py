# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import typing

from faebryk.core.core import Parameter
from faebryk.library.is_representable_by_single_value_defined import (
    is_representable_by_single_value_defined,
)
from faebryk.libs.exceptions import FaebrykException


class Range(Parameter):
    def __init__(self, value_min: typing.Any, value_max: typing.Any) -> None:
        super().__init__()
        self.min = value_min
        self.max = value_max

    def pick(self, value_to_check: typing.Any):
        if not self.min <= value_to_check <= self.max:
            raise FaebrykException(
                f"Value not in range: {value_to_check} not in [{self.min},{self.max}]"
            )
        self.add_trait(is_representable_by_single_value_defined(value_to_check))

    def contains(self, value_to_check: typing.Any) -> bool:
        return self.min <= value_to_check <= self.max

    @classmethod
    def from_center(cls, center: typing.Any, delta: typing.Any) -> "Range":
        return cls(center - delta, center + delta)

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.min} -> {self.max})"

    def __repr__(self):
        return str(self)  # + "@" + hex(id(self))

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, Range):
            return False
        return self.min == other.min and self.max == other.max

    def __hash__(self) -> int:
        return hash((self.min, self.max))
