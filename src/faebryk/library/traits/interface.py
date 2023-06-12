# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod

from faebryk.library.core import InterfaceTrait, Link

logger = logging.getLogger(__name__)


class has_single_connection(InterfaceTrait):
    @abstractmethod
    def get_connection(self) -> Link:
        ...


class has_single_connection_impl(has_single_connection.impl()):
    def get_connection(self):
        conns = self.get_obj().connections
        assert len(conns) == 1
        return conns[0]
