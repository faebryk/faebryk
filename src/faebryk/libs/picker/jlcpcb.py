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
from faebryk.libs.picker.lcsc import (
    LCSC_Part,
    attach_footprint,
)
from faebryk.libs.picker.picker import (
    PickerOption,
    Supplier,
    has_part_picked_defined,
)
from faebryk.libs.util import si_str_to_float

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


def _jlcpcb_db_extra_parse_tolerance(tolerance_str: str, cmp_value: Parameter) -> str:
    """
    Parse the tolerance field from the JLCPCB database and return it as a string
    """
    try:
        if "%" in tolerance_str:
            tolerance = float(tolerance_str.strip("%±")) / 100
            return str(tolerance)
        elif "~" in tolerance_str:
            tolerances = tolerance_str.split("~")
            tolerances = [float(t) for t in tolerances]
            tolerance = max(tolerances) / 100
            return str(tolerance)
        else:
            # absolute value in si units
            tolerance_value = si_str_to_float(tolerance_str.strip("±"))
            if isinstance(cmp_value, F.Constant):
                return str(tolerance_value / cmp_value.value)
            elif isinstance(cmp_value, F.Range):
                return str(tolerance_value / cmp_value.max)
            raise NotImplementedError
    except Exception as e:
        logger.info(f"Could not convert tolerance from string: {tolerance_str}, {e}")
        return "inf"


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


def jlcpcb_download_db(
    jlcpcb_db_path: Path,
    prompt_update_timediff: datetime.timedelta = datetime.timedelta(days=7),
):
    prompt_update = False
    db_file = jlcpcb_db_path / Path("cache.sqlite3")
    zip_file = jlcpcb_db_path / Path("cache.zip")

    if not jlcpcb_db_path.is_dir():
        os.makedirs(jlcpcb_db_path)

    if not db_file.is_file():
        print(f"No JLCPCB database file in {jlcpcb_db_path}.")
        prompt_update = True
    elif (
        datetime.datetime.fromtimestamp(
            jlcpcb_db_path.stat().st_mtime, tz=datetime.timezone.utc
        )
        < datetime.datetime.now(tz=datetime.timezone.utc) - prompt_update_timediff
    ):
        print(f"JLCPCB database file in {jlcpcb_db_path} is outdated.")
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
                        out=str(jlcpcb_db_path / Path(f"cache.z{i:02d}")),
                    )
                except HTTPError:
                    break
            subprocess.run(["7z", "x", str(zip_file), f"-o{jlcpcb_db_path}"])


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

    async def init_db(self):
        jlcpcb_download_db(self.db_path)

        await Tortoise.init(
            db_url=f"sqlite://{self.db_path}/cache.sqlite3",
            modules={
                "models": [__name__]
            },  # Use __name__ to refer to the current module
        )
        self.connected = True

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

    async def get_category_id(
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

    def build_query(self, key: str, p: Parameter) -> Q:
        filter_dict = {}
        if isinstance(p, F.Constant):
            filter_dict[key] = p.value
            return Q(**filter_dict)
        elif isinstance(p, F.Range):
            filter_dict[key + "__gte"] = p.min
            filter_dict[key + "__lte"] = p.max
            return Q(**filter_dict)
        elif isinstance(p, F.TBD):
            logger.warning(f"Skipping filter for key '{key}'', parameter type F.TBD.")
            return Q()
        elif isinstance(p, F.ANY):
            return Q()
        else:
            raise NotImplementedError

    async def find_resistor(self, cmp: F.Resistor):
        category_ids = await self.get_category_id(
            "Resistors", "Chip Resistor - Surface Mount"
        )
        filter_query = Q(category_id__in=category_ids)
        filter_query &= self.build_query(
            "attributes__Resistance", cmp.PARAMs.resistance
        )
        filter_query &= self.build_query("attributes__Power", cmp.PARAMs.rated_power)

        results = await Component.filter(filter_query).order_by("-basic", "price")

        results = [
            r
            for r in results
            if _jlcpcb_db_extra_parse_tolerance(
                r.extra["attributes"]["Tolerance"], cmp.PARAMs.resistance
            )
        ]

        filter_query &= self.build_query("attributes__Tolerance", cmp.PARAMs.tolerance)

    async def query_category(
        self,
        category: str = "",
        subcategory: str = "",
    ) -> list[jlcpcb_part]:
        category_ids = await self.get_category_id(category, subcategory)
        res = await Component.filter(
            category_id__in=category_ids,
            extra__contains=[
                {"attributes__Resistance": value_to_find},
                {"attributes__Tolerance": tolerance_to_find},
            ],
            # extra__contains={"Tolerance": tolerance_to_find}
        ).first()

        category_query = f"(category_id = {category_id[0]}"
        for id in category_id[1:]:
            category_query += f" OR category_id = {id}"
        category_query += ")"
        query = f"""
            SELECT lcsc, mfr, basic, price, extra, description
            FROM "main"."components"
            WHERE {category_query}
            AND {query}
            """
        res = self.cur.execute(query).fetchall()
        if len(res) == 0:
            raise LookupError(f"Could not find any parts in category {category_id}")

        res = Component.filter(
            category_id=category_id,
        ).order_by("-basic", "price")
        if res.count() != 1:
            raise LookupError(f"Could not find exact match for PN {lcsc_pn}")
        res = res.first()
        parts = []
        for r in res:
            parts.append(
                {
                    "lcsc_pn": r[0],
                    "manufacturer_pn": r[1],
                    "basic": r[2],
                    "price": r[3],
                    "extra": r[4],
                    "description": r[5],
                }
            )
        self.results = parts
        return parts

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
                    part_val = si_str_to_float(field_val)
                    if part_val == value.value:
                        filtered_results.append(part)
                except Exception as e:
                    logger.debug(f"Could not parse part {part}, {e}")
        elif isinstance(value, F.Range):
            for _, part in enumerate(self.results):
                try:
                    extra_json = json.loads(part["extra"])
                    attributes = extra_json["attributes"]
                    field_val = attr_fn(attributes[key])
                    part_val = si_str_to_float(field_val)
                    if part_val > value.min and part_val < value.max:
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
