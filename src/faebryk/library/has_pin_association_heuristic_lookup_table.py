# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.has_pin_association_heuristic import has_pin_association_heuristic


class has_pin_association_heuristic_lookup_table(has_pin_association_heuristic.impl()):
    def __init__(
        self,
        mapping: dict[ModuleInterface, list[str]],
        accept_prefix: bool,
        case_sensitive: bool,
    ) -> None:
        super().__init__()
        self.mapping = mapping
        self.accept_prefix = accept_prefix
        self.case_sensitive = case_sensitive

    def get_pins(
        self,
        names: list[str],
    ) -> list[ModuleInterface]:
        mifs = []
        for n in names:
            for mif, alt_names in self.mapping.items():
                match = None
                for alt_name in alt_names:
                    if self.case_sensitive:
                        alt_name = alt_name.lower()
                        n = n.lower()
                    if self.accept_prefix and n.endswith(alt_name):
                        match = alt_name
                    elif n == match:
                        match = alt_name
                if not match:
                    raise ValueError(f"Could not find a match for pin with name {n}")
                mifs.append(match)
        return mifs
