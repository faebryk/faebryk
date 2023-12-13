# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import typing
from typing import Generic, TypeVar

from faebryk.core.core import Parameter

PV = TypeVar("PV")


class Operation(Generic[PV], Parameter[PV]):
    class OperationNotExecutable(Exception):
        ...

    def __init__(
        self,
        operands: typing.Sequence[Parameter[PV]],
        operation: typing.Callable[..., Parameter[PV]],
    ) -> None:
        super().__init__()
        self.operands = operands
        self.operation = operation

    def __repr__(self):
        return f"{type(self).__name__}({self.operands!r})@{id(self):#x}"

    def execute(self):
        try:
            return self.operation(*self.operands)
        except Exception as e:
            raise Operation.OperationNotExecutable from e
