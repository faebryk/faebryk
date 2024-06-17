# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import asyncio
import datetime
import json
import logging
import math
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError

import faebryk.library._F as F
import wget
from easyeda2kicad.easyeda.easyeda_api import EasyedaApi
from easyeda2kicad.easyeda.easyeda_importer import (
    EasyedaSymbolImporter,
)
from faebryk.core.core import Module, Parameter
from faebryk.library.can_attach_to_footprint import can_attach_to_footprint
from faebryk.library.can_attach_to_footprint_symmetrically import (
    can_attach_to_footprint_symmetrically,
)
from faebryk.library.has_descriptive_properties import has_descriptive_properties
from faebryk.library.has_pin_association_heuristic import has_pin_association_heuristic
from faebryk.libs.e_series import E_SERIES_VALUES, e_series_intersect
from faebryk.libs.picker.lcsc import (
    LCSC_Part,
    attach_footprint,
)
from faebryk.libs.picker.picker import (
    DescriptiveProperties,
    PickerOption,
    PickError,
    Supplier,
    has_part_picked,
    has_part_picked_defined,
)
from faebryk.libs.util import float_to_si_str, si_str_to_float

# import asyncio
from tortoise import Tortoise
from tortoise.expressions import Q
from tortoise.fields import CharField, IntField, JSONField
from tortoise.models import Model

logger = logging.getLogger(__name__)

# TODO dont hardcode relative paths
BUILD_FOLDER = Path("./build")
LIB_FOLDER = Path("./src/kicad/libs")
MODEL_PATH: str | None = "${KIPRJMOD}/../libs/"


class JLCPCB(Supplier):
    def __init__(self) -> None:
        super().__init__()
        self.db = jlcpcb_db()

    def attach(self, module: Module, part: PickerOption):
        assert isinstance(part.part, JLCPCB_Part)
        attach_footprint(component=module, partno=part.part.partno)
        if part.info is not None:
            F.has_defined_descriptive_properties.add_properties_to(module, part.info)

    def pick(self, module: Module):
        if module.has_trait(has_part_picked):
            if isinstance(module.get_trait(has_part_picked).get_part(), JLCPCB_Part):
                lcsc_pn = module.get_trait(has_part_picked).get_part().partno
                asyncio.run(self.db.find_by_lcsc_pn(lcsc_pn))
            else:
                return
        if module.has_trait(has_descriptive_properties) and hasattr(
            module.get_trait(has_descriptive_properties).get_properties,
            DescriptiveProperties.partno,
        ):
            mfr_pn = module.get_trait(has_descriptive_properties).get_properties()[
                DescriptiveProperties.partno
            ]
            asyncio.run(self.db.find_by_manufacturer_pn(mfr_pn))
        elif isinstance(module, F.Resistor):
            asyncio.run(self.db.find_resistor(module))
        elif isinstance(module, F.Capacitor):
            asyncio.run(self.db.find_capacitor(module))
        elif isinstance(module, F.Inductor):
            asyncio.run(self.db.find_inductor(module))
        elif isinstance(module, F.MOSFET):
            asyncio.run(self.db.find_mosfet(module))
        else:
            return


class JLCPCB_Part(LCSC_Part):
    def __init__(self, partno: str) -> None:
        super().__init__(partno=partno)


class Category(Model):
    id = IntField(pk=True)
    category = CharField(max_length=255)
    subcategory = CharField(max_length=255)

    class Meta:
        table = "categories"


class Manufacturers(Model):
    id = IntField(pk=True)
    name = CharField(max_length=255)

    class Meta:
        table = "manufacturers"


class Component(Model):
    lcsc = IntField(pk=True)
    category_id = IntField()
    mfr = CharField(max_length=255)
    package = CharField(max_length=255)
    joints = IntField()
    manufacturer_id = IntField()
    basic = IntField()
    description = CharField(max_length=255)
    datasheet = CharField(max_length=255)
    stock = IntField()
    price = JSONField()
    last_update = IntField()
    extra = JSONField()
    flag = IntField()
    last_on_stock = IntField()
    preferred = IntField()

    class Meta:
        table = "components"


class jlcpcb_db:
    def __init__(self, db_path: Path = Path("jlcpcb_part_database")) -> None:
        self.results = []
        self.db_path = db_path
        self.connected = False
        asyncio.run(self._init_db())

    def __del__(self):
        if self.connected:
            asyncio.run(self._close_db())

    async def _init_db(self):
        self.download()

        await Tortoise.init(
            db_url=f"sqlite://{self.db_path}/cache.sqlite3",
            modules={
                "models": [__name__]
            },  # Use __name__ to refer to the current module
        )
        self.connected = True

    async def _close_db(self):
        await Tortoise.close_connections()
        self.connected = False

    def download(
        self,
        prompt_update_timediff: datetime.timedelta = datetime.timedelta(days=7),
    ):
        prompt_update = False
        db_file = self.db_path / Path("cache.sqlite3")
        zip_file = self.db_path / Path("cache.zip")

        if not self.db_path.is_dir():
            os.makedirs(self.db_path)

        if not db_file.is_file():
            print(f"No JLCPCB database file in {self.db_path}.")
            prompt_update = True
        elif (
            datetime.datetime.fromtimestamp(
                self.db_path.stat().st_mtime, tz=datetime.timezone.utc
            )
            < datetime.datetime.now(tz=datetime.timezone.utc) - prompt_update_timediff
        ):
            print(f"JLCPCB database file in {self.db_path} is outdated.")
            prompt_update = True

        if prompt_update:
            ans = input("Update JLCPCB database? [Y/n]:").lower()
            if ans == "y" or ans == "":
                wget.download(
                    "https://yaqwsx.github.io/jlcparts/data/cache.zip",
                    out=str(zip_file),
                )
                # TODO: use 7z from python? (py7zr) and auto calc number of files
                for i in range(1, 50):
                    try:
                        wget.download(
                            f"https://yaqwsx.github.io/jlcparts/data/cache.z{i:02d}",
                            out=str(self.db_path / Path(f"cache.z{i:02d}")),
                        )
                    except HTTPError:
                        break
                subprocess.run(["7z", "x", str(zip_file), f"-o{self.db_path}"])

    @dataclass
    class parameter_to_db_map:
        param_name: str
        attr_key: str
        attr_tolerance_key: str | None = None
        transform_fn: Callable[[str], Any] = lambda x: x

    async def find_by_lcsc_pn(self, partnumber: str, qty: int = 100):
        filter_query = Q(stock__gte=qty) & Q(id=partnumber.strip("C"))
        res = await Component.filter(filter_query).order_by("-basic")
        if len(res) != 1:
            raise PickError(
                f"Could not find exact match for LCSC PN {partnumber} with qty {qty}"
            )
        await self._attach_component_to_module(Module(), res[0], [], qty)

    async def find_by_manufacturer_pn(self, partnumber: str, qty: int = 100):
        filter_query = Q(stock__gte=qty) & Q(mfr__icontains=partnumber)
        res = await Component.filter(filter_query).order_by("-basic")
        if len(res) < 1:
            raise PickError(
                f"Could not find match for manufacturer PN {partnumber} with qty {qty}"
            )
        res = self._sort_results_by_basic_preferred_price(res, qty)[0]
        await self._attach_component_to_module(Module(), res, [], qty)

    async def get_manufacturer_from_id(self, manufacturer_id: int) -> str:
        return (await Manufacturers.get(id=manufacturer_id)).name

    async def find_resistor(self, cmp: F.Resistor, qty: int = 100):
        """
        Find a resistor part in the JLCPCB database that matches the parameters of the
        provided resistor
        """

        category_ids = await self._get_category_id(
            "Resistors", "Chip Resistor - Surface Mount"
        )

        value_query = Q()
        for r in e_series_intersect(
            cmp.PARAMs.resistance.get_most_narrow(), E_SERIES_VALUES.E_ALL
        ).params:
            assert isinstance(r, F.Constant)
            si_val = float_to_si_str(r.value, "Ω")
            value_query |= Q(description__contains=f" {si_val}")

        filter_query = (
            Q(category_id__in=category_ids)
            & Q(stock__gte=qty)
            & Q(joints=2)
            & value_query
        )

        resistors = await Component.filter(filter_query).order_by("-basic")

        if len(resistors) < 1:
            raise PickError("No parts found")

        resistors = self._sort_results_by_basic_preferred_price(resistors, qty)

        mapping = [
            self.parameter_to_db_map("resistance", "Resistance", "Tolerance"),
            self.parameter_to_db_map(
                "rated_power",
                "Power(Watts)",
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            self.parameter_to_db_map(
                "rated_voltage",
                "Overload Voltage (Max)",
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
        ]

        await self._filter_by_params_and_attach(cmp, resistors, mapping, qty)

    async def find_capacitor(self, cmp: F.Capacitor, qty: int = 100):
        """
        Find a capacitor part in the JLCPCB database that matches the parameters of the
        provided capacitor
        """

        category_ids = await self._get_category_id(
            "Capacitors", "Multilayer Ceramic Capacitors MLCC - SMD/SMT"
        )

        value_query = Q()
        for r in e_series_intersect(
            cmp.PARAMs.capacitance.get_most_narrow(), E_SERIES_VALUES.E_ALL
        ).params:
            assert isinstance(r, F.Constant)
            si_val = float_to_si_str(r.value, "F").replace("µ", "u")
            value_query |= Q(description__contains=f" {si_val}")

        filter_query = (
            Q(category_id__in=category_ids)
            & Q(stock__gte=qty)
            & Q(joints=2)
            & value_query
        )

        capacitors = await Component.filter(filter_query).order_by("-basic")

        logger.debug(f"Found {len(capacitors)} capacitors")

        if len(capacitors) < 1:
            raise PickError("No parts found")

        capacitors = self._sort_results_by_basic_preferred_price(capacitors, qty)

        mapping = [
            self.parameter_to_db_map("capacitance", "Capacitance", "Tolerance"),
            self.parameter_to_db_map(
                "rated_voltage",
                "Voltage Rated",
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            self.parameter_to_db_map(
                "temperature_coefficient",
                "Temperature Coefficient",
                transform_fn=lambda x: F.Constant(
                    F.Capacitor.TemperatureCoefficient[x.replace("NP0", "C0G")]
                ),
            ),
        ]

        await self._filter_by_params_and_attach(cmp, capacitors, mapping, qty)

    async def find_inductor(self, cmp: F.Inductor, qty: int = 100):
        """
        Find an inductor part in the JLCPCB database that matches the parameters of the
        provided inductor.

        Note: When the "self_resonant_frequency" parameter is not ANY, only inductors
        from the HF and SMD categories are used.
        """

        # Get Inductors (SMD), Power Inductors, TH Inductors, HF Inductors,
        # Adjustable Inductors. HF and Adjtable are basically empty. TH inductors do not
        # match the DC resistance (DCR) field. TODO: add support for TH inductors
        category_ids = await self._get_category_id("Inductors", "Inductors")

        value_query = Q()
        for r in e_series_intersect(
            cmp.PARAMs.inductance.get_most_narrow(), E_SERIES_VALUES.E_ALL
        ).params:
            assert isinstance(r, F.Constant)
            si_val = float_to_si_str(r.value, "H").replace("µ", "u")
            value_query |= Q(description__contains=f" {si_val}")

        filter_query = (
            Q(category_id__in=category_ids)
            & Q(stock__gte=qty)
            & Q(joints=2)
            & value_query
        )

        inductors = await Component.filter(filter_query).order_by("-basic")

        logger.debug(f"Found {len(inductors)} inductors")

        if len(inductors) < 1:
            raise PickError("No parts found")

        inductors = self._sort_results_by_basic_preferred_price(inductors, qty)

        mapping = [
            self.parameter_to_db_map("inductance", "Inductance", "Tolerance"),
            self.parameter_to_db_map(
                "rated_current",
                "Rated Current",
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            self.parameter_to_db_map(
                "dc_resistance",
                "DC Resistance (DCR)",
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            self.parameter_to_db_map(
                "self_resonant_frequency",
                "Frequency - Self Resonant",
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
        ]

        await self._filter_by_params_and_attach(cmp, inductors, mapping, qty)

    async def find_mosfet(self, cmp: F.MOSFET, qty: int = 100):
        """
        Find a MOSFET part in the JLCPCB database that matches the parameters of the
        provided MOSFET
        """

        category_ids = await self._get_category_id("", "MOSFET")

        footprint_query = Q()
        if cmp.has_trait(F.has_footprint_requirement):
            req = cmp.get_trait(F.has_footprint_requirement).get_footprint_requirement()
            for footprint, pin_count in req:
                footprint_query |= Q(description__icontains=footprint) & Q(
                    joints=pin_count
                )

        filter_query = (
            Q(category_id__in=category_ids) & Q(stock__gte=qty) & footprint_query
        )

        mosfets = await Component.filter(filter_query).order_by("-basic")

        if len(mosfets) < 1:
            raise PickError("No parts found")

        mosfets = self._sort_results_by_basic_preferred_price(mosfets, qty)

        def ChannelType_str_to_param(x: str) -> F.Constant[F.MOSFET.ChannelType]:
            if x in ["N Channel", "N-Channel"]:
                return F.Constant(F.MOSFET.ChannelType.N_CHANNEL)
            elif x in ["P Channel", "P-Channel"]:
                return F.Constant(F.MOSFET.ChannelType.P_CHANNEL)
            else:
                raise ValueError(f"Unknown MOSFET type: {x}")

        mapping = [
            self.parameter_to_db_map(
                "max_drain_source_voltage",
                "Drain Source Voltage (Vdss)",
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            self.parameter_to_db_map(
                "max_continuous_drain_current",
                "Continuous Drain Current (Id)",
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            self.parameter_to_db_map(
                "channel_type",
                "Type",
                transform_fn=lambda x: (ChannelType_str_to_param(x)),
            ),
            self.parameter_to_db_map(
                "gate_source_threshold_voltage",
                "Gate Threshold Voltage (Vgs(th)@Id)",
                transform_fn=lambda x: F.Constant(si_str_to_float(x.split("@")[0])),
            ),
            self.parameter_to_db_map(
                "on_resistance",
                "Drain Source On Resistance (RDS(on)@Vgs,Id)",
                transform_fn=lambda x: F.Constant(si_str_to_float(x.split("@")[0])),
            ),
        ]

        await self._filter_by_params_and_attach(cmp, mosfets, mapping, qty)

    async def _attach_component_to_module(
        self,
        module: Module,
        component: Component,
        mapping: list[parameter_to_db_map],
        qty: int = 100,
    ):
        F.has_defined_descriptive_properties.add_properties_to(
            module,
            {
                DescriptiveProperties.partno: component.mfr,
                DescriptiveProperties.manufacturer: await self.get_manufacturer_from_id(
                    component.manufacturer_id
                ),
                DescriptiveProperties.datasheet: component.datasheet,
                "JLCPCB stock": str(component.stock),
                "JLCPCB price": f"{self._get_unit_price_for_qty(component, qty):.4f}",
                "JLCPCB description": component.description,
                "JLCPCB Basic": str(bool(component.basic)),
                "JLCPCB Preferred": str(bool(component.preferred)),
            },
        )

        module.add_trait(has_part_picked_defined(JLCPCB_Part(f"C{component.lcsc}")))

        if not module.has_trait(can_attach_to_footprint):
            self.auto_pinmapping(module, f"C{component.lcsc}")

        attach_footprint(module, f"C{component.lcsc}", True)

    async def _filter_by_params_and_attach(
        self,
        module: Module,
        components: list[Component],
        mapping: list[parameter_to_db_map],
        qty: int = 100,
    ):
        for c in components:
            if not all(
                pm := [
                    self._component_satisfies_requirement(
                        c,
                        m.attr_key,
                        module.PARAMs.__getattribute__(m.param_name).get_most_narrow(),
                        use_tolerance=m.attr_tolerance_key is not None,
                        tolerance_key=m.attr_tolerance_key or "",
                        attr_fn=m.transform_fn,
                    )
                    for m in mapping
                ]
            ):
                for p, mapp in zip(pm, mapping):
                    if not p:
                        logger.debug(
                            f"Component {c.lcsc} does not satisfy requirement: "
                            f"{mapp.param_name}: requirement: "
                            f"{module.PARAMs.__getattribute__(mapp.param_name).get_most_narrow()}, "
                            f"value: {c.extra['attributes'][mapp.attr_key] if isinstance(c.extra, dict) and 'attributes' in c.extra and mapp.attr_key in c.extra['attributes'] else 'N/A'}"
                        )
                continue

            for name, value in zip([m.param_name for m in mapping], pm):
                module.PARAMs.__getattribute__(name).merge(value)

            logger.info(
                f"Found part {c.lcsc:8} "
                f"Basic: {bool(c.basic)}, Preferred: {bool(c.preferred)}, "
                f"Price: ${self._get_unit_price_for_qty(c, 100):2.4f}, "
                f"{c.description:15},"
            )

            try:
                await self._attach_component_to_module(module, c, mapping, qty)
            except Exception as e:
                logger.error(f"Could not attach component {c.lcsc}: {e}")
                continue

            return

    def auto_pinmapping(self, component: Module, partno: str):
        if component.has_trait(can_attach_to_footprint):
            logger.warning(f"Component {component} already has a pinmap, skipping")
            return

        if component.has_trait(can_attach_to_footprint_symmetrically):
            logger.warning(
                f"Component {component} is symmetrical, thus doesn't need a pimap"
            )
            return

        api = EasyedaApi()

        cache_base = BUILD_FOLDER / Path("cache/easyeda")
        cache_base.mkdir(parents=True, exist_ok=True)

        comp_path = cache_base.joinpath(partno)
        if not comp_path.exists():
            logger.info(f"Did not find component {partno} in cache, downloading...")
            cad_data = api.get_cad_data_of_component(lcsc_id=partno)
            serialized = json.dumps(cad_data)
            comp_path.write_text(serialized)

        data = json.loads(comp_path.read_text())

        logger.warning(
            f"No pinmap found for component {component}, attaching pins by name"
        )
        easyeda_symbol = EasyedaSymbolImporter(easyeda_cp_cad_data=data).get_symbol()
        pins = [
            (int(pin.settings.spice_pin_number), pin.name.text)
            for pin in easyeda_symbol.pins
        ]
        if component.has_trait(has_pin_association_heuristic):
            pinmap = component.get_trait(has_pin_association_heuristic).get_pins(pins)
        else:
            raise NotImplementedError

        component.add_trait(F.can_attach_to_footprint_via_pinmap(pinmap))

    async def _get_category_id(
        self, category: str = "", subcategory: str = ""
    ) -> list[dict[str, Any]]:
        filter_query = Q()
        if category != "":
            filter_query &= Q(category__icontains=category)
        if subcategory != "":
            filter_query &= Q(subcategory__icontains=subcategory)
        category_ids = await Category.filter(filter_query).values("id")
        if len(category_ids) < 1:
            raise PickError(
                f"Could not find a match for category {category} "
                f"and subcategory {subcategory}"
            )
        return [c["id"] for c in category_ids]

    def _db_field_to_parameter(self, field: str) -> Parameter:
        if "~" in field:
            values = field.split("~")
            values = [si_str_to_float(v) for v in values]
            assert len(values) == 2
            return F.Range(*values)
        try:
            return F.Constant(si_str_to_float(field))
        except Exception as e:
            logger.info(
                f"Could not convert field from database with value '{field}'"
                f"to parameter: {e}"
            )
            return F.TBD()

    def _db_component_to_parameter(
        self, value_field: str, tolerance_field: str
    ) -> Parameter:
        try:
            value = si_str_to_float(value_field)
        except Exception as e:
            logger.info(
                f"Could not convert component from database with value "
                f"'{value_field}' to parameter: {e}"
            )
            return F.TBD()

        try:
            if "ppm" in tolerance_field:
                tolerance = float(tolerance_field.strip("±ppm")) / 1e6
            elif "%~+" in tolerance_field:
                tolerances = tolerance_field.split("~")
                tolerances = [float(t.strip("%+-")) for t in tolerances]
                tolerance = max(tolerances) / 100
            elif "%" in tolerance_field:
                tolerance = float(tolerance_field.strip("%±")) / 100
            else:
                # absolute value in si units
                tolerance_value = si_str_to_float(tolerance_field.strip("±"))
                tolerance = str(tolerance_value / value)
                raise NotImplementedError
        except Exception as e:
            logger.info(
                f"Could not convert tolerance from string: {tolerance_field}, {e}"
            )
            return F.TBD()

        return F.Range(value - value * tolerance, value + value * tolerance)

    def _get_unit_price_for_qty(self, component: Component, qty: int) -> float:
        """
        Get the price for qty of the component
        """
        if qty < 1:
            raise ValueError("Quantity must be greater than 0")
        try:
            for p in component.price:
                if qty > p["qFrom"] or qty < p["qTo"]:
                    return float(p["price"])
        except Exception:
            pass
        return float("inf")

    def _sort_results_by_basic_preferred_price(
        self, results: list[Component], qty: int = 100
    ) -> list[Component]:
        """
        Sort the results by basic, then preferred, then unit price for qty
        """
        results.sort(
            key=lambda x: (-x.basic, -x.preferred, self._get_unit_price_for_qty(x, qty))
        )
        return results

    def _is_close_or_contains(
        self, requirement: Parameter, value: Parameter, rel_tol: float = 1e-6
    ) -> bool:
        if isinstance(requirement, F.ANY):
            return True
        if not (
            isinstance(requirement, (F.Constant, F.Range))
            and isinstance(value, (F.Constant, F.Range))
        ):
            raise NotImplementedError
        req_max = (
            requirement.max if isinstance(requirement, F.Range) else requirement.value
        )
        req_min = (
            requirement.min if isinstance(requirement, F.Range) else requirement.value
        )
        if not math.isinf(req_min):
            req_min -= req_min * rel_tol
        if not math.isinf(req_max):
            req_max += req_max * rel_tol
        req_tol = F.Range(req_min, req_max)

        return req_tol.contains(value)

    def _component_satisfies_requirement(
        self,
        component: Component,
        attributes_key: str,
        requirement: Parameter,
        use_tolerance: bool = False,
        tolerance_key: str = "Tolerance",
        attr_fn: Callable[[str], Any] = lambda x: float(x),
    ) -> Parameter | None:
        if isinstance(requirement, F.ANY):
            return F.ANY()

        assert isinstance(component.extra, dict)
        if (
            "attributes" not in component.extra
            or attributes_key not in component.extra["attributes"]
            or use_tolerance
            and (tolerance_key not in component.extra["attributes"])
        ):
            return None

        try:
            if use_tolerance:
                if not isinstance(requirement, F.Range):
                    raise NotImplementedError
                value = self._db_component_to_parameter(
                    component.extra["attributes"][attributes_key],
                    component.extra["attributes"][tolerance_key],
                )
                return value if self._is_close_or_contains(requirement, value) else None
            else:
                field_val = attr_fn(component.extra["attributes"][attributes_key])
                return (
                    field_val
                    if self._is_close_or_contains(requirement, field_val)
                    else None
                )
        except Exception as e:
            logger.debug(
                f"Could not parse component with '{attributes_key}' field "
                f"'{component.extra['attributes'][attributes_key]}', Error: '{e}'"
            )
            return None
