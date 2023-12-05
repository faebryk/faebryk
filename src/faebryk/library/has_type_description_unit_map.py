# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Sequence

from faebryk.core.core import Parameter
from faebryk.core.util import unit_map
from faebryk.library.Constant import Constant
from faebryk.library.has_type_description import has_type_description


class has_type_description_unit_map(has_type_description.impl()):
    def __init__(
        self,
        param: Parameter,
        units: Sequence[str],
        start: str | None = None,
        base: int = 1000,
    ) -> None:
        super().__init__()
        self.param = param
        self.args = (units, start, base)

    def get_type_description(self) -> str:
        param_const = self.param.get_most_narrow()
        assert isinstance(param_const, Constant)
        return unit_map(param_const.value, *self.args)

    def is_implemented(self):
        return isinstance(self.param.get_most_narrow(), Constant)
