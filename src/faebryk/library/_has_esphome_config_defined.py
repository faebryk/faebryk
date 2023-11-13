# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

from faebryk.core.core import NodeTrait, ModuleInterfaceTrait


class has_esphome_config_defined(has_esphome_config.impl()):
    def __init__(self, config: dict):
        self._config = config

    def get_config(self) -> dict:
        return self._config


# TODO move
class is_esphome_bus(ModuleInterfaceTrait):
    ...
