# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F

logger = logging.getLogger(__name__)


class has_pin_association_heuristic_lookup_table(
    F.has_pin_association_heuristic.impl()
):
    def __init__(
        self,
        mapping: dict[F.Electrical, list[str]],
        accept_prefix: bool,
        case_sensitive: bool,
        nc: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.mapping = mapping
        self.accept_prefix = accept_prefix
        self.case_sensitive = case_sensitive
        self.nc = nc or ["NC", "nc"]

    def get_pins(
        self,
        pins: list[tuple[str, str]],
    ) -> dict[str, F.Electrical]:
        """
        Get the pinmapping for a list of pins based on a lookup table.

        :param pins: A list of tuples with the pin number and name.
        :return: A dictionary with the pin name as key and the module interface as value
        """

        pinmap = {}
        for number, name in pins:
            if name in self.nc:
                continue
            match = None
            for mif, alt_names in self.mapping.items():
                for alt_name in alt_names:
                    if not self.case_sensitive:
                        alt_name = alt_name.lower()
                        name = name.lower()
                    if self.accept_prefix and name.endswith(alt_name):
                        match = (mif, alt_name)
                        break
                    elif name == alt_name:
                        match = (mif, alt_name)
                        break
            if not match:
                raise F.has_pin_association_heuristic.PinMatchException(
                    f"Could not find a match for pin {number} with name {name}"
                    f" in the mapping {self.mapping}"
                )
            pinmap[number] = match[0]
            logger.debug(
                f"Matched pin {number} with name {name} to {match[0]} with "
                f"alias {match[1]}"
            )
        return pinmap
