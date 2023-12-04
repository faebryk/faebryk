# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Iterable

from faebryk.core.core import Parameter


class Set(Parameter):
    def __init__(self, params: Iterable[Parameter]) -> None:
        super().__init__()
        self.params = Set.flatten(set(params))

        if not self.params:
            raise ValueError("Set must contain at least one parameter")

    @staticmethod
    def flatten(params: set[Parameter]) -> set[Parameter]:
        return set(p for p in params if not isinstance(p, Set)) | set(
            x for p in params if isinstance(p, Set) for x in Set.flatten(p.params)
        )

    def __str__(self) -> str:
        return f"{type(self).__name__}({str(self.params)})"

    def __repr__(self):
        return str(self)  # + "@" + hex(id(self))

    def __eq__(self, other) -> bool:
        if not isinstance(other, Set):
            return False

        return self.params == other.params

    def __hash__(self) -> int:
        return sum(hash(p) for p in self.params)
