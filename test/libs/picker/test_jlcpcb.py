# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import unittest

import faebryk.library._F as F
from faebryk.core.core import Module, Parameter
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.picker.jlcpcb import JLCPCB
from faebryk.libs.picker.picker import DescriptiveProperties, has_part_picked

logger = logging.getLogger(__name__)


class TestPickerJlcpcb(unittest.TestCase):
    class TestRequirements:
        def __init__(
            self,
            test_case: unittest.TestCase,
            module: Module,
            requirements: dict[str, Parameter],
            footprint: list[tuple[str, int]],
        ):
            self.test_case = test_case
            self.module = module
            self.requirements = requirements
            self.footprint = footprint

            self.merge()

            self.test()

        def merge(self):
            for p, req in self.requirements.items():
                self.module.PARAMs.__dict__[p] = self.module.PARAMs.__getattribute__(
                    p
                ).merge(req)

            self.module.add_trait(F.has_footprint_requirement_defined(self.footprint))

        def test(self):
            try:
                JLCPCB(no_download_prompt=True).pick(self.module)
            except Exception as e:
                self.test_case.fail(f"Failed to pick part: {e}")

            self.test_case.assertTrue(self.module.has_trait(has_part_picked))

            # check part number
            self.test_case.assertTrue(
                self.module.has_trait(F.has_descriptive_properties)
            )
            self.test_case.assertIn(
                DescriptiveProperties.partno,
                self.module.get_trait(F.has_descriptive_properties).get_properties(),
            )
            self.test_case.assertNotEqual(
                "",
                self.module.get_trait(F.has_descriptive_properties).get_properties()[
                    DescriptiveProperties.partno
                ],
            )

            # check footprint
            self.test_case.assertTrue(self.module.has_trait(F.has_footprint))
            self.test_case.assertTrue(
                self.module.get_trait(F.has_footprint)
                .get_footprint()
                .has_trait(F.has_kicad_footprint)
            )
            # check pin count
            self.test_case.assertTrue(
                self.footprint[0][1]
                == len(
                    self.module.get_trait(F.has_footprint)
                    .get_footprint()
                    .get_trait(F.has_kicad_footprint)
                    .get_pin_names()
                )
            )

            for p, req in self.requirements.items():
                req = req.get_most_narrow()
                p = self.module.PARAMs.__getattribute__(p).get_most_narrow()
                if isinstance(req, F.Range):
                    self.test_case.assertTrue(req.contains(p))
                elif isinstance(req, F.Constant):
                    self.test_case.assertEqual(req, p)
                elif isinstance(req, F.Set):
                    self.test_case.assertTrue(p in req.params)

    def test_find_resistor(self):
        self.TestRequirements(
            self,
            F.Resistor(),
            requirements={
                "resistance": F.Range.from_center(10e3, 1e3),
                "rated_power": F.Range.lower_bound(0.05),
                "rated_voltage": F.Range.lower_bound(25),
            },
            footprint=[("0402", 2)],
        )

        self.TestRequirements(
            self,
            F.Resistor(),
            requirements={
                "resistance": F.Range.from_center(69e3, 2e3),
                "rated_power": F.Range.lower_bound(0.1),
                "rated_voltage": F.Range.lower_bound(50),
            },
            footprint=[("0603", 2)],
        )

    def test_find_capacitor(self):
        self.TestRequirements(
            self,
            F.Capacitor(),
            requirements={
                "capacitance": F.Range.from_center(100e-9, 10e-9),
                "rated_voltage": F.Range.lower_bound(25),
                "temperature_coefficient": F.Range.lower_bound(
                    F.Capacitor.TemperatureCoefficient.X7R
                ),
            },
            footprint=[("0603", 2)],
        )

        self.TestRequirements(
            self,
            F.Capacitor(),
            requirements={
                "capacitance": F.Range.from_center(47e-12, 4.7e-12),
                "rated_voltage": F.Range.lower_bound(50),
                "temperature_coefficient": F.Range.lower_bound(
                    F.Capacitor.TemperatureCoefficient.C0G
                ),
            },
            footprint=[("0402", 2)],
        )

    def test_find_inductor(self):
        self.TestRequirements(
            self,
            F.Inductor(),
            requirements={
                "inductance": F.Range.from_center(4.7e-9, 0.47e-9),
                "rated_current": F.Range.lower_bound(0.01),
                "dc_resistance": F.Range.upper_bound(1),
                "self_resonant_frequency": F.Range.lower_bound(100e6),
            },
            footprint=[("0603", 2)],
        )

    def test_find_mosfet(self):
        self.TestRequirements(
            self,
            F.MOSFET(),
            requirements={
                "channel_type": F.Constant(F.MOSFET.ChannelType.N_CHANNEL),
                "saturation_type": F.Constant(F.MOSFET.SaturationType.ENHANCEMENT),
                "gate_source_threshold_voltage": F.Range(0.4, 3),
                "max_drain_source_voltage": F.Range.lower_bound(20),
                "max_continuous_drain_current": F.Range.lower_bound(2),
                "on_resistance": F.Range.upper_bound(0.1),
            },
            footprint=[("SOT-23", 3)],
        )

    def test_find_diode(self):
        self.TestRequirements(
            self,
            F.Diode(),
            requirements={
                "forward_voltage": F.Range.upper_bound(1.7),
                "reverse_working_voltage": F.Range.lower_bound(20),
                "reverse_leakage_current": F.Range.upper_bound(100e-6),
                "max_current": F.Range.lower_bound(1),
            },
            footprint=[("SOD-123", 2)],
        )

    def test_find_tvs(self):
        self.TestRequirements(
            self,
            F.TVS(),
            requirements={
                "forward_voltage": F.ANY(),
                "reverse_working_voltage": F.Range.lower_bound(5),
                "reverse_leakage_current": F.ANY(),
                "max_current": F.Range.lower_bound(10),
                "reverse_breakdown_voltage": F.Range.upper_bound(8),
            },
            footprint=[("SMB(DO-214AA)", 2)],
        )

    def test_find_ldo(self):
        self.TestRequirements(
            self,
            F.LDO(),
            requirements={
                "output_voltage": F.Range.from_center(3.3, 0.1),
                "output_current": F.Range.lower_bound(0.1),
                "max_input_voltage": F.Range.lower_bound(5),
                "dropout_voltage": F.Range.upper_bound(1),
                "output_polarity": F.Constant(F.LDO.OutputPolarity.POSITIVE),
                "output_type": F.Constant(F.LDO.OutputType.FIXED),
                "psrr": F.ANY(),
            },
            footprint=[
                ("SOT-23", 3),
                ("SOT23", 3),
                ("SOT-23-3", 3),
                ("SOT-23-3L", 3),
            ],
        )


if __name__ == "__main__":
    setup_basic_logging()
    unittest.main()
