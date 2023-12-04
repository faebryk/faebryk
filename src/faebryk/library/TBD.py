# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Parameter


class TBD(Parameter):
    def __init__(self) -> None:
        super().__init__()

    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, TBD):
            return True

        return False
