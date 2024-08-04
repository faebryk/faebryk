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


@dataclass
class MappingParameterDB:
    param_name: str
    attr_keys: list[str]
    attr_tolerance_key: str | None = None
    transform_fn: Callable[[str], Any] = lambda x: x


def auto_pinmapping(component: Module, partno: str):
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

    logger.warning(f"No pinmap found for component {component}, attaching pins by name")
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


class JLCPCB(Supplier):
    def __init__(self, no_download_prompt: bool = False) -> None:
        super().__init__()
        self.db = JLCPCB_DB(no_download_prompt=no_download_prompt)

    def attach(self, module: Module, part: PickerOption):
        assert isinstance(part.part, JLCPCB_Part)
        asyncio.run(Component().find_by_lcsc_pn(part.part.partno))

    def pick(self, module: Module):
        if module.has_trait(has_part_picked):
            if isinstance(module.get_trait(has_part_picked).get_part(), JLCPCB_Part):
                lcsc_pn = module.get_trait(has_part_picked).get_part().partno
                asyncio.run(Component().find_by_lcsc_pn(lcsc_pn))
            else:
                return
        if module.has_trait(has_descriptive_properties) and hasattr(
            module.get_trait(has_descriptive_properties).get_properties,
            DescriptiveProperties.partno,
        ):
            mfr_pn = module.get_trait(has_descriptive_properties).get_properties()[
                DescriptiveProperties.partno
            ]
            asyncio.run(Component().find_by_manufacturer_pn(mfr_pn))
        elif isinstance(module, F.Resistor):
            asyncio.run(self.db.find_resistor(module))
        elif isinstance(module, F.Capacitor):
            asyncio.run(self.db.find_capacitor(module))
        elif isinstance(module, F.Inductor):
            asyncio.run(self.db.find_inductor(module))
        elif isinstance(module, F.TVS):
            asyncio.run(self.db.find_tvs(module))
        elif isinstance(module, F.Diode):
            asyncio.run(self.db.find_diode(module))
        elif isinstance(module, F.MOSFET):
            asyncio.run(self.db.find_mosfet(module))
        elif isinstance(module, F.LDO):
            logger.setLevel(logging.DEBUG)
            asyncio.run(self.db.find_ldo(module))
            logger.setLevel(logging.INFO)
        else:
            return


class JLCPCB_Part(LCSC_Part):
    def __init__(self, partno: str) -> None:
        super().__init__(partno=partno)


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

    async def _attach_component_to_module(
        self,
        module: Module,
        mapping: list[MappingParameterDB],
        qty: int = 100,
    ):
        F.has_defined_descriptive_properties.add_properties_to(
            module,
            {
                DescriptiveProperties.partno: self.mfr,
                DescriptiveProperties.manufacturer: await Manufacturers().get_from_id(
                    self.manufacturer_id
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

        if not module.has_trait(can_attach_to_footprint):
            auto_pinmapping(module, f"C{self.lcsc}")

        attach_footprint(module, f"C{self.lcsc}", True)

    async def find_by_lcsc_pn(self, partnumber: str, qty: int = 100):
        filter_query = Q(stock__gte=qty) & Q(id=partnumber.strip("C"))
        res = await self.filter(filter_query).order_by("-basic")
        if len(res) != 1:
            raise LookupError(
                f"Could not find exact match for LCSC PN {partnumber} with qty {qty}"
            )
        await res[0]._attach_component_to_module(Module(), [], qty)

    async def find_by_manufacturer_pn(self, partnumber: str, qty: int = 100):
        filter_query = Q(stock__gte=qty) & Q(mfr__icontains=partnumber)
        res = await self.filter(filter_query).order_by("-basic")
        if len(res) < 1:
            raise LookupError(
                f"Could not find match for manufacturer PN {partnumber} with qty {qty}"
            )
        sorted(res, key=lambda x: x.get_price(qty))
        await res[0]._attach_component_to_module(Module(), [], qty)

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
            return F.TBD()

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
                tolerances = self.extra["attributes"]["tolerance"].split("~")
                tolerances = [float(t.strip("%+-")) for t in tolerances]
                tolerance = max(tolerances) / 100
            elif "%" in self.extra["attributes"]["Tolerance"]:
                tolerance = (
                    float(self.extra["attributes"]["Tolerance"].strip("%±")) / 100
                )
            else:
                raise ValueError
        except ValueError as e:
            logger.warning(e)
            return F.TBD()

        return F.Range.from_center_rel(value, tolerance)

    def satisfies_requirement(
        self,
        attributes_keys: list[str],
        requirement: Parameter,
        use_tolerance: bool = False,
        tolerance_key: str = "Tolerance",
        attr_fn: Callable[[str], Any] = lambda x: float(x),
    ) -> Parameter | None:
        """
        Check if the component satisfies the requirement

        :param attributes_key: The key in the component's extra['attributes'] dict that
        holds the value to check
        :param requirement: The requirement to check against
        :param use_tolerance: Whether to use the tolerance field in the component
        :param tolerance_key: The key in the component's extra['attributes'] dict that
        holds the tolerance value
        :param attr_fn: A function to convert the attribute value to the correct type

        :return Returns the value of the component if it satisfies the requirement,
        otherwise None
        """
        if isinstance(requirement, F.ANY):
            return F.ANY()

        assert isinstance(self.extra, dict)

        attr_key = next(
            (k for k in attributes_keys if k in self.extra.get("attributes", "")),
            None,
        )

        if (
            "attributes" not in self.extra
            or not attr_key
            or (use_tolerance and (tolerance_key not in self.extra["attributes"]))
        ):
            logger.debug(
                f"self {self.lcsc} does not have any of required fields "
                f"'{attributes_keys}'"
            )
            return None

        try:
            # field_val = self.attribute_to_parameter(attr_key, use_tolerance)
            if use_tolerance:
                if not isinstance(requirement, F.Range):
                    raise NotImplementedError
                field_val = self.attribute_to_parameter(attr_key, use_tolerance)
            else:
                field_val = attr_fn(self.extra["attributes"][attr_key])

            valid = field_val.is_more_specific_than(requirement)
            if not valid:
                logger.debug(
                    f"self {self.lcsc} does not satisfy requirement "
                    f"'{attr_key}': requirement: {requirement}, "
                    f"value: {field_val}"
                )
            return field_val if valid else None
        except ValueError as e:
            logger.debug(
                f"Could not parse component with '{attr_key}' field "
                f"'{self.extra['attributes'][attr_key]}', Error: '{e}'"
            )
            return None


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

    async def find_resistor(self, cmp: F.Resistor, qty: int = 100):
        """
        Find a resistor part in the JLCPCB database that matches the parameters of the
        provided resistor
        """

        resistors = await self._run_query(
            cmp,
            category="Resistors",
            subcategory="Chip Resistor - Surface Mount",
            si_values_from_param=cmp.PARAMs.resistance,
            si_unit="Ω",
            qty=qty,
        )

        mapping = [
            MappingParameterDB("resistance", ["Resistance"], "Tolerance"),
            MappingParameterDB(
                "rated_power",
                ["Power(Watts)"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            MappingParameterDB(
                "rated_voltage",
                ["Overload Voltage (Max)"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
        ]

        await self._filter_by_params_and_attach(cmp, resistors, mapping, qty)

    async def find_capacitor(self, cmp: F.Capacitor, qty: int = 100):
        """
        Find a capacitor part in the JLCPCB database that matches the parameters of the
        provided capacitor
        """

        # TODO: add support for electrolytic capacitors.
        capacitors = await self._run_query(
            cmp,
            category="Capacitors",
            subcategory="Multilayer Ceramic Capacitors MLCC - SMD/SMT",
            si_values_from_param=cmp.PARAMs.capacitance,
            si_unit="F",
            qty=qty,
        )

        def TemperatureCoefficient_str_to_param(
            x: str,
        ) -> F.Constant[F.Capacitor.TemperatureCoefficient]:
            try:
                return F.Constant(
                    F.Capacitor.TemperatureCoefficient[x.replace("NP0", "C0G")]
                )
            except KeyError:
                raise ValueError(f"Unknown temperature coefficient: {x}")

        mapping = [
            MappingParameterDB("capacitance", ["Capacitance"], "Tolerance"),
            MappingParameterDB(
                "rated_voltage",
                ["Voltage Rated"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            MappingParameterDB(
                "temperature_coefficient",
                ["Temperature Coefficient"],
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
        # Adjustable Inductors. HF and Adjustable are basically empty.
        inductors = await self._run_query(
            cmp,
            category="Inductors",
            subcategory="Inductors",
            si_values_from_param=cmp.PARAMs.inductance,
            si_unit="H",
            qty=qty,
        )

        mapping = [
            MappingParameterDB("inductance", ["Inductance"], "Tolerance"),
            MappingParameterDB(
                "rated_current",
                ["Rated Current"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            MappingParameterDB(
                "dc_resistance",
                ["DC Resistance (DCR)", "DC Resistance"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            MappingParameterDB(
                "self_resonant_frequency",
                ["Frequency - Self Resonant"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
        ]

        await self._filter_by_params_and_attach(cmp, inductors, mapping, qty)

    async def find_tvs(self, cmp: F.TVS, qty: int = 100):
        """
        Find a TVS diode part in the JLCPCB database that matches the parameters of the
        provided diode
        """
        # TODO: handle bidirectional TVS diodes
        # "Bidirectional Channels": "1" in extra['attributes']
        diodes = await self._run_query(
            cmp,
            category="",
            subcategory="TVS",
            qty=qty,
        )

        mapping = [
            MappingParameterDB(
                "forward_voltage",
                ["Forward Voltage", "Forward Voltage (Vf@If)"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x.split("@")[0])),
            ),
            # TODO: think about the difference of meaning for max_current between Diode
            # and TVS
            MappingParameterDB(
                "max_current",
                ["Peak Pulse Current (Ipp)@10/1000us"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            MappingParameterDB(
                "reverse_working_voltage",
                ["Reverse Voltage (Vr)", "Reverse Stand-Off Voltage (Vrwm)"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            MappingParameterDB(
                "reverse_leakage_current",
                ["Reverse Leakage Current", "Reverse Leakage Current (Ir)"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x.split("@")[0])),
            ),
            MappingParameterDB(
                "reverse_breakdown_voltage",
                ["Breakdown Voltage"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
        ]

        await self._filter_by_params_and_attach(cmp, diodes, mapping, qty)

    async def find_diode(self, cmp: F.Diode, qty: int = 100):
        """
        Find a diode part in the JLCPCB database that matches the parameters of the
        provided diode
        """
        diodes = await self._run_query(
            cmp,
            category="",
            subcategory="Diodes",
            qty=qty,
        )

        mapping = [
            MappingParameterDB(
                "forward_voltage",
                ["Forward Voltage", "Forward Voltage (Vf@If)"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x.split("@")[0])),
            ),
            MappingParameterDB(
                "max_current",
                ["Average Rectified Current (Io)"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            MappingParameterDB(
                "reverse_working_voltage",
                ["Reverse Voltage (Vr)", "Reverse Stand-Off Voltage (Vrwm)"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            MappingParameterDB(
                "reverse_leakage_current",
                ["Reverse Leakage Current", "Reverse Leakage Current (Ir)"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x.split("@")[0])),
            ),
        ]

        await self._filter_by_params_and_attach(cmp, diodes, mapping, qty)

    async def find_mosfet(self, cmp: F.MOSFET, qty: int = 100):
        """
        Find a MOSFET part in the JLCPCB database that matches the parameters of the
        provided MOSFET
        """

        mosfets = await self._run_query(
            cmp,
            category="",
            subcategory="MOSFET",
            qty=qty,
        )

        def ChannelType_str_to_param(x: str) -> F.Constant[F.MOSFET.ChannelType]:
            if x in ["N Channel", "N-Channel"]:
                return F.Constant(F.MOSFET.ChannelType.N_CHANNEL)
            elif x in ["P Channel", "P-Channel"]:
                return F.Constant(F.MOSFET.ChannelType.P_CHANNEL)
            else:
                raise ValueError(f"Unknown MOSFET type: {x}")

        mapping = [
            MappingParameterDB(
                "max_drain_source_voltage",
                ["Drain Source Voltage (Vdss)"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            MappingParameterDB(
                "max_continuous_drain_current",
                ["Continuous Drain Current (Id)"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            MappingParameterDB(
                "channel_type",
                ["Type"],
                transform_fn=lambda x: (ChannelType_str_to_param(x)),
            ),
            MappingParameterDB(
                "gate_source_threshold_voltage",
                ["Gate Threshold Voltage (Vgs(th)@Id)"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x.split("@")[0])),
            ),
            MappingParameterDB(
                "on_resistance",
                ["Drain Source On Resistance (RDS(on)@Vgs,Id)"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x.split("@")[0])),
            ),
        ]

        await self._filter_by_params_and_attach(cmp, mosfets, mapping, qty)

    async def find_ldo(self, cmp: F.LDO, qty: int = 100):
        """
        Find a LDO part in the JLCPCB database that matches the parameters of the
        provided LDO
        """

        ldos = await self._run_query(
            cmp,
            category="",
            subcategory="LDO",
            qty=qty,
        )

        def OutputType_str_to_param(x: str) -> F.Constant[F.LDO.OutputType]:
            if x == "Fixed":
                return F.Constant(F.LDO.OutputType.FIXED)
            elif x == "Adjustable":
                return F.Constant(F.LDO.OutputType.ADJUSTABLE)
            else:
                raise ValueError(f"Unknown LDO output type: {x}")

        def OutputPolarity_str_to_param(x: str) -> F.Constant[F.LDO.OutputPolarity]:
            if x == "Positive":
                return F.Constant(F.LDO.OutputPolarity.POSITIVE)
            elif x == "Negative":
                return F.Constant(F.LDO.OutputPolarity.NEGATIVE)
            else:
                raise ValueError(f"Unknown LDO output polarity: {x}")

        mapping = [
            MappingParameterDB(
                "output_polarity",
                ["Output Polarity"],
                transform_fn=lambda x: OutputPolarity_str_to_param(x),
            ),
            MappingParameterDB(
                "max_input_voltage",
                ["Maximum Input Voltage"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            MappingParameterDB(
                "output_type",
                ["Output Type"],
                transform_fn=lambda x: OutputType_str_to_param(x),
            ),
            MappingParameterDB(
                "output_current",
                ["Output Current"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
            MappingParameterDB(
                "dropout_voltage",
                ["Dropout Voltage"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x.split("@")[0])),
            ),
            MappingParameterDB(
                "output_voltage",
                ["Output Voltage"],
                transform_fn=lambda x: F.Constant(si_str_to_float(x)),
            ),
        ]

        await self._filter_by_params_and_attach(cmp, ldos, mapping, qty)

    async def _filter_by_params_and_attach(
        self,
        module: Module,
        components: list[Component],
        mapping: list[MappingParameterDB],
        qty: int = 100,
    ):
        for c in components:
            if not all(
                pm := [
                    c.satisfies_requirement(
                        m.attr_keys,
                        module.PARAMs.__getattribute__(m.param_name).get_most_narrow(),
                        use_tolerance=m.attr_tolerance_key is not None,
                        tolerance_key=m.attr_tolerance_key or "",
                        attr_fn=m.transform_fn,
                    )
                    for m in mapping
                ]
            ):
                continue

            for name, value in zip([m.param_name for m in mapping], pm):
                module.PARAMs.__getattribute__(name).merge(value)

            logger.info(
                f"Found part {c.lcsc:8} "
                f"Basic: {bool(c.basic)}, Preferred: {bool(c.preferred)}, "
                f"Price: ${c.get_price(1):2.4f}, "
                f"{c.description:15},"
            )

            try:
                await c._attach_component_to_module(module, mapping, qty)
            except ValueError as e:
                logger.error(f"Could not attach component {c.lcsc}: {e}")
                continue

            return

    async def _run_query(
        self,
        module: Module,
        category: str,
        subcategory: str,
        si_values_from_param: Parameter | None = None,
        si_unit="",
        qty: int = 100,
    ) -> list[Component]:
        try:
            category_ids = await Category().get_ids(category, subcategory)
        except LookupError as e:
            raise PickError(f"Could not find category: {e}", module)

        footprint_query = Q()
        if module.has_trait(F.has_footprint_requirement):
            req = module.get_trait(
                F.has_footprint_requirement
            ).get_footprint_requirement()
            for footprint, pin_count in req:
                footprint_query |= Q(description__icontains=footprint) & Q(
                    joints=pin_count
                )

        value_query = Q()
        if si_values_from_param:
            for r in e_series_intersect(
                si_values_from_param.get_most_narrow(), E_SERIES_VALUES.E_ALL
            ).params:
                assert isinstance(r, F.Constant)
                si_val = float_to_si_str(r.value, si_unit).replace("µ", "u")
                value_query |= Q(description__contains=f" {si_val}")

        filter_query = (
            Q(category_id__in=category_ids)
            & Q(stock__gte=qty)
            & footprint_query
            & value_query
        )

        results = await Component.filter(filter_query).order_by("-basic")

        if len(results) < 1:
            raise PickError("No parts found", module)

        sorted(results, key=lambda x: x.get_price(qty))

        return results
