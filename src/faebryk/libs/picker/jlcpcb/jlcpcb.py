# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import asyncio
import datetime
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Self, Sequence, TypeVar
from urllib.error import HTTPError

import faebryk.library._F as F
import wget
from easyeda2kicad.easyeda.easyeda_api import EasyedaApi
from easyeda2kicad.easyeda.easyeda_importer import (
    EasyedaSymbolImporter,
)
from faebryk.core.core import Module, Parameter
from faebryk.libs.e_series import E_SERIES_VALUES, e_series_intersect
from faebryk.libs.picker.lcsc import (
    LCSC_Part,
    attach_footprint,
)
from faebryk.libs.picker.picker import (
    DescriptiveProperties,
    PickError,
    has_part_picked_defined,
)
from faebryk.libs.units import float_to_si_str, si_str_to_float

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


class JLCPCB_Part(LCSC_Part):
    def __init__(self, partno: str) -> None:
        super().__init__(partno=partno)


@dataclass
class MappingParameterDB:
    param_name: str
    attr_keys: list[str]
    attr_tolerance_key: str | None = None
    transform_fn: Callable[[str], Parameter] | None = None


def auto_pinmapping(component: Module, partno: str) -> dict[str, F.Electrical] | None:
    if component.has_trait(F.can_attach_to_footprint):
        logger.warning(f"Component {component} already has a pinmap, skipping")
        return None

    if component.has_trait(F.can_attach_to_footprint_symmetrically):
        logger.warning(
            f"Component {component} is symmetrical, thus doesn't need a pimap"
        )
        return None

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

    logger.warning(f"No pinmap found for component {component}, attaching pins by name")
    easyeda_symbol = EasyedaSymbolImporter(easyeda_cp_cad_data=data).get_symbol()
    pins = [
        (int(pin.settings.spice_pin_number), pin.name.text)
        for pin in easyeda_symbol.pins
    ]
    if component.has_trait(F.has_pin_association_heuristic):
        pinmap = component.get_trait(F.has_pin_association_heuristic).get_pins(pins)
    else:
        raise NotImplementedError

    return pinmap


class Category(Model):
    id = IntField(primary_key=True)
    category = CharField(max_length=255)
    subcategory = CharField(max_length=255)

    class Meta:
        table = "categories"

    async def get_ids(
        self, category: str = "", subcategory: str = ""
    ) -> list[dict[str, Any]]:
        """
        Get the category ids for the given category and subcategory

        :param category: The category to search for, use "" for any
        :param subcategory: The subcategory to search for, use "" for any

        :return: A list of category ids for the JLCPCB database Component id field
        """
        filter_query = Q()
        if category != "":
            filter_query &= Q(category__icontains=category)
        if subcategory != "":
            filter_query &= Q(subcategory__icontains=subcategory)
        category_ids = await self.filter(filter_query).values("id")
        if len(category_ids) < 1:
            raise LookupError(
                f"Could not find a match for category {category} "
                f"and subcategory {subcategory}",
            )
        return [c["id"] for c in category_ids]


class Manufacturers(Model):
    id = IntField(primary_key=True)
    name = CharField(max_length=255)

    class Meta:
        table = "manufacturers"

    async def get_from_id(self, manufacturer_id: int) -> str:
        return (await self.get(id=manufacturer_id)).name


class Component(Model):
    lcsc = IntField(primary_key=True)
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

    def get_price(self, qty: int = 1) -> float:
        """
        Get the price for qty of the component including handling fees

        For handling fees and component price classifications, see:
        https://jlcpcb.com/help/article/pcb-assembly-faqs
        """
        BASIC_HANDLING_FEE = 0
        PREFERRED_HANDLING_FEE = 0
        EXTENDED_HANDLING_FEE = 3

        if qty < 1:
            raise ValueError("Quantity must be greater than 0")

        if self.basic:
            handling_fee = BASIC_HANDLING_FEE
        elif self.preferred:
            handling_fee = PREFERRED_HANDLING_FEE
        else:
            handling_fee = EXTENDED_HANDLING_FEE

        unit_price = float("inf")
        try:
            for p in self.price:
                if p["qTo"] is None or qty < p["qTo"]:
                    unit_price = float(p["price"])
            unit_price = float(self.price[-1]["price"])
        except LookupError:
            pass

        return unit_price * qty + handling_fee

    def attribute_to_parameter(
        self, attribute_name: str, use_tolerance: bool = False
    ) -> Parameter:
        """
        Convert a component value in the extra['attributes'] dict to a parameter

        :param attribute_name: The key in the extra['attributes'] dict to convert
        :param use_tolerance: Whether to use the tolerance field in the component

        :return: The parameter representing the attribute value
        """
        assert isinstance(self.extra, dict) and "attributes" in self.extra

        value_field = self.extra["attributes"][attribute_name]
        # JLCPCB uses "u" for µ
        value_field = value_field.replace("u", "µ")
        # parse fields like "850mV@1A"
        value_field = value_field.split("@")[0]

        try:
            # parse fields like "1.5V~2.5V"
            if "~" in value_field:
                values = value_field.split("~")
                values = [si_str_to_float(v) for v in values]
                if len(values) != 2:
                    raise ValueError(f"Invalid range from value '{value_field}'")
                return F.Range(*values)

            value = si_str_to_float(value_field)

        except ValueError as e:
            logger.warning(e)
            return F.ANY()

        if not use_tolerance:
            return F.Constant(value)

        try:
            if "Tolerance" not in self.extra["attributes"]:
                raise ValueError(f"No Tolerance field in component (lcsc: {self.lcsc})")
            if "ppm" in self.extra["attributes"]["Tolerance"]:
                tolerance = (
                    float(self.extra["attributes"]["Tolerance"].strip("±pm")) / 1e6
                )
            elif "%~+" in self.extra["attributes"]["Tolerance"]:
                tolerances = self.extra["attributes"]["Tolerance"].split("~")
                tolerances = [float(t.strip("%+-")) for t in tolerances]
                tolerance = max(tolerances) / 100
            elif "%" in self.extra["attributes"]["Tolerance"]:
                tolerance = (
                    float(self.extra["attributes"]["Tolerance"].strip("%±")) / 100
                )
            else:
                raise ValueError(
                    "Could not parse tolerance field "
                    f"'{self.extra['attributes']['Tolerance']}'"
                )
        except ValueError as e:
            logger.warning(e)
            return F.ANY()

        return F.Range.from_center_rel(value, tolerance)

    T = TypeVar("T")

    def get_parameter(
        self,
        attribute_search_keys: str | list[str],
        tolerance_search_key: str | None = None,
        parser: Callable[[str], T] | None = None,
    ) -> Parameter[T]:
        """
        Transform a component attribute to a parameter

        :param attribute_search_keys: The key in the component's extra['attributes']
        dict that holds the value to check
        :param tolerance_search_key: The key in the component's extra['attributes'] dict
        that holds the tolerance value
        :param parser: A function to convert the attribute value to the correct type

        :return: The parameter representing the attribute value
        """

        if tolerance_search_key is not None and parser is not None:
            raise NotImplementedError(
                "Cannot provide both tolerance_search_key and parser arguments"
            )

        assert isinstance(self.extra, dict)

        attr_key = next(
            (k for k in attribute_search_keys if k in self.extra.get("attributes", "")),
            None,
        )

        if "attributes" not in self.extra:
            logger.debug(f"self {self.lcsc} does not have any attributes")
            return F.ANY()
        if attr_key is None:
            logger.debug(
                f"self {self.lcsc} does not have any of required attribute fields: "
                f"{attribute_search_keys}"
            )
            return F.ANY()
        if (
            tolerance_search_key is not None
            and tolerance_search_key not in self.extra["attributes"]
        ):
            logger.debug(
                f"self {self.lcsc} does not have any of required tolerance fields: "
                f"{tolerance_search_key}"
            )
            return F.ANY()

        try:
            # field_val = self.attribute_to_parameter(attr_key, use_tolerance)
            if parser is None:
                field_val = self.attribute_to_parameter(attr_key, True)
            else:
                field_val = parser(self.extra["attributes"][attr_key])
            return field_val

        except ValueError as e:
            logger.debug(
                f"Could not parse component with '{attr_key}' field "
                f"'{self.extra['attributes'][attr_key]}', Error: '{e}'"
            )

        return F.ANY()

    def attach(
        self,
        module: Module,
        mapping: list[MappingParameterDB],
        qty: int = 1,
    ):
        params = [
            self.get_parameter(
                attribute_search_keys=m.attr_keys,
                tolerance_search_key=m.attr_tolerance_key,
                parser=m.transform_fn,
            )
            for m in mapping
        ]

        for name, value in zip([m.param_name for m in mapping], params):
            module.PARAMs.__getattribute__(name).merge(value)

        F.has_defined_descriptive_properties.add_properties_to(
            module,
            {
                DescriptiveProperties.partno: self.mfr,
                DescriptiveProperties.manufacturer: asyncio.run(
                    Manufacturers().get_from_id(self.manufacturer_id)
                ),
                DescriptiveProperties.datasheet: self.datasheet,
                "JLCPCB stock": str(self.stock),
                "JLCPCB price": f"{self.get_price(qty):.4f}",
                "JLCPCB description": self.description,
                "JLCPCB Basic": str(bool(self.basic)),
                "JLCPCB Preferred": str(bool(self.preferred)),
            },
        )

        module.add_trait(has_part_picked_defined(JLCPCB_Part(f"C{self.lcsc}")))

        if not module.has_trait(F.can_attach_to_footprint):
            pinmap = auto_pinmapping(module, f"C{self.lcsc}")
            assert pinmap is not None
            module.add_trait(F.can_attach_to_footprint_via_pinmap(pinmap))

        attach_footprint(module, f"C{self.lcsc}", True)


class ComponentQuery:
    def __init__(self):
        self.Q = Q()
        self.results: list[Component] = []

    async def exec(self) -> list[Component]:
        self.results = await Component.filter(self.Q)
        return self.results

    def get(self) -> list[Component]:
        return self.results or asyncio.run(self.exec())

    def by_stock(self, qty: int) -> Self:
        assert not self.results
        self.Q &= Q(stock__gte=qty)
        return self

    def by_value(self, value: Parameter, si_unit: str) -> Self:
        assert not self.results
        value_query = Q()
        for r in e_series_intersect(
            value.get_most_narrow(), E_SERIES_VALUES.E_ALL
        ).params:
            assert isinstance(r, F.Constant)
            si_val = float_to_si_str(r.value, si_unit).replace("µ", "u")
            value_query |= Q(description__contains=f" {si_val}")
        self.Q &= value_query
        return self

    def by_category(self, category: str, subcategory: str) -> Self:
        assert not self.results
        category_ids = asyncio.run(Category().get_ids(category, subcategory))
        self.Q &= Q(category_id__in=category_ids)
        return self

    def by_footprint(
        self, footprint_candidates: Sequence[tuple[str, int]] | None
    ) -> Self:
        assert not self.results
        if not footprint_candidates:
            return self
        footprint_query = Q()
        if footprint_candidates is not None:
            for footprint, pin_count in footprint_candidates:
                footprint_query |= Q(description__icontains=footprint) & Q(
                    joints=pin_count
                )
        self.Q &= footprint_query
        return self

    def sort_by_price(self, qty: int = 1) -> Self:
        results = self.get()
        sorted(results, key=lambda x: x.get_price(qty))
        return self

    def by_lcsc_pn(self, partnumber: str) -> Self:
        assert not self.results
        self.Q &= Q(id=partnumber.strip("C"))
        return self

    def by_manufacturer_pn(self, partnumber: str) -> Self:
        assert not self.results
        self.Q &= Q(mfr__icontains=partnumber)
        return self

    def by_params(
        self,
        module: Module,
        mapping: list[MappingParameterDB],
        qty: int = 1,
        attach_first: bool = False,
    ) -> Self:
        """
        Filter the results by the parameters of the module

        This should be used as the last step before attaching the component to the
        module

        :param module: The module to filter by
        :param mapping: The mapping of module parameters to component attributes
        :param qty: The quantity of components needed
        :param attach_first: Whether to attach the first component that matches the
        parameters and return immediately

        :return: The first component that matches the parameters
        """
        if not self.results:
            self.get()

        results = []

        for c in self.results:
            params = [
                c.get_parameter(
                    attribute_search_keys=m.attr_keys,
                    tolerance_search_key=m.attr_tolerance_key,
                    parser=m.transform_fn,
                )
                for m in mapping
            ]
            if not all(
                pm := [
                    p.is_more_specific_than(
                        module.PARAMs.__getattribute__(m.param_name).get_most_narrow()
                    )
                    for p, m in zip(params, mapping)
                ]
            ):
                logger.debug(
                    f"Component {c.lcsc} doesn't match: "
                    f"{[p for p, v in zip(params, pm) if not v]}"
                )
                continue

            logger.info(
                f"Found part {c.lcsc:8} "
                f"Basic: {bool(c.basic)}, Preferred: {bool(c.preferred)}, "
                f"Price: ${c.get_price(1):2.4f}, "
                f"{c.description:15},"
            )

            results.append(c)

            if attach_first:
                try:
                    c.attach(module, mapping, qty)
                    return self
                except Exception as e:
                    logger.warning(f"Failed to attach component: {e}")

        if attach_first:
            raise PickError(
                "No components that matched the parameters could be attached", module
            )

        return self


class JLCPCB_DB:
    def __init__(
        self,
        db_path: Path = Path("jlcpcb_part_database"),
        no_download_prompt: bool = False,
        force_db_update: bool = False,
    ) -> None:
        self.results = []
        self.db_path = db_path
        self.db_file = db_path / Path("cache.sqlite3")
        self.connected = False

        if not sys.stdin.isatty():
            no_download_prompt = True

        if force_db_update:
            self.download()
        elif not self.has_db():
            if no_download_prompt or self.prompt_db_update(
                f"No JLCPCB database found at {self.db_file}, download now?"
            ):
                self.download()
            else:
                raise FileNotFoundError(f"No JLCPCB database found at {self.db_file}")
        elif not self.is_db_up_to_date():
            if no_download_prompt or self.prompt_db_update(
                f"JLCPCB database at {self.db_file} is older than 7 days, update?"
            ):
                self.download()
            else:
                logger.warning("Continuing with outdated JLCPCB database")

        asyncio.run(self._init_db())

    def __del__(self):
        if self.connected:
            asyncio.run(self._close_db())

    async def _init_db(self):

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

    def has_db(self) -> bool:
        return self.db_path.is_dir() and self.db_file.is_file()

    def is_db_up_to_date(
        self, max_timediff: datetime.timedelta = datetime.timedelta(days=7)
    ) -> bool:
        if not self.has_db():
            return False

        return (
            datetime.datetime.fromtimestamp(
                self.db_file.stat().st_mtime, tz=datetime.timezone.utc
            )
            >= datetime.datetime.now(tz=datetime.timezone.utc) - max_timediff
        )

    def prompt_db_update(self, prompt: str = "Update JLCPCB database?") -> bool:
        ans = input(prompt + " [Y/n]:").lower()
        return ans == "y" or ans == ""

    def download(
        self,
    ):
        zip_file = self.db_path / Path("cache.zip")

        if not self.db_path.is_dir():
            os.makedirs(self.db_path)

        wget.download(
            "https://yaqwsx.github.io/jlcparts/data/cache.zip",
            out=str(zip_file),
        )
        # TODO: use requrests and 7z from python? (py7zr) and auto calc number
        # of files
        for i in range(1, 50):
            try:
                wget.download(
                    f"https://yaqwsx.github.io/jlcparts/data/cache.z{i:02d}",
                    out=str(self.db_path / Path(f"cache.z{i:02d}")),
                )
            except HTTPError:
                break
        subprocess.run(["7z", "x", str(zip_file), f"-o{self.db_path}"])
