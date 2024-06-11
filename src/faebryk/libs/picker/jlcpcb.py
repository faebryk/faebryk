# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import asyncio
import datetime
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, TypedDict
from urllib.error import HTTPError

import faebryk.library._F as F

# from library.e_series import E24, E48, E96, E192
import wget
from faebryk.core.core import Module, Parameter
from faebryk.libs.e_series import E192, e_series_in_range
from faebryk.libs.picker.lcsc import (
    LCSC_Part,
    attach_footprint,
)
from faebryk.libs.picker.picker import (
    PickerOption,
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


# utils --------------------------------------------------------------------------------


class JLCPCB(Supplier):
    def __init__(self) -> None:
        super().__init__()
        self.db = jlcpcb_db()

    def attach(self, module: Module, part: PickerOption):
        assert isinstance(part.part, JLCPCB_Part)
        attach_footprint(component=module, partno=part.part.partno)
        if part.info is not None:
            F.has_defined_descriptive_properties.add_properties_to(module, part.info)

    # @staticmethod
    def pick(self, module: Module):
        if not self.db.connected:
            asyncio.run(self.db.init_db())
        partno = ""
        if isinstance(module, F.Resistor):
            partno = asyncio.run(self.db.find_resistor(module))
        elif isinstance(module, F.Capacitor):
            ...
            # partno = self.db.find_capacitor(module)
        else:
            return
        print(partno)
        exit()
        attach_footprint(module, partno, True)
        part = JLCPCB_Part(partno)

        module.add_trait(has_part_picked_defined(part))


class JLCPCB_Part(LCSC_Part):
    def __init__(self, partno: str) -> None:
        super().__init__(partno=partno)


class jlcpcb_part(TypedDict):
    lcsc_pn: str
    manufacturer_pn: str
    basic: int
    price: str
    extra: str
    description: str


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
            if "%" in tolerance_field:
                tolerance = float(tolerance_field.strip("%±")) / 100
            elif "~" in tolerance_field:
                tolerances = tolerance_field.split("~")
                tolerances = [float(t) for t in tolerances]
                tolerance = max(tolerances) / 100
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

    def get_part(self, lcsc_pn: str) -> jlcpcb_part:
        res = Component.filter(
            lcsc=lcsc_pn.strip("C"),
        )
        if res.count() != 1:
            raise LookupError(f"Could not find exact match for PN {lcsc_pn}")
        res = res.first()

        return {
            "lcsc_pn": res.lcsc,
            "manufacturer_pn": res.mfr,
            "basic": res.basic,
            "price": res.price,
            "extra": res.extra,
            "description": res.description,
        }

    def get_part_by_manufacturer_pn(self, partnumber: str, moq: int = 1):
        query = f"""
            SELECT lcsc
            FROM "main"."components"
            WHERE stock > {moq}
            AND mfr LIKE '%{partnumber}%'
            ORDER BY basic DESC, price ASC
            """
        res = self.cur.execute(query).fetchone()
        if res is None:
            raise LookupError(f"Could not find partnumber for query: {query}")
        return "C" + str(res[0])

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
            raise LookupError(
                f"Could not find a match for category {category} and subcategory {subcategory}"
            )
        return [c["id"] for c in category_ids]

    async def find_resistor(self, cmp: F.Resistor):
        category_ids = await self._get_category_id(
            "Resistors", "Chip Resistor - Surface Mount"
        )
        category_query = Q(category_id__in=category_ids)

        value_query = Q()
        for r in e_series_in_range(cmp.PARAMs.resistance.get_most_narrow(), E192):
            si_val = float_to_si_str(r, "Ω")
            logger.info(f"Filter: {r}, {si_val}")
            value_query |= Q(description__contains=f" {si_val}")
        filter_query = Q(category_query, value_query, join_type="AND")

        logger.info(f"Filter query: {filter_query}")

        resistors = await Component.filter(filter_query).order_by("-basic")

        logger.info(f"num results: {len(resistors)}")

        if not isinstance(cmp, F.Resistor):
            raise ValueError

        target = cmp.PARAMs.resistance.get_most_narrow()

        if not isinstance(target, F.Range):
            raise NotImplementedError(f"Parameter type {type(target)} not implemented")

        results = []
        for r in resistors:
            assert isinstance(r.extra, dict)
            if "attributes" not in r.extra:
                logger.debug(f"Part {r.lcsc} has no attributes ({r.extra})")
                continue
            attributes = r.extra["attributes"]
            if not ("Resistance" in attributes and "Tolerance" in attributes):
                continue
            value = self._db_component_to_parameter(
                attributes["Resistance"], attributes["Tolerance"]
            )
            if not isinstance(value, F.Range):
                continue
            if not target.contains(value.max) and target.contains(value.min):
                continue
            #if not value.is_more_specific_than(target):
            #   continue

            if "Power(Watts)" not in attributes:
                continue

            try:
                power = si_str_to_float(attributes["Power(Watts)"])
                assert isinstance(cmp.PARAMs.rated_power.get_most_narrow(), F.Range)
                if power >= cmp.PARAMs.rated_power.get_most_narrow().min:
                    results.append(r)
            except Exception as e:
                logger.debug(f"Could not parse power for part {r.lcsc}, {e}")
                continue

        for r in results:
            print(r.lcsc, r.mfr, r.basic, r.price[0]["price"], r.extra, r.description)

    def filter_results_by_extra_json_attributes(
        self, key: str, value: Parameter, attr_fn: Callable[[str], str] = lambda x: x
    ) -> None:
        filtered_results = []
        if isinstance(value, F.Constant):
            for _, part in enumerate(self.results):
                try:
                    extra_json = json.loads(part["extra"])
                    attributes = extra_json["attributes"]
                    field_val = attr_fn(attributes[key])
                    if field_val == value.value:
                        filtered_results.append(part)
                except Exception as e:
                    logger.debug(f"Could not parse part {part}, {e}")
        elif isinstance(value, F.Range):
            for _, part in enumerate(self.results):
                try:
                    extra_json = json.loads(part["extra"])
                    attributes = extra_json["attributes"]
                    field_val = attr_fn(attributes[key])
                    if value.contains(field_val):
                        filtered_results.append(part)
                except Exception as e:
                    logger.debug(f"Could not parse part {part}, {e}")
        elif isinstance(value, F.TBD):
            logger.warning(f"Skipping filter for key '{key}'', parameter type F.TBD.")
            return
        elif isinstance(value, F.ANY):
            return
        else:
            logger.error(
                f"Skipping filter for key '{key}'', parameter type {type(value)} unknown."
            )
            return
            # raise NotImplementedError

        logger.info(
            f"{len(filtered_results)} of {len(self.results)} left after filtering for key {key}"
        )
        self.results = filtered_results
