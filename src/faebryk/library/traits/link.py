# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod

from faebryk.library.core import GraphInterface, LinkTrait

logger = logging.getLogger(__name__)


class can_determine_partner_by_single_end(LinkTrait):
    @abstractmethod
    def get_partner(self, other: GraphInterface) -> GraphInterface:
        ...
