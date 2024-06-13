# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import asyncio
import datetime
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError

import faebryk.library._F as F

# from library.e_series import E24, E48, E96, E192
import wget
from faebryk.core.core import Module, Parameter
from faebryk.library.has_defined_descriptive_properties import (
    has_defined_descriptive_properties,
)
from faebryk.libs.e_series import E192, e_series_in_range
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
        if not self.db.connected:
            asyncio.run(self.db.init_db())
        partno = None
        if isinstance(module, F.Resistor):
            partno = asyncio.run(self.db.find_resistor(module))
        elif isinstance(module, F.Capacitor):
            partno = asyncio.run(self.db.find_capacitor(module))
        else:
            return

        if partno is None:
            raise PickError("Could not find part")

        assert isinstance(partno, str)

        attach_footprint(module, partno, True)
        part = JLCPCB_Part(partno)

        module.add_trait(has_part_picked_defined(part))


class JLCPCB_Part(LCSC_Part):
    def __init__(self, partno: str) -> None:
        super().__init__(partno=partno)


class Category(Model):
    id = IntField(pk=True)
    category = CharField(max_length=255)
    subcategory = CharField(max_length=255)

    class Meta:
        table = "categories"


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

    async def init_db(self):
        self.download()

        await Tortoise.init(
            db_url=f"sqlite://{self.db_path}/cache.sqlite3",
            modules={
                "models": [__name__]
            },  # Use __name__ to refer to the current module
        )
        self.connected = True

    async def attach_part_details(
        self, cmp: Module, lcsc_pn: str, qty: int = 100
    ) -> None:
        res = Component.filter(
            lcsc=lcsc_pn.strip("C"),
        )
        if res.count() != 1:
            raise PickError(f"Could not find exact match for PN {lcsc_pn}")
        res = await res.first()
        assert isinstance(res, Component)

        cmp.add_trait(
            has_defined_descriptive_properties(
                properties={
                    DescriptiveProperties.partno: f"C{res.lcsc}",
                    DescriptiveProperties.manufacturer: res.mfr,
                    DescriptiveProperties.datasheet: res.datasheet,
                    "JLCPCB stock": str(res.stock),
                    "JLCPCB price": f"{self._get_unit_price_for_qty(res, qty):.4f}",
                    "JLCPCB description": res.description,
                    "JLCPCB Basic": str(bool(res.basic)),
                    "JLCPCB Preferred": str(bool(res.preferred)),
                }
            )
        )

    async def find_part_by_manufacturer_pn(self, partnumber: str, qty: int = 100):
        filter_query = Q(stock__gte=qty) & Q(mfr__icontains=partnumber)
        res = await Component.filter(filter_query).order_by("-basic")
        if len(res) < 1:
            raise PickError(
                f"Could not find exact match for PN {partnumber} with qty {qty}"
            )
        res = self._sort_results_by_basic_preferred_price(res, qty)[0]
        return f"C{res.lcsc}"

    async def find_resistor(self, cmp: F.Resistor, qty: int = 100):
        """
        Find a resistor part in the JLCPCB database that matches the parameters of the
        provided resistor
        """

        if not isinstance(cmp, F.Resistor):
            raise ValueError

        logger.info(
            f"Finding resistor for {cmp}, basic/preferred/cheapest with parameters: {cmp.PARAMs.resistance=} and {cmp.PARAMs.rated_power=}"
        )

        category_ids = await self._get_category_id(
            "Resistors", "Chip Resistor - Surface Mount"
        )
        category_query = Q(category_id__in=category_ids)

        value_query = Q()
        for r in e_series_in_range(cmp.PARAMs.resistance.get_most_narrow(), E192):
            si_val = float_to_si_str(r, "Ω")
            value_query |= Q(description__contains=f" {si_val}")

        filter_query = Q(stock__gte=qty) & category_query & value_query

        resistors = await Component.filter(filter_query).order_by("-basic")

        if len(resistors) < 1:
            raise PickError("No parts found")

        resistors = self._sort_results_by_basic_preferred_price(resistors, qty)

        for r in resistors:
            if not self._component_satisfies_requirement_with_tolerance(
                r,
                "Resistance",
                cmp.PARAMs.resistance.get_most_narrow(),
            ):
                continue

            if not self._component_satisfies_requirement(
                r,
                "Power(Watts)",
                cmp.PARAMs.rated_power.get_most_narrow(),
                lambda x: si_str_to_float(x),
            ):
                continue

            if not self._component_satisfies_requirement(
                r,
                "Overload Voltage (Max)",
                cmp.PARAMs.rated_voltage.get_most_narrow(),
                lambda x: si_str_to_float(x),
            ):
                continue

            logger.info(
                f"Found part {r.lcsc:8} "
                f"Basic: {bool(r.basic)}, Preferred: {bool(r.preferred)}, "
                f"Price: {self._get_unit_price_for_qty(r, 100):2.4f}, "
                f"{r.description:15},"
            )
            return f"C{r.lcsc}"

    async def find_capacitor(self, cmp: F.Capacitor, qty: int = 100):
        """
        Find a capacitor part in the JLCPCB database that matches the parameters of the
        provided capacitor
        """

        if not isinstance(cmp, F.Capacitor):
            raise ValueError

        logger.info(
            f"Finding capacitor for {cmp}, basic/preferred/cheapest with parameters: {cmp.PARAMs.capacitance=} and {cmp.PARAMs.rated_voltage=}"
        )

        category_ids = await self._get_category_id(
            "Capacitors", "Multilayer Ceramic Capacitors MLCC - SMD/SMT"
        )
        category_query = Q(category_id__in=category_ids)

        value_query = Q()
        for r in e_series_in_range(cmp.PARAMs.capacitance.get_most_narrow(), E192):
            si_val = float_to_si_str(r, "F").replace("µ", "u")
            value_query |= Q(description__contains=f" {si_val}")

        filter_query = Q(stock__gte=qty) & category_query & value_query

        capacitors = await Component.filter(filter_query).order_by("-basic")

        logger.info(f"Found {len(capacitors)} capacitors")

        if len(capacitors) < 1:
            raise PickError("No parts found")

        capacitors = self._sort_results_by_basic_preferred_price(capacitors, qty)

        for c in capacitors:
            if not self._component_satisfies_requirement_with_tolerance(
                c,
                "Capacitance",
                cmp.PARAMs.capacitance.get_most_narrow(),
            ):
                continue

            if not self._component_satisfies_requirement(
                c,
                "Voltage Rated",
                cmp.PARAMs.rated_voltage.get_most_narrow(),
                lambda x: si_str_to_float(x),
            ):
                continue

            if not self._component_satisfies_requirement(
                c,
                "Temperature Coefficient",
                cmp.PARAMs.temperature_coefficient.get_most_narrow(),
                lambda x: F.Capacitor.TemperatureCoefficient[x.replace("NP0", "C0G")],
            ):
                continue

            logger.info(
                f"Found part {c.lcsc:8} "
                f"Basic: {bool(c.basic)}, Preferred: {bool(c.preferred)}, "
                f"Price: {self._get_unit_price_for_qty(c, 100):2.4f}$, "
                f"{c.description:15},"
            )
            return f"C{c.lcsc}"

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
                f"Could not find a match for category {category} and subcategory {subcategory}"
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

    def _component_satisfies_requirement_with_tolerance(
        self,
        component: Component,
        attributes_key: str,
        requirement: Parameter,
        tolerance_key: str = "Tolerance",
    ) -> bool:
        if isinstance(requirement, F.ANY):
            return True

        if not isinstance(requirement, F.Range):
            raise ValueError(
                "Only range requirements for values with tolerances are allowed"
            )

        assert isinstance(component.extra, dict)
        if (
            "attributes" not in component.extra
            or attributes_key not in component.extra["attributes"]
            or tolerance_key not in component.extra["attributes"]
        ):
            return False

        try:
            value = self._db_component_to_parameter(
                component.extra["attributes"][attributes_key],
                component.extra["attributes"][tolerance_key],
            )
            if not isinstance(value, F.Range):
                logger.error(
                    f"Could not parse component with {attributes_key} field "
                    "{component.extra['attributes'][attributes_key]}"
                )
                return False
            return requirement.contains(value.max) and requirement.contains(value.min)
        except Exception:
            logger.debug(
                f"Could not parse component with {attributes_key} field "
                "{component.extra['attributes'][attributes_key]}, {e}"
            )
            return False

    def _component_satisfies_requirement(
        self,
        component: Component,
        attributes_key: str,
        requirement: Parameter,
        attr_fn: Callable[[str], Any] = lambda x: float(x),
    ) -> bool:
        if isinstance(requirement, F.ANY):
            return True

        assert isinstance(component.extra, dict)

        if (
            "attributes" not in component.extra
            or attributes_key not in component.extra["attributes"]
        ):
            return False

        if isinstance(requirement, F.Range):
            try:
                field_val = attr_fn(component.extra["attributes"][attributes_key])
                return requirement.contains(field_val)
            except Exception as e:
                logger.debug(
                    f"Could not parse component with {attributes_key} field "
                    f"{component.extra['attributes'][attributes_key]}, {e}"
                )
                return False
        elif isinstance(requirement, F.Constant):
            try:
                field_val = attr_fn(component.extra["attributes"][attributes_key])
                return field_val == requirement.value
            except Exception as e:
                logger.debug(
                    f"Could not parse component with {attributes_key} field "
                    f"{component.extra['attributes'][attributes_key]}, {e}"
                )
                return False
        else:
            raise NotImplementedError
