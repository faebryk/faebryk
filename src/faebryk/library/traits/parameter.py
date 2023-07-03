# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod

from faebryk.library.core import ParameterTrait

logger = logging.getLogger(__name__)


class is_representable_by_single_value(ParameterTrait):
    @abstractmethod
    def get_single_representing_value(self):
        ...
