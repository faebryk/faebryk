# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.library.Footprint import FootprintTrait, Pad


class has_equal_pins(FootprintTrait):
    @abstractmethod
    def get_pin_map(self) -> dict[Pad, str]: ...
