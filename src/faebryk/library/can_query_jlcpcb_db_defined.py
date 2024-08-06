# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Callable

from faebryk.core.core import Module
from faebryk.library.can_query_jlcpcb_db import can_query_jlcpcb_db


class can_query_jlcpcb_db_defined(can_query_jlcpcb_db.impl()):
    def __init__(self, query_fn: Callable[[Module, int], None]):
        super().__init__()
        self.query_fn = query_fn

    def get_picker(self) -> Callable[[Module, int], None]:
        return self.query_fn
