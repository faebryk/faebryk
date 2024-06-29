# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
"""

import logging
from pathlib import Path

import faebryk.library._F as F
import typer
from faebryk.core.core import Module
from faebryk.exporters.pcb.kicad.layout.font import FontLayout
from faebryk.exporters.pcb.kicad.layout.simple import SimpleLayout
from faebryk.library.has_pcb_layout_defined import has_pcb_layout_defined
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.has_pcb_position_defined import has_pcb_position_defined
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.experiments.buildutil import (
    tag_and_export_module_to_netlist,
)
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class LEDText(Module):
    def __init__(self, num_leds: int) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            power = F.ElectricPower()

        self.IFs = _IFs(self)

        class _NODES(Module.NODES()):
            leds = times(
                num_leds,
                F.PoweredLED,
            )

        self.NODEs = _NODES(self)

        for led in self.NODEs.leds:
            led.IFs.power.connect(self.IFs.power)
            # Parametrize
            led.NODEs.led.PARAMs.color.merge(F.LED.Color.YELLOW)
            #led.NODEs.led.PARAMs.brightness.merge(
            #    TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value.value
            #)


class App(Module):
    def __init__(self) -> None:
        super().__init__()

        led_layout = FontLayout(
            ttf=Path("Minecraftia-Regular.ttf"),
            text="F",
            char_dimensions=(5, 7),
            resolution=(1, 1),
        )

        class _NODES(Module.NODES()):
            leds = LEDText(led_layout.get_count())
            battery = F.Battery()

        self.NODEs = _NODES(self)

        self.NODEs.leds.IFs.power.connect(self.NODEs.battery.IFs.power)

        led_layout.apply(self.NODEs.leds)

        # Layout
        Point = has_pcb_position.Point
        L = has_pcb_position.layer_type

        layout = SimpleLayout(
            layouts=[
                SimpleLayout.SubLayout(
                    mod_type=LEDText,
                    position=Point((0, 0, 0, L.TOP_LAYER)),
                ),
                SimpleLayout.SubLayout(
                    mod_type=F.Battery,
                    position=Point((0, 30, 180, L.TOP_LAYER)),
                ),
            ]
        )
        self.add_trait(has_pcb_layout_defined(layout))
        self.add_trait(has_pcb_position_defined(Point((100, 100, 0, L.TOP_LAYER))))


def main():
    logger.info("Building app")
    app = App()

    logger.info("Export")
    tag_and_export_module_to_netlist(app, pcb_transform=True)


if __name__ == "__main__":
    setup_basic_logging()
    logger.info("Running experiment")

    typer.run(main)
