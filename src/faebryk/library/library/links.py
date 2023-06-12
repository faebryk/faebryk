# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from typing import List

from faebryk.library.core import GraphInterface, Link
from faebryk.library.traits.link import can_determine_partner_by_single_end


class LinkDirect(Link):
    def __init__(self, interfaces: List[GraphInterface]) -> None:
        super().__init__()
        assert len(set(map(type, interfaces))) == 1
        self.interfaces = interfaces

        if len(interfaces) == 2:

            class _(can_determine_partner_by_single_end.impl()):
                def get_partner(_self, other: GraphInterface):
                    return [i for i in self.interfaces if i is not other][0]

            self.add_trait(_())

    def get_connections(self) -> List[GraphInterface]:
        return self.interfaces
