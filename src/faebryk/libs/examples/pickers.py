# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Example picker library. Used both for demonstration and as the dedicated example picker.
"""

import logging

import faebryk.library._F as F
from faebryk.core.core import Module
from faebryk.core.util import specialize_module
from faebryk.library._F import Constant, Range
from faebryk.libs.app.parameters import replace_tbd_with_any
from faebryk.libs.picker.lcsc import LCSC_Part
from faebryk.libs.picker.picker import (
    PickerOption,
    pick_module_by_params,
)

logger = logging.getLogger(__name__)


def pick_fuse(module: F.Fuse):
    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C914087"),
                params={
                    "fuse_type": Constant(F.Fuse.FuseType.RESETTABLE),
                    "response_type": Constant(F.Fuse.ResponseType.SLOW),
                    "trip_current": Constant(1),
                },
            ),
            PickerOption(
                part=LCSC_Part(partno="C914085"),
                params={
                    "fuse_type": Constant(F.Fuse.FuseType.RESETTABLE),
                    "response_type": Constant(F.Fuse.ResponseType.SLOW),
                    "trip_current": Constant(0.5),
                },
            ),
        ],
    )


def pick_mosfet(module: F.MOSFET):
    standard_pinmap = {
        "1": module.IFs.gate,
        "2": module.IFs.source,
        "3": module.IFs.drain,
    }
    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C20917"),
                params={
                    "channel_type": Constant(F.MOSFET.ChannelType.N_CHANNEL),
                },
                pinmap=standard_pinmap,
            ),
            PickerOption(
                part=LCSC_Part(partno="C15127"),
                params={
                    "channel_type": Constant(F.MOSFET.ChannelType.P_CHANNEL),
                },
                pinmap=standard_pinmap,
            ),
        ],
    )


def pick_capacitor(module: F.Capacitor):
    """
    Link a partnumber/footprint to a Capacitor

    Uses 0402 when possible
    """

    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C1525"),
                params={
                    "temperature_coefficient": Range(
                        F.Capacitor.TemperatureCoefficient.Y5V,
                        F.Capacitor.TemperatureCoefficient.X7R,
                    ),
                    "capacitance": Constant(100e-9),
                    "rated_voltage": Range(0, 16),
                },
            ),
            PickerOption(
                part=LCSC_Part(partno="C19702"),
                params={
                    "temperature_coefficient": Range(
                        F.Capacitor.TemperatureCoefficient.Y5V,
                        F.Capacitor.TemperatureCoefficient.X7R,
                    ),
                    "capacitance": Constant(10e-6),
                    "rated_voltage": Range(0, 10),
                },
            ),
        ],
    )


def pick_resistor(resistor: F.Resistor):
    """
    Link a partnumber/footprint to a Resistor

    Selects only 1% 0402 resistors
    """

    pick_module_by_params(
        resistor,
        [
            PickerOption(
                part=LCSC_Part(partno="C25111"),
                params={"resistance": Constant(40.2)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25076"),
                params={"resistance": Constant(100)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25087"),
                params={"resistance": Constant(200)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C11702"),
                params={"resistance": Constant(1e3)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25879"),
                params={"resistance": Constant(2.2e3)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25900"),
                params={"resistance": Constant(4.7e3)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25905"),
                params={"resistance": Constant(5.1e3)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25917"),
                params={"resistance": Constant(6.8e3)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25744"),
                params={"resistance": Constant(10e3)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25752"),
                params={"resistance": Constant(12e3)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25771"),
                params={"resistance": Constant(27e3)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25741"),
                params={"resistance": Constant(100e3)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25782"),
                params={"resistance": Constant(390e3)},
            ),
            PickerOption(
                part=LCSC_Part(partno="C25790"),
                params={"resistance": Constant(470e3)},
            ),
        ],
    )


def pick_led(module: F.LED):
    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C72043"),
                params={
                    "color": Constant(F.LED.Color.GREEN),
                    "max_brightness": Constant(285e-3),
                    "forward_voltage": Constant(3.7),
                    "max_current": Constant(100e-3),
                },
                pinmap={"1": module.IFs.cathode, "2": module.IFs.anode},
            ),
            PickerOption(
                part=LCSC_Part(partno="C72041"),
                params={
                    "color": Constant(F.LED.Color.BLUE),
                    "max_brightness": Constant(28.5e-3),
                    "forward_voltage": Constant(3.1),
                    "max_current": Constant(100e-3),
                },
                pinmap={"1": module.IFs.cathode, "2": module.IFs.anode},
            ),
            PickerOption(
                part=LCSC_Part(partno="C72038"),
                params={
                    "color": Constant(F.LED.Color.YELLOW),
                    "max_brightness": Constant(180e-3),
                    "forward_voltage": Constant(2.3),
                    "max_current": Constant(60e-3),
                },
                pinmap={"1": module.IFs.cathode, "2": module.IFs.anode},
            ),
        ],
    )


def pick_tvs(module: F.TVS):
    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C85402"),
                params={
                    "reverse_working_voltage": Constant(5),
                },
                pinmap={
                    "1": module.IFs.cathode,
                    "2": module.IFs.anode,
                },
            ),
        ],
    )


def pick_battery(module: F.Battery):
    if not isinstance(module, F.ButtonCell):
        bcell = F.ButtonCell()
        replace_tbd_with_any(bcell, recursive=False)
        specialize_module(module, bcell)
        return

    pick_module_by_params(
        module,
        [
            PickerOption(
                part=LCSC_Part(partno="C5239862"),
                params={
                    "voltage": Constant(3),
                    "capacity": Range.from_center(225, 50),
                    "material": Constant(F.ButtonCell.Material.Lithium),
                    "size": Constant(F.ButtonCell.Size.N_2032),
                    "shape": Constant(F.ButtonCell.Shape.Round),
                },
                pinmap={
                    "1": module.IFs.power.IFs.lv,
                    "2": module.IFs.power.IFs.hv,
                },
            ),
        ],
    )


def pick_parts_for_examples(module: Module):
    # switch over types
    if isinstance(module, F.Resistor):
        pick_resistor(module)
    elif isinstance(module, F.LED):
        pick_led(module)
    elif isinstance(module, F.Fuse):
        pick_fuse(module)
    elif isinstance(module, F.TVS):
        pick_tvs(module)
    elif isinstance(module, F.MOSFET):
        pick_mosfet(module)
    elif isinstance(module, F.Capacitor):
        pick_capacitor(module)
    elif isinstance(module, F.Battery):
        pick_battery(module)
