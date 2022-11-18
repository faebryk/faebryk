# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from typing import List

from faebryk.library.core import Interface, Link


class LinkDirect(Link):
    def __init__(self, interfaces: List[Interface]) -> None:
        super().__init__()
        assert len(set(map(type, interfaces))) == 1
        self.interfaces = interfaces

    def get_connections(self) -> List[Interface]:
        return self.interfaces
