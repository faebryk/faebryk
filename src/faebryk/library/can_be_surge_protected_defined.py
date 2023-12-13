# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.library.can_be_surge_protected import can_be_surge_protected
from faebryk.library.Electrical import Electrical
from faebryk.library.is_surge_protected import is_surge_protected
from faebryk.library.is_surge_protected_nodes import is_surge_protected_nodes
from faebryk.library.TVS import TVS

logger = logging.getLogger(__name__)


class can_be_surge_protected_defined(can_be_surge_protected.impl()):
    def __init__(self, low_potential: Electrical, *protect_if: Electrical) -> None:
        super().__init__()
        self.protect_if = protect_if
        self.low_potential = low_potential

    def protect(self):
        obj = self.get_obj()

        tvs = TVS()
        obj.NODEs.tvs = tvs
        for protect_if in self.protect_if:
            protect_if.connect_via(tvs, self.low_potential)

        obj.add_trait(is_surge_protected_nodes())
        return tvs

    def is_implemented(self):
        return not self.get_obj().has_trait(is_surge_protected)
