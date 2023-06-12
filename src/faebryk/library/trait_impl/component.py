# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod

logger = logging.getLogger(__name__)

from faebryk.library.core import Footprint, GraphInterface, LinkParent
from faebryk.library.library.interfaces import ModuleInterface
from faebryk.library.traits.component import (
    can_bridge,
    has_footprint,
    has_overriden_name,
    has_type_description,
)


class has_defined_type_description(has_type_description.impl()):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value

    def get_type_description(self) -> str:
        return self.value


class can_bridge_defined(can_bridge.impl()):
    def __init__(
        self,
        in_if: GraphInterface | ModuleInterface,
        out_if: GraphInterface | ModuleInterface,
    ) -> None:
        super().__init__()

        self.get_in = lambda: in_if
        self.get_out = lambda: out_if


class has_overriden_name_defined(has_overriden_name.impl()):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    def get_name(self):
        return self.name


class has_footprint_impl(has_footprint.impl()):
    # TODO
    class FootprintInterface(GraphInterface):
        ...

    @abstractmethod
    def __init__(self) -> None:
        super().__init__()

    def set_footprint(self, fp: Footprint):
        # fp_if = self.FootprintInterface()
        # comp_if = self.FootprintInterface()

        # self.get_obj().GIFs.footprint = fp_if
        # fp.GIFs.component = comp_if

        # fp_if.connect(comp_if)

        ## TODO: consider child vs direct
        self.get_obj().GIFs.children.connect(
            fp.GIFs.parent, LinkParent.curry("footprint")
        )

    def get_footprint(self) -> Footprint:
        # fp_if: has_footprint_impl.FootprintInterface = getattr(
        #    self.get_obj().GIFs, "footprint"
        # )

        # fp = (
        #    fp_if.get_trait(has_single_connection)
        #    .get_connection()
        #    .get_trait(can_determine_partner_by_single_end)
        #    .get_partner(fp_if)
        #    .node
        # )
        # assert isinstance(fp, Footprint)

        # return fp

        children = self.get_obj().GIFs.children.get_children()
        fps = [c for _, c in children if isinstance(c, Footprint)]
        assert len(fps) == 1
        return fps[0]


class has_defined_footprint(has_footprint_impl):
    def __init__(self, fp: Footprint) -> None:
        super().__init__()
        self.fp = fp

    def on_obj_set(self):
        self.set_footprint(self.fp)
