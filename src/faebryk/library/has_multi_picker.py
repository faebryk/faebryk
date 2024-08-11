# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from abc import abstractmethod

from faebryk.core.core import Module
from faebryk.library.has_picker import has_picker
from faebryk.libs.picker.picker import PickError

logger = logging.getLogger(__name__)


class has_multi_picker(has_picker.impl()):
    def pick(self):
        for prio, picker in self.pickers:
            logger.debug(f"Trying picker {picker}")
            try:
                picker.pick(self.get_obj())
                return
            except PickError as e:
                logger.info(f"Picker {picker} failed: {e}")
        raise LookupError("All pickers failed")


    class Picker:
        @abstractmethod
        def pick(self, module: Module): ...

    def __init__(self) -> None:
        super().__init__()

        self.pickers: list[tuple[int, has_multi_picker.Picker]] = []

    def add_picker(self, prio: int, picker: Picker):
        self.pickers.append((prio, picker))
        self.pickers = sorted(self.pickers, key=lambda x: x[0])

    @classmethod
    def add_to_module(cls, module: Module, prio: int, picker: Picker):
        if not module.has_trait(has_picker):
            module.add_trait(cls())

        t = module.get_trait(has_picker)
        assert isinstance(t, has_multi_picker)
        t.add_picker(prio, picker)
