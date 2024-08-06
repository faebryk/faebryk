# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from typing import Callable

from faebryk.core.core import Module, ModuleTrait


class can_query_jlcpcb_db(ModuleTrait):
    @abstractmethod
    def get_picker(self) -> Callable[[Module, int], None]: ...
