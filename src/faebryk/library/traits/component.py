# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod
from typing import Any

logger = logging.getLogger(__name__)

from faebryk.library.core import Footprint, NodeTrait


class has_type_description(NodeTrait):
    @abstractmethod
    def get_type_description(self) -> str:
        ...


class can_bridge(NodeTrait):
    def bridge(self, _in, out):
        _in.connect(self.get_in())
        out.connect(self.get_out())

    @abstractmethod
    def get_in(self) -> Any:
        ...

    @abstractmethod
    def get_out(self) -> Any:
        ...


class has_overriden_name(NodeTrait):
    @abstractmethod
    def get_name(self) -> str:
        ...


# TODO should this be a module trait or so?
class has_footprint(NodeTrait):
    @abstractmethod
    def get_footprint(self) -> Footprint:
        ...
