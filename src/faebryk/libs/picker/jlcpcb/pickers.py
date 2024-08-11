import logging
from typing import Callable

import faebryk.library._F as F
from faebryk.core.core import Module
from faebryk.libs.picker.jlcpcb.jlcpcb import (
    JLCPCB_DB,
    ComponentQuery,
    MappingParameterDB,
)
from faebryk.libs.picker.picker import (
    DescriptiveProperties,
    PickError,
    has_part_picked,
)
from faebryk.libs.units import si_str_to_float

logger = logging.getLogger(__name__)


class JLCPCBPicker(F.has_multi_picker.Picker):
    def __init__(self, picker: Callable[[Module, int], None]):
        self.picker = picker

    def pick(self, module: Module, qty: int = 1) -> None:
        assert not module.has_trait(has_part_picked)
        db = JLCPCB_DB()
        self.picker(module, qty)
        del db

    def __repr__(self):
        return f"<{self.__class__.__name__} ({self.picker.__name__})>"


def add_jlcpcb_pickers(module: Module, prio: int = 0) -> None:
    F.has_multi_picker.add_to_module(
        module,
        prio,
        JLCPCBPicker(find_lcsc_part),
    )
    F.has_multi_picker.add_to_module(
        module,
        prio,
        JLCPCBPicker(find_manufacturer_part),
    )

    if isinstance(module, F.Resistor):
        F.has_multi_picker.add_to_module(
            module,
            prio,
            JLCPCBPicker(find_resistor),
        )
    elif isinstance(module, F.Capacitor):
        F.has_multi_picker.add_to_module(
            module,
            prio,
            JLCPCBPicker(find_capacitor),
        )
    elif isinstance(module, F.Inductor):
        F.has_multi_picker.add_to_module(
            module,
            prio,
            JLCPCBPicker(find_inductor),
        )
    elif isinstance(module, F.TVS):
        F.has_multi_picker.add_to_module(
            module,
            prio,
            JLCPCBPicker(find_tvs),
        )
    elif isinstance(module, F.Diode):
        F.has_multi_picker.add_to_module(
            module,
            prio,
            JLCPCBPicker(find_diode),
        )
    elif isinstance(module, F.MOSFET):
        F.has_multi_picker.add_to_module(
            module,
            prio,
            JLCPCBPicker(find_mosfet),
        )
    elif isinstance(module, F.LDO):
        F.has_multi_picker.add_to_module(
            module,
            prio,
            JLCPCBPicker(find_ldo),
        )


def find_lcsc_part(module: Module, qty: int = 1):
    """
    Find a part in the JLCPCB database by its LCSC part number
    """

    if not module.has_trait(F.has_descriptive_properties):
        raise PickError("Module does not have any descriptive properties", module)
    if "LCSC" not in module.get_trait(F.has_descriptive_properties).get_properties():
        raise PickError("Module does not have an LCSC part number", module)

    lcsc_pn = module.get_trait(F.has_descriptive_properties).get_properties()["LCSC"]

    parts = ComponentQuery().filter_by_lcsc_pn(lcsc_pn).get()

    if len(parts) < 1:
        raise PickError(f"Could not find part with LCSC part number {lcsc_pn}", module)

    if len(parts) > 1:
        raise PickError(f"Found no exact match for LCSC part number {lcsc_pn}", module)

    if parts[0].stock < qty:
        raise PickError(
            f"Part with LCSC part number {lcsc_pn} has insufficient stock", module
        )

    parts[0].attach(module, [])


def find_manufacturer_part(module: Module, qty: int = 1):
    """
    Find a part in the JLCPCB database by its manufacturer part number
    """

    if not module.has_trait(F.has_descriptive_properties):
        raise PickError("Module does not have any descriptive properties", module)
    if (
        DescriptiveProperties.partno
        not in module.get_trait(F.has_descriptive_properties).get_properties()
    ):
        raise PickError("Module does not have a manufacturer part number", module)
    if (
        DescriptiveProperties.manufacturer
        not in module.get_trait(F.has_descriptive_properties).get_properties()
    ):
        raise PickError("Module does not have a manufacturer", module)

    mfr_pn = module.get_trait(F.has_descriptive_properties).get_properties()[
        DescriptiveProperties.partno
    ]
    mfr = module.get_trait(F.has_descriptive_properties).get_properties()[
        DescriptiveProperties.manufacturer
    ]

    parts = (
        ComponentQuery()
        .filter_by_manufacturer_pn(mfr_pn)
        .filter_by_manufacturer(mfr)
        .filter_by_stock(qty)
        .sort_by_price()
        .get()
    )

    if len(parts) < 1:
        raise PickError(
            f"Could not find part with manufacturer part number {mfr_pn}", module
        )

    for part in parts:
        try:
            part.attach(module, [])
            return
        except ValueError as e:
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
        .filter_by_category("Resistors", "Chip Resistor - Surface Mount")
        .filter_by_stock(qty)
        .filter_by_value(cmp.PARAMs.resistance, "Ω")
        .filter_by_footprint(
            footprint_candidates=(
                cmp.get_trait(F.has_footprint_requirement).get_footprint_requirement()
                if cmp.has_trait(F.has_footprint_requirement)
                else None
            ),
        )
        .sort_by_price(qty)
        .filter_by_module_params_and_attach(cmp, mapping, qty)
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
        .filter_by_category(
            "Capacitors", "Multilayer Ceramic Capacitors MLCC - SMD/SMT"
        )
        .filter_by_stock(qty)
        .filter_by_footprint(
            footprint_candidates=(
                cmp.get_trait(F.has_footprint_requirement).get_footprint_requirement()
                if cmp.has_trait(F.has_footprint_requirement)
                else None
            ),
        )
        .filter_by_value(cmp.PARAMs.capacitance, "F")
        .sort_by_price(qty)
        .filter_by_module_params_and_attach(cmp, mapping, qty)
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
        .filter_by_category("Inductors", "Inductors")
        .filter_by_stock(qty)
        .filter_by_footprint(
            footprint_candidates=(
                cmp.get_trait(F.has_footprint_requirement).get_footprint_requirement()
                if cmp.has_trait(F.has_footprint_requirement)
                else None
            ),
        )
        .filter_by_value(cmp.PARAMs.inductance, "H")
        .sort_by_price(qty)
        .filter_by_module_params_and_attach(cmp, mapping, qty)
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
        .filter_by_category("", "TVS")
        .filter_by_stock(qty)
        .filter_by_footprint(
            footprint_candidates=(
                cmp.get_trait(F.has_footprint_requirement).get_footprint_requirement()
                if cmp.has_trait(F.has_footprint_requirement)
                else None
            ),
        )
        .sort_by_price(qty)
        .filter_by_module_params_and_attach(cmp, mapping, qty)
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
        .filter_by_category("", "Diodes")
        .filter_by_stock(qty)
        .filter_by_footprint(
            footprint_candidates=(
                cmp.get_trait(F.has_footprint_requirement).get_footprint_requirement()
                if cmp.has_trait(F.has_footprint_requirement)
                else None
            ),
        )
        .sort_by_price(qty)
        .filter_by_module_params_and_attach(cmp, mapping, qty)
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
        .filter_by_category("", "MOSFET")
        .filter_by_stock(qty)
        .filter_by_footprint(
            footprint_candidates=(
                cmp.get_trait(F.has_footprint_requirement).get_footprint_requirement()
                if cmp.has_trait(F.has_footprint_requirement)
                else None
            ),
        )
        .sort_by_price(qty)
        .filter_by_module_params_and_attach(cmp, mapping, qty)
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
        MappingParameterDB(
            "quiescent_current",
            [
                "Quiescent Current",
                "standby current",
                "Quiescent Current (Ground Current)",
            ],
            transform_fn=lambda x: F.Constant(si_str_to_float(x)),
        ),
    ]

    (
        ComponentQuery()
        .filter_by_category("", "LDO")
        .filter_by_stock(qty)
        .filter_by_footprint(
            footprint_candidates=(
                cmp.get_trait(F.has_footprint_requirement).get_footprint_requirement()
                if cmp.has_trait(F.has_footprint_requirement)
                else None
            ),
        )
        .sort_by_price(qty)
        .filter_by_module_params_and_attach(cmp, mapping, qty)
    )
