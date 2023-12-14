# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Any, Generic, Protocol, TypeVar

from faebryk.core.core import Parameter
from faebryk.library.is_representable_by_single_value_defined import (
    is_representable_by_single_value_defined,
)
from faebryk.libs.exceptions import FaebrykException

X = TypeVar("X", bound="SupportsRangeOps")


class SupportsRangeOps(Protocol):
    def __add__(self, __value: X) -> X:
        ...

    def __sub__(self, __value: X) -> X:
        ...

    def __le__(self, __value: X) -> bool:
        ...

    def __lt__(self, __value: X) -> bool:
        ...

    def __ge__(self, __value: X) -> bool:
        ...


T = TypeVar("T", bound=SupportsRangeOps)


class Range(Generic[T], Parameter):
    def __init__(self, bound1: T, bound2: T) -> None:
        super().__init__()
        self.min = min((bound1, bound2))
        self.max = max((bound1, bound2))

    def pick(self, value_to_check: T):
        if not self.min <= value_to_check <= self.max:
            raise FaebrykException(
                f"Value not in range: {value_to_check} not in [{self.min},{self.max}]"
            )
        self.add_trait(is_representable_by_single_value_defined(value_to_check))

    def contains(self, value_to_check: T) -> bool:
        return self.min <= value_to_check <= self.max

    def as_tuple(self) -> tuple[T, T]:
        return (self.min, self.max)

    def as_center_tuple(self) -> tuple[T, T]:
        return (self.min + self.max) / 2, (self.max - self.min) / 2

    @classmethod
    def from_center(cls, center: T, delta: T, delta_r: T | None = None) -> "Range":
        if delta_r is None:
            delta_r = delta
        return cls(center - delta, center + delta_r)

    @classmethod
    def lower_bound(cls, lower) -> "Range":
        # TODO range should take params as bounds
        return cls(lower, 1 << 32)

    @classmethod
    def upper_bound(cls, upper) -> "Range":
        # TODO range should take params as bounds
        return cls(0, upper)

    def __str__(self) -> str:
        return super().__str__() + f"({self.min} -> {self.max})"

    def __repr__(self):
        return super().__repr__() + f"({self.min} -> {self.max})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Range):
            return False
        return self.min == other.min and self.max == other.max

    def __hash__(self) -> int:
        return hash((self.min, self.max))
