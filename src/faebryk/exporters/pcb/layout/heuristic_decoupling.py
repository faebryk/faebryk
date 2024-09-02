# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import IntEnum

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.layout.layout import Layout
from faebryk.libs.kicad.fileformats import C_kicad_pcb_file
from faebryk.libs.util import NotNone, find

logger = logging.getLogger(__name__)


KFootprint = C_kicad_pcb_file.C_kicad_pcb.C_pcb_footprint
KPad = KFootprint.C_pad

# TODO move all those helpers and make them more general and precise


class Side(IntEnum):
    Right = 0
    Bottom = 90
    Left = 180
    Top = 270

    def rot(self, angle=90):
        return type(self)((self + angle) % 360)

    def rot_vector(self, vec: tuple[float, float]):
        x, y = vec
        if self == Side.Right:
            return x, y
        elif self == Side.Bottom:
            return -y, x
        elif self == Side.Left:
            return -x, -y
        elif self == Side.Top:
            return y, -x
        else:
            assert False


def _get_pad_side(fp: KFootprint, pad: KPad) -> Side:
    # TODO this def does not work well

    # relative to fp center
    if pad.at.x < 0 and abs(pad.at.x) > abs(pad.at.y):
        pos_side = Side.Left
    elif pad.at.x > 0 and abs(pad.at.x) > abs(pad.at.y):
        pos_side = Side.Right
    elif pad.at.y < 0 and abs(pad.at.y) > abs(pad.at.x):
        pos_side = Side.Top
    else:
        pos_side = Side.Bottom

    # pad size as heuristic
    rot = (fp.at.r - pad.at.r) % 360
    assert pad.size.h is not None
    if pad.size.h > pad.size.w and rot not in (90, 270):
        pos_rot = {Side.Top, Side.Bottom}
    else:
        pos_rot = {Side.Right, Side.Left}

    if pos_side in pos_rot:
        return pos_side

    assert False


def _next_to_pad(
    fp: KFootprint, spad: KPad, dfp: KFootprint, dpad: KPad, distance: float
):
    def _add(v1, v2):
        return v1[0] + v2[0], v1[1] + v2[1]

    def _sub(v1, v2):
        return v1[0] - v2[0], v1[1] - v2[1]

    side = _get_pad_side(fp, spad)
    vec_pad_to_pad = side.rot_vector((distance, 0))
    vec_abs_to_pad_edge = _add(vec_pad_to_pad, (spad.at.x, spad.at.y))

    def _rel_edge_of_pad(size):
        if side == Side.Top:
            return 0, 0 + size.h / 2
        elif side == Side.Bottom:
            return 0, 0 - size.h / 2
        elif side == Side.Left:
            return 0 - size.w / 2, 0
        else:
            return 0 + size.w / 2, 0

    _vec = _add(vec_abs_to_pad_edge, _rel_edge_of_pad(spad.size))
    vec_abs_to_pad_edge = _add(_vec, _rel_edge_of_pad(dpad.size))

    vec_abs_to_fp_center = _sub(vec_abs_to_pad_edge, (dpad.at.x, dpad.at.y))

    # rotate fp to let pads face each other
    dside = _get_pad_side(dfp, dpad)
    fp_rot_rel_to_source = (dside.rot() - side.rot() - 180) % 360

    return (*vec_abs_to_fp_center, fp_rot_rel_to_source)


def place_next_to_pad(module: Module, pad: F.Pad):
    kfp, kpad = pad.get_trait(PCB_Transformer.has_linked_kicad_pad).get_pad()
    if len(kpad) != 1:
        raise NotImplementedError()
    kpad = kpad[0]

    nfp = module.get_trait(F.has_footprint).get_footprint()
    npad = find(
        nfp.get_children(direct_only=True, types=F.Pad),
        lambda p: p.net.is_connected_to(pad.net) is not None,
    )
    nkfp, nkpad = npad.get_trait(PCB_Transformer.has_linked_kicad_pad).get_pad()
    if len(nkpad) != 1:
        raise NotImplementedError()
    nkpad = nkpad[0]

    # TODO rot & layer not correct
    pos = _next_to_pad(kfp, kpad, nkfp, nkpad, distance=1)

    module.add_trait(
        F.has_pcb_position_defined_relative_to_parent(
            (
                *pos,
                F.has_pcb_position.layer_type.NONE,
            )
        )
    )


def place_next_to(
    parent: Module, intf: F.Electrical, child: Module, route: bool = False
):
    parent_fp = parent.get_trait(F.has_footprint).get_footprint()
    parent_pads = parent_fp.get_children(direct_only=True, types=F.Pad)
    parent_pad = find(parent_pads, lambda p: p.net.is_connected_to(intf) is not None)

    place_next_to_pad(child, parent_pad)

    if route:
        intf.add_trait(
            F.has_pcb_routing_strategy_greedy_direct_line(extra_mifs=[parent_pad.net])
        )


class LayoutHeuristicElectricalClosenessDecouplingCaps(Layout):
    def apply(self, *node: Node):
        from faebryk.core.util import get_parent_of_type, get_parent_with_trait

        # Remove nodes that have a position defined
        node = tuple(
            n
            for n in node
            if not n.has_trait(F.has_pcb_position) and n.has_trait(F.has_footprint)
        )

        for n in node:
            assert isinstance(n, F.Capacitor)
            power = NotNone(get_parent_of_type(n, F.ElectricPower))

            hv = find(
                n.get_children(direct_only=True, types=F.Electrical),
                lambda x: x.is_connected_to(power.hv) is not None,
            )

            parent = get_parent_with_trait(n, F.has_footprint, include_self=False)[0]
            assert isinstance(parent, Module)
            place_next_to(parent, hv, n, route=True)

    @staticmethod
    def find_module_candidates(node: Node):
        from faebryk.core.util import get_parent_of_type

        return node.get_children(
            direct_only=False,
            types=F.Capacitor,
            f_filter=lambda c: get_parent_of_type(c, F.ElectricPower) is not None,
        )

    @classmethod
    def add_to_all_suitable_modules(cls, node: Node):
        layout = cls()
        for c in cls.find_module_candidates(node):
            c.add_trait(F.has_pcb_layout_defined(layout))
