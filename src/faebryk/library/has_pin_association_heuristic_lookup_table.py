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
        pins: list[tuple[int, str]],
    ) -> dict[str, ModuleInterface]:
        """
        Get the pinmapping for a list of pins based on a lookup table.

        :param pins: A list of tuples with the pin number and name.
        :return: A dictionary with the pin name as key and the module interface as value
        """

        pinmap = {}
        for number, name in pins:
            for mif, alt_names in self.mapping.items():
                match = None
                for alt_name in alt_names:
                    if self.case_sensitive:
                        alt_name = alt_name.lower()
                        name = name.lower()
                    if self.accept_prefix and name.endswith(alt_name):
                        match = alt_name
                    elif name == match:
                        match = alt_name
                if not match:
                    raise ValueError(
                        f"Could not find a match for pin {number} with name {name}"
                    )
                pinmap[name] = mif
        return pinmap
