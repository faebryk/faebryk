# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Iterable

from faebryk.core.core import Module, Parameter
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.Electrical import Electrical
from faebryk.library.TBD import TBD
from faebryk.libs.util import NotNone

logger = logging.getLogger(__name__)


class Supplier(ABC):
    @abstractmethod
    def attach(self, component: Module, part: "Part", partid: "PartIdentifier" = None):
        ...


@dataclass
class Part:
    partno: str
    supplier: Supplier


@dataclass
class PartIdentifier:
    manufacturer: str
    partno: str
    datasheet: str


@dataclass
class PickerOption:
    part: Part
    params: dict[str, Parameter] | None = None
    filter: Callable[[Module], bool] | None = None
    pinmap: dict[str, Electrical] | None = None
    info: dict[str, str] | None = None
    partid: PartIdentifier | None = None


def pick_module_by_params(module: Module, options: Iterable[PickerOption]):
    params = {
        NotNone(p.get_parent())[1]: p.get_most_narrow() for p in module.PARAMs.get_all()
    }

    try:
        option = next(
            filter(
                lambda o: (not o.filter or o.filter(module))
                and all(
                    v.is_mergeable_with(params.get(k, TBD()))
                    for k, v in (o.params or {}).items()
                    if not k.startswith("_")
                ),
                options,
            )
        )
    except StopIteration:
        raise ValueError(
            f"Could not find part for {module=} with params {params} in {options=}"
        )

    if option.pinmap:
        module.add_trait(can_attach_to_footprint_via_pinmap(option.pinmap))

    option.part.supplier.attach(module, option.part, option.partid)

    # Merge params from footprint option
    for k, v in (option.params or {}).items():
        if k not in params:
            continue
        params[k].merge(v)

    logger.debug(f"Attached {option.part.partno} to {module}")
    return option
