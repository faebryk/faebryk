# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Footprint, Module
from faebryk.core.util import get_connected_mifs, get_parent_of_type
from faebryk.library.Electrical import Electrical
from faebryk.library.has_type_description import has_type_description

logger = logging.getLogger(__name__)


class Net(Module):
    def __init__(self) -> None:
        super().__init__()

        class _IFs(super().IFS()):
            part_of = Electrical()

        self.IFs = _IFs(self)

        class _(has_type_description.impl()):
            def get_type_description(_self):
                from faebryk.exporters.netlist.graph import (
                    can_represent_kicad_footprint,
                )

                name = "-".join(
                    sorted(
                        (
                            t := fp.get_trait(can_represent_kicad_footprint)
                        ).get_name_and_value()[0]
                        + "-"
                        + t.get_pin_name(mif)
                        for mif, fp in self.get_fps().items()
                        if fp.has_trait(can_represent_kicad_footprint)
                    )
                )

                # kicad can't handle long net names
                if len(name) > 255:
                    name = name[:200] + "..." + name[-52:]

                return name

        self.add_trait(_())

    def get_fps(self):
        return {
            mif: fp
            for mif in self.get_connected_interfaces()
            if (fp := get_parent_of_type(mif, Footprint)) is not None
        }

    # TODO should this be here?
    def get_connected_interfaces(self):
        return {
            mif
            for mif in get_connected_mifs(self.IFs.part_of.GIFs.connected)
            if isinstance(mif, type(self.IFs.part_of))
        }
