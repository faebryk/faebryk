# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.library.is_surge_protected import is_surge_protected
from faebryk.library.TVS import TVS

logger = logging.getLogger(__name__)


class is_surge_protected_nodes(is_surge_protected.impl()):
    def __init__(self) -> None:
        super().__init__()
        assert hasattr(self.get_obj().NODEs, "tvs")

    def get_tvs(self) -> TVS:
        return self.get_obj().NODEs.tvs
