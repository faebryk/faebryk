# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

from faebryk.core.core import ModuleInterface, ModuleInterfaceTrait, NodeTrait
from faebryk.libs.util import find


class has_esphome_config(NodeTrait):
    @abstractmethod
    def get_config(self) -> dict:
        ...


# TODO move
class has_esphome_config_defined(has_esphome_config.impl()):
    def __init__(self, config: dict):
        super().__init__()
        self._config = config

    def get_config(self) -> dict:
        return self._config


# TODO move
class is_esphome_bus(ModuleInterfaceTrait):
    ...

    @abstractmethod
    def get_bus_id(self) -> str:
        ...

    @staticmethod
    def find_connected_bus(bus: ModuleInterface):
        connected_mifs = bus.get_direct_connections()
        try:
            return find(connected_mifs, lambda mif: mif.has_trait(is_esphome_bus))
        except ValueError:
            raise Exception(f"No esphome bus connected to {bus}: {connected_mifs}")


class is_esphome_bus_defined(is_esphome_bus.impl()):
    def __init__(self, bus_id: str):
        super().__init__()
        self._bus_id = bus_id

    def get_bus_id(self) -> str:
        return self._bus_id
