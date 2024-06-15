# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import asyncio
import datetime
import json
import logging
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
        if isinstance(module, F.Resistor):
            asyncio.run(self.db.find_resistor(module))
        elif isinstance(module, F.Capacitor):
            asyncio.run(self.db.find_capacitor(module))
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

    async def find_part_by_manufacturer_pn(self, partnumber: str, qty: int = 100):
        filter_query = Q(stock__gte=qty) & Q(mfr__icontains=partnumber)
        res = await Component.filter(filter_query).order_by("-basic")
        if len(res) < 1:
            raise PickError(
                f"Could not find exact match for PN {partnumber} with qty {qty}"
            )
        res = self._sort_results_by_basic_preferred_price(res, qty)[0]
        return f"C{res.lcsc}"

    async def get_manufacturer_from_id(self, manufacturer_id: int) -> str:
        return (await Manufacturers.get(id=manufacturer_id)).name

    async def find_resistor(self, cmp: F.Resistor, qty: int = 100):
        """
        Find a resistor part in the JLCPCB database that matches the parameters of the
        provided resistor
        """

        if not isinstance(cmp, F.Resistor):
            raise ValueError

        logger.info(
            f"Finding resistor for {cmp}, basic/preferred/cheapest with parameters: "
            f"{cmp.PARAMs.resistance=} and {cmp.PARAMs.rated_power=}"
        )

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
                transform_fn=lambda x: si_str_to_float(x),
            ),
            self.parameter_to_db_map(
                "rated_voltage",
                "Overload Voltage (Max)",
                transform_fn=lambda x: si_str_to_float(x),
            ),
        ]

        await self._filter_by_params_and_attach(cmp, resistors, mapping, qty)

    async def find_capacitor(self, cmp: F.Capacitor, qty: int = 100):
        """
        Find a capacitor part in the JLCPCB database that matches the parameters of the
        provided capacitor
        """

        if not isinstance(cmp, F.Capacitor):
            raise ValueError

        logger.info(
            f"Finding capacitor for {cmp}, basic/preferred/cheapest with parameters: "
            f"{cmp.PARAMs.capacitance=} and {cmp.PARAMs.rated_voltage=}"
        )

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

        logger.info(f"Found {len(capacitors)} capacitors")

        if len(capacitors) < 1:
            raise PickError("No parts found")

        capacitors = self._sort_results_by_basic_preferred_price(capacitors, qty)

        mapping = [
            self.parameter_to_db_map("capacitance", "Capacitance", "Tolerance"),
            self.parameter_to_db_map(
                "rated_voltage",
                "Voltage Rated",
                transform_fn=lambda x: si_str_to_float(x),
            ),
            self.parameter_to_db_map(
                "temperature_coefficient",
                "Temperature Coefficient",
                transform_fn=lambda x: F.Capacitor.TemperatureCoefficient[
                    x.replace("NP0", "C0G")
                ],
            ),
        ]

        await self._filter_by_params_and_attach(cmp, capacitors, mapping, qty)

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
                continue

            logger.info(
                f"Found part {c.lcsc:8} "
                f"Basic: {bool(c.basic)}, Preferred: {bool(c.preferred)}, "
                f"Price: ${self._get_unit_price_for_qty(c, 100):2.4f}, "
                f"{c.description:15},"
            )

            for name, value in zip([m.param_name for m in mapping], pm):
                module.PARAMs.__getattribute__(name).merge(value)

            F.has_defined_descriptive_properties.add_properties_to(
                module,
                {
                    DescriptiveProperties.partno: c.mfr,
                    DescriptiveProperties.manufacturer: await (
                        self.get_manufacturer_from_id(c.manufacturer_id)
                    ),
                    DescriptiveProperties.datasheet: c.datasheet,
                    "JLCPCB stock": str(c.stock),
                    "JLCPCB price": f"{self._get_unit_price_for_qty(c, qty):.4f}",
                    "JLCPCB description": c.description,
                    "JLCPCB Basic": str(bool(c.basic)),
                    "JLCPCB Preferred": str(bool(c.preferred)),
                },
            )

            module.add_trait(has_part_picked_defined(JLCPCB_Part(f"C{c.lcsc}")))
            attach_footprint(module, f"C{c.lcsc}", True)
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

        for pin, mif in pinmap.items():
            logger.info(f"Attaching pin {pin} to {mif}")
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
        Sort the results by basic, preferred, price and return the top qty results
        """
        results.sort(
            key=lambda x: (-x.basic, -x.preferred, self._get_unit_price_for_qty(x, qty))
        )
        return results

    def _component_satisfies_requirement(
        self,
        component: Component,
        attributes_key: str,
        requirement: Parameter,
        use_tolerance: bool = False,
        tolerance_key: str = "Tolerance",
        attr_fn: Callable[[str], Any] = lambda x: float(x),
    ) -> Parameter | None:

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
                value = self._db_component_to_parameter(
                    component.extra["attributes"][attributes_key],
                    component.extra["attributes"][tolerance_key],
                )
                if not isinstance(value, F.Range):
                    logger.error(
                        f"Could not parse component with {attributes_key} field "
                        "{component.extra['attributes'][attributes_key]}"
                    )
                    return None

                if isinstance(requirement, F.ANY):
                    return value

                if not isinstance(requirement, F.Range):
                    raise NotImplementedError
                return (
                    value
                    if requirement.contains(value.max)
                    and requirement.contains(value.min)
                    else None
                )
            else:
                field_val = attr_fn(component.extra["attributes"][attributes_key])
                if isinstance(requirement, F.Range):
                    return field_val if requirement.contains(field_val) else None
                elif isinstance(requirement, F.Constant):
                    return field_val if field_val == requirement.value else None
                else:
                    raise NotImplementedError
        except Exception:
            logger.debug(
                f"Could not parse component with {attributes_key} field "
                "{component.extra['attributes'][attributes_key]}, {e}"
            )
            return None
