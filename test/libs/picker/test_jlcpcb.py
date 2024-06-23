# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import unittest

import faebryk.library._F as F
from faebryk.core.core import Parameter
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.picker.jlcpcb import JLCPCB
from faebryk.libs.picker.picker import DescriptiveProperties, has_part_picked

logger = logging.getLogger(__name__)


class TestPickerJlcpcb(unittest.TestCase):
    class TestResistorRequirements:
        def __init__(
            self,
            test_case: unittest.TestCase,
            r: F.Resistor,
            resistance: Parameter,
            rated_power: Parameter,
            rated_voltage: Parameter,
            footprint: list[tuple[str, int]],
        ):
            self.test_case = test_case
            self.r = r
            self.resistance = resistance
            self.rated_power = rated_power
            self.rated_voltage = rated_voltage
            self.footprint = footprint

            self.merge()

            self.test()

        def merge(self):
            self.r.PARAMs.resistance.merge(self.resistance)
            self.r.PARAMs.rated_power.merge(self.rated_power)
            self.r.PARAMs.rated_voltage.merge(self.rated_voltage)
            self.r.add_trait(F.has_footprint_requirement_defined(self.footprint))

        def test(self):
            try:
                JLCPCB(no_download_prompt=True).pick(self.r)
            except Exception as e:
                self.test_case.fail(f"Failed to pick part: {e}")

            self.test_case.assertTrue(self.r.has_trait(has_part_picked))

            self.test_case.assertTrue(self.r.has_trait(F.has_descriptive_properties))

            self.test_case.assertIn(
                DescriptiveProperties.partno,
                self.r.get_trait(F.has_descriptive_properties).get_properties(),
            )

            self.test_case.assertNotEqual(
                "",
                self.r.get_trait(F.has_descriptive_properties).get_properties()[
                    DescriptiveProperties.partno
                ],
            )

            self.test_case.assertTrue(self.r.has_trait(F.has_footprint))
            self.test_case.assertTrue(
                self.r.get_trait(F.has_footprint)
                .get_footprint()
                .has_trait(F.has_kicad_footprint)
            )
            self.test_case.assertTrue(
                self.footprint[0][1]
                == len(
                    self.r.get_trait(F.has_footprint)
                    .get_footprint()
                    .get_trait(F.has_kicad_footprint)
                    .get_pin_names()
                )
            )

            for p, req in zip(
                [
                    self.r.PARAMs.resistance,
                    self.r.PARAMs.rated_power,
                    self.r.PARAMs.rated_voltage,
                ],
                [self.resistance, self.rated_power, self.rated_voltage],
            ):
                req = req.get_most_narrow()
                p = p.get_most_narrow()
                if isinstance(req, F.Range):
                    self.test_case.assertTrue(req.contains(p))
                elif isinstance(req, F.Constant):
                    self.test_case.assertEqual(req, p)
                elif isinstance(req, F.Set):
                    self.test_case.assertTrue(p in req.params)

    def test_find_resistor(self):
        r1 = F.Resistor()
        r2 = F.Resistor()

        self.TestResistorRequirements(
            self,
            r1,
            F.Range.from_center(10e3, 1e3),
            F.Range.lower_bound(0.05),
            F.Range.lower_bound(25),
            [("0402", 2)],
        )

        self.TestResistorRequirements(
            self,
            r2,
            F.Range.from_center(69e3, 2e3),
            F.Range.lower_bound(0.1),
            F.Range.lower_bound(50),
            [("0603", 2)],
        )

    def test_find_capacitor(self):
        c1 = F.Capacitor()
        c2 = F.Capacitor()

        c1.PARAMs.capacitance.merge(F.Range.from_center(100e-9, 10e-9))
        c1.PARAMs.rated_voltage.merge(F.Range.lower_bound(25))
        c1.PARAMs.temperature_coefficient.merge(
            F.Range.lower_bound(F.Capacitor.TemperatureCoefficient.X7R)
        )

        c2.PARAMs.capacitance.merge(F.Range.from_center(47e-12, 4.7e-12))
        c2.PARAMs.rated_voltage.merge(F.Range.lower_bound(50))
        c2.PARAMs.temperature_coefficient.merge(
            F.Range.lower_bound(F.Capacitor.TemperatureCoefficient.C0G)
        )

    def test_find_inductor(self):
        l1 = F.Inductor()

        l1.PARAMs.inductance.merge(F.Range.from_center(4.7e-9, 0.47e-9))
        l1.PARAMs.rated_current.merge(F.Range.lower_bound(0.01))
        l1.PARAMs.dc_resistance.merge(F.Range.upper_bound(1))
        l1.PARAMs.self_resonant_frequency.merge(F.Range.lower_bound(100e6))
        l1.PARAMs.self_resonant_frequency.merge(F.ANY())

    def test_find_mosfet(self):
        q1 = F.MOSFET()

        q1.PARAMs.channel_type.merge(F.MOSFET.ChannelType.N_CHANNEL)
        q1.PARAMs.saturation_type.merge(F.MOSFET.SaturationType.ENHANCEMENT)
        q1.PARAMs.gate_source_threshold_voltage.merge(F.Range(0.4, 3))
        q1.PARAMs.max_drain_source_voltage.merge(F.Range.lower_bound(20))
        q1.PARAMs.max_continuous_drain_current.merge(F.Range.lower_bound(2))
        q1.PARAMs.on_resistance.merge(F.Range.upper_bound(0.1))
        q1.add_trait(
            F.has_footprint_requirement_defined(
                [("SOT-23", 3), ("SOT23", 3), ("SOT-23-3", 3)]
            )
        )

    def test_find_diode(self):
        d1 = F.Diode()

        d1.add_trait(F.has_footprint_requirement_defined([("SOD-123", 2)]))
        d1.PARAMs.forward_voltage.merge(F.Range.upper_bound(1.7))
        d1.PARAMs.reverse_working_voltage.merge(F.Range.lower_bound(20))
        d1.PARAMs.reverse_leakage_current.merge(F.Range.upper_bound(100e-6))
        d1.PARAMs.max_current.merge(F.Range.lower_bound(1))

    def test_find_tvs(self):
        d2 = F.TVS()

        d2.add_trait(F.has_footprint_requirement_defined([("SMB(DO-214AA)", 2)]))
        d2.PARAMs.forward_voltage.merge(F.ANY())
        d2.PARAMs.reverse_working_voltage.merge(F.Range.lower_bound(5))
        d2.PARAMs.reverse_leakage_current.merge(F.ANY())
        d2.PARAMs.max_current.merge(F.Range.lower_bound(10))
        d2.PARAMs.reverse_breakdown_voltage.merge(F.Range.upper_bound(8))


if __name__ == "__main__":
    setup_basic_logging()
    unittest.main()
