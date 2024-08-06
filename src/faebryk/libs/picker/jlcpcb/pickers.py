import logging

import faebryk.library._F as F
from faebryk.core.core import Module
from faebryk.library.can_query_jlcpcb_db import can_query_jlcpcb_db
from faebryk.library.can_query_jlcpcb_db_defined import can_query_jlcpcb_db_defined
from faebryk.libs.picker.jlcpcb.jlcpcb import (
    JLCPCB_DB,
    ComponentQuery,
    MappingParameterDB,
)
from faebryk.libs.picker.picker import (
    DescriptiveProperties,
    PickError,
    PickErrorNotImplemented,
    has_part_picked,
)
from faebryk.libs.units import si_str_to_float

logger = logging.getLogger(__name__)


def pick_module_by_query(module: Module, qty: int = 1) -> None:
    if not module.has_trait(can_query_jlcpcb_db):
        find_query_for_module(module)

    db = JLCPCB_DB()
    module.get_trait(can_query_jlcpcb_db).get_picker()(module, qty)
    del db


def find_query_for_module(module: Module) -> None:
    if module.has_trait(has_part_picked):
        raise PickError("Module already has a part picked", module)

    if module.has_trait(F.has_descriptive_properties) and hasattr(
        module.get_trait(F.has_descriptive_properties).get_properties,
        DescriptiveProperties.partno,
    ):
        mfr_pn = module.get_trait(F.has_descriptive_properties).get_properties()[
            DescriptiveProperties.partno
        ]
        module.add_trait(
            can_query_jlcpcb_db_defined(
                lambda m, q: find_manufacturer_part(m, mfr_pn, q)
            )
        )
    elif isinstance(module, F.Resistor):
        module.add_trait(can_query_jlcpcb_db_defined(find_resistor))
    elif isinstance(module, F.Capacitor):
        module.add_trait(can_query_jlcpcb_db_defined(find_capacitor))
    elif isinstance(module, F.Inductor):
        module.add_trait(can_query_jlcpcb_db_defined(find_inductor))
    elif isinstance(module, F.TVS):
        module.add_trait(can_query_jlcpcb_db_defined(find_tvs))
    elif isinstance(module, F.Diode):
        module.add_trait(can_query_jlcpcb_db_defined(find_diode))
    elif isinstance(module, F.MOSFET):
        module.add_trait(can_query_jlcpcb_db_defined(find_mosfet))
    elif isinstance(module, F.LDO):
        module.add_trait(can_query_jlcpcb_db_defined(find_ldo))
    else:
        raise PickErrorNotImplemented(module)


def find_lcsc_part(module: Module, lcsc_pn: str, qty: int = 1):
    """
    Find a part in the JLCPCB database by its LCSC part number
    """

    parts = ComponentQuery().by_lcsc_pn(lcsc_pn).get()

    if len(parts) < 1:
        raise PickError(f"Could not find part with LCSC part number {lcsc_pn}", module)

    if len(parts) > 1:
        raise PickError(f"Found no exact match for LCSC part number {lcsc_pn}", module)

    if parts[0].stock < qty:
        raise PickError(
            f"Part with LCSC part number {lcsc_pn} has insufficient stock", module
        )

    parts[0].attach(module, [])


def find_manufacturer_part(module: Module, mfr_pn: str, qty: int = 1):
    """
    Find a part in the JLCPCB database by its manufacturer part number
    """

    parts = (
        ComponentQuery().by_manufacturer_pn(mfr_pn).by_stock(qty).sort_by_price().get()
    )

    if len(parts) < 1:
        raise PickError(
            f"Could not find part with manufacturer part number {mfr_pn}", module
        )

    for part in parts:
        try:
            part.attach(module, [])
            return
        except Exception as e:
            logger.warning(f"Failed to attach component: {e}")
            continue

    raise PickError(
        f"Could not attach any part with manufacturer part number {mfr_pn}", module
    )


def find_resistor(cmp: Module, qty: int = 1):
    """
    Find a resistor part in the JLCPCB database that matches the parameters of the
    provided resistor
    """
    assert isinstance(cmp, F.Resistor)

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

    (
        ComponentQuery()
        .by_category("Resistors", "Chip Resistor - Surface Mount")
        .by_stock(qty)
        .by_value(cmp.PARAMs.resistance, "Ω")
        .by_footprint(
            footprint_candidates=(
                cmp.get_trait(F.has_footprint_requirement).get_footprint_requirement()
                if cmp.has_trait(F.has_footprint_requirement)
                else None
            ),
        )
        .sort_by_price(qty)
        .by_params(cmp, mapping, qty, attach_first=True)
    )


def find_capacitor(cmp: Module, qty: int = 1):
    """
    Find a capacitor part in the JLCPCB database that matches the parameters of the
    provided capacitor
    """

    assert isinstance(cmp, F.Capacitor)

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

    # TODO: add support for electrolytic capacitors.
    (
        ComponentQuery()
        .by_category("Capacitors", "Multilayer Ceramic Capacitors MLCC - SMD/SMT")
        .by_stock(qty)
        .by_footprint(
            footprint_candidates=(
                cmp.get_trait(F.has_footprint_requirement).get_footprint_requirement()
                if cmp.has_trait(F.has_footprint_requirement)
                else None
            ),
        )
        .by_value(cmp.PARAMs.capacitance, "F")
        .sort_by_price(qty)
        .by_params(cmp, mapping, qty, attach_first=True)
    )


def find_inductor(cmp: Module, qty: int = 1):
    """
    Find an inductor part in the JLCPCB database that matches the parameters of the
    provided inductor.

    Note: When the "self_resonant_frequency" parameter is not ANY, only inductors
    from the HF and SMD categories are used.
    """

    assert isinstance(cmp, F.Inductor)

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

    (
        ComponentQuery()
        # Get Inductors (SMD), Power Inductors, TH Inductors, HF Inductors,
        # Adjustable Inductors. HF and Adjustable are basically empty.
        .by_category("Inductors", "Inductors")
        .by_stock(qty)
        .by_footprint(
            footprint_candidates=(
                cmp.get_trait(F.has_footprint_requirement).get_footprint_requirement()
                if cmp.has_trait(F.has_footprint_requirement)
                else None
            ),
        )
        .by_value(cmp.PARAMs.inductance, "H")
        .sort_by_price(qty)
        .by_params(cmp, mapping, qty, attach_first=True)
    )


def find_tvs(cmp: Module, qty: int = 1):
    """
    Find a TVS diode part in the JLCPCB database that matches the parameters of the
    provided diode
    """

    assert isinstance(cmp, F.TVS)

    # TODO: handle bidirectional TVS diodes
    # "Bidirectional Channels": "1" in extra['attributes']

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

    (
        ComponentQuery()
        .by_category("", "TVS")
        .by_stock(qty)
        .by_footprint(
            footprint_candidates=(
                cmp.get_trait(F.has_footprint_requirement).get_footprint_requirement()
                if cmp.has_trait(F.has_footprint_requirement)
                else None
            ),
        )
        .sort_by_price(qty)
        .by_params(cmp, mapping, qty, attach_first=True)
    )


def find_diode(cmp: Module, qty: int = 1):
    """
    Find a diode part in the JLCPCB database that matches the parameters of the
    provided diode
    """

    assert isinstance(cmp, F.Diode)

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

    (
        ComponentQuery()
        .by_category("", "Diodes")
        .by_stock(qty)
        .by_footprint(
            footprint_candidates=(
                cmp.get_trait(F.has_footprint_requirement).get_footprint_requirement()
                if cmp.has_trait(F.has_footprint_requirement)
                else None
            ),
        )
        .sort_by_price(qty)
        .by_params(cmp, mapping, qty, attach_first=True)
    )


def find_mosfet(cmp: Module, qty: int = 1):
    """
    Find a MOSFET part in the JLCPCB database that matches the parameters of the
    provided MOSFET
    """

    assert isinstance(cmp, F.MOSFET)

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

    (
        ComponentQuery()
        .by_category("", "MOSFET")
        .by_stock(qty)
        .by_footprint(
            footprint_candidates=(
                cmp.get_trait(F.has_footprint_requirement).get_footprint_requirement()
                if cmp.has_trait(F.has_footprint_requirement)
                else None
            ),
        )
        .sort_by_price(qty)
        .by_params(cmp, mapping, qty, attach_first=True)
    )


def find_ldo(cmp: Module, qty: int = 1):
    """
    Find a LDO part in the JLCPCB database that matches the parameters of the
    provided LDO
    """

    assert isinstance(cmp, F.LDO)

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
            transform_fn=lambda x: (
                F.Constant(si_str_to_float(x))
                if "~" not in x
                else F.Range(*map(si_str_to_float, x.split("~")))
            ),
        ),
    ]

    (
        ComponentQuery()
        .by_category("", "LDO")
        .by_stock(qty)
        .by_footprint(
            footprint_candidates=(
                cmp.get_trait(F.has_footprint_requirement).get_footprint_requirement()
                if cmp.has_trait(F.has_footprint_requirement)
                else None
            ),
        )
        .sort_by_price(qty)
        .by_params(cmp, mapping, qty, attach_first=True)
    )
