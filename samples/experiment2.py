# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

# Test stuff ------------------------------------------------------------------
def make_t1_netlist_from_graph(comps):
    t1_netlist = [comp.get_comp() for comp in comps]

    return t1_netlist

def make_graph_from_components(components):
    import faebryk as fy
    import faebryk.library.library as lib
    import faebryk.library.traits as traits
    from faebryk.libs.exceptions import FaebrykException

    class wrapper():
        def __init__(self, component: lib.Component) -> None:
            self.component = component
            self._setup_non_rec()

        def _setup_non_rec(self):
            import random
            c = self.component
            self.real = c.has_trait(traits.has_footprint) and c.has_trait(traits.has_footprint_pinmap)
            self.properties = {}
            self.neighbors = {}
            if self.real:
                self.value = c.get_trait(traits.has_type_description).get_type_description()
                self.properties["footprint"] = \
                    c.get_trait(traits.has_footprint).get_footprint().get_trait(
                        traits.has_kicad_footprint).get_kicad_footprint()
            self.name = "COMP[{}:{}]@{:08X}".format(type(self.component).__name__, self.value if self.real else "virt", int(random.random()*2**32))
            self._comp = {}
            self._update_comp()

        def _update_comp(self):
            self._comp.update({
                "name": self.name,
                "real": self.real,
                "properties": self.properties,
                "neighbors": self.neighbors
            })
            if self.real:
                self._comp["value"] = self.value

        def _get_comp(self):
            return self._comp

        def get_comp(self):
            # only executed once
            neighbors = {}
            for pin, interface in self.component.get_trait(traits.has_footprint_pinmap).get_pin_map().items():
                neighbors[pin] = []
                for target_interface in interface.connections:
                    if target_interface.has_trait(traits.is_part_of_component):
                        target_component = target_interface.get_trait(traits.is_part_of_component).get_component()
                        target_pinmap = target_component.get_trait(traits.has_footprint_pinmap).get_pin_map()
                        target_pin = list(target_pinmap.items())[list(target_pinmap.values()).index(target_interface)][0]
                        try:
                            target_wrapped = [i for i in wrapped_list if i.component == target_component][0]
                        except IndexError:
                            raise FaebrykException("Discovered associated component not in component list:", target_component)

                        neighbors[pin].append({
                          "vertex": target_wrapped._get_comp(),
                          "pin": target_pin
                        })
                    else:
                        print("Warning: {comp} pin {pin} is connected to interface without component".format(
                            comp=self.name,
                            #intf=target_interface,
                            pin=pin,
                        ))

            self.neighbors = neighbors
            self._update_comp()

            return self._get_comp()

    wrapped_list = list(map(wrapper, components))
    for i in wrapped_list:
        i.wrapped_list = wrapped_list

    print("Making graph from components:\n\t{}".format("\n\t".join(map(str, components))))

    return wrapped_list


def run_experiment():
    import faebryk as fy
    import faebryk.library.library as lib
    import faebryk.library.traits as traits
    from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
    from faebryk.exporters.netlist import make_t2_netlist_from_t1

    class _has_interfaces(traits.has_interfaces):
        def __init__(self, interfaces) -> None:
            super().__init__()
            self.interfaces = interfaces

        def get_interfaces(self):
            return lib.get_all_interfaces(self.interfaces)

    class _has_footprint_pinmap(traits.has_footprint_pinmap):
        def __init__(self, comp) -> None:
            super().__init__()
            self.comp = comp

        def get_pin_map(self):
            ifs = self.comp.get_trait(traits.has_interfaces).get_interfaces()
            return {k+1:v for k,v in enumerate(ifs)}


    # levels
    high = lib.Electrical()
    low = lib.Electrical()

    # power
    battery = lib.Component()
    battery.power = lib.Power()

    # alias
    gnd = battery.power.lv
    power = battery.power

    # logic
    nands = [lib.NAND(2) for _ in range(2)]
    nands[0].inputs[1].connect(low)
    nands[1].inputs[0].connect(nands[0].output)
    nands[1].inputs[1].connect(low)
    logic_in = nands[0].inputs[0]
    logic_out = nands[1].output

    #
    current_limiting_resistor = lib.Resistor(resistance=lib.TBD())
    led = lib.LED()

    # led driver
    led.cathode.connect(current_limiting_resistor.interfaces[0])
    current_limiting_resistor.interfaces[1].connect(gnd)

    # application
    switch = lib.Switch()
    switch.interfaces[0].connect(high)
    pull_down_resistor = lib.Resistor(lib.TBD())
    pull_down_resistor.interfaces[0].connect(low)

    logic_in.connect(pull_down_resistor.interfaces[1])
    logic_in.connect(switch.interfaces[1])
    logic_out.connect(led.anode)

    # parametrizing
    battery.voltage = 5
    pull_down_resistor.set_resistance(lib.Constant(100_000))
    led.set_forward_parameters(
        voltage_V=lib.Constant(2.4),
        current_A=lib.Constant(0.020)
    )
    nand_ic = lib.CD4011().get_trait(lib.CD4011.constructable_from_nands).from_nands(nands)
    nand_ic.power.connect(power)
    high.connect(power.hv)
    low.connect(power.lv)
    current_limiting_resistor.set_resistance(led.get_trait(lib.LED.has_calculatable_needed_series_resistance).get_needed_series_resistance_ohm(battery.voltage))

    # packaging
    nand_ic.add_trait(traits.has_defined_footprint(lib.DIP(
        pin_cnt=14,
        spacing_mm=7.62,
        long_pads=False
    )))
    nand_ic.add_trait(traits.has_defined_footprint_pinmap(
        {
            7:  nand_ic.power.lv,
            14: nand_ic.power.hv,
            3:  nand_ic.connection_map[nand_ic.nands[0].output],
            4:  nand_ic.connection_map[nand_ic.nands[1].output],
            11: nand_ic.connection_map[nand_ic.nands[2].output],
            10: nand_ic.connection_map[nand_ic.nands[3].output],
            1:  nand_ic.connection_map[nand_ic.nands[0].inputs[0]],
            2:  nand_ic.connection_map[nand_ic.nands[0].inputs[1]],
            5:  nand_ic.connection_map[nand_ic.nands[1].inputs[0]],
            6:  nand_ic.connection_map[nand_ic.nands[1].inputs[1]],
            12: nand_ic.connection_map[nand_ic.nands[2].inputs[0]],
            13: nand_ic.connection_map[nand_ic.nands[2].inputs[1]],
            9:  nand_ic.connection_map[nand_ic.nands[3].inputs[0]],
            8:  nand_ic.connection_map[nand_ic.nands[3].inputs[1]],
        }
    ))

    for smd_comp in [led, pull_down_resistor, current_limiting_resistor]:
        smd_comp.add_trait(traits.has_defined_footprint(lib.SMDTwoPin(
            lib.SMDTwoPin.Type._0805
        )))

    switch_fp = lib.Footprint()
    switch_fp.add_trait(lib.has_kicad_manual_footprint("Panasonic_EVQPUJ_EVQPUA"))
    switch.add_trait(traits.has_defined_footprint(switch_fp))

    for symmetric_component in [pull_down_resistor, current_limiting_resistor, switch]:
        symmetric_component.add_trait(_has_footprint_pinmap(symmetric_component))

    led.add_trait(traits.has_defined_footprint_pinmap(
        {
            1: led.anode,
            2: led.cathode,
        }
    ))

    #TODO: remove, just compensation for old graph
    battery.add_trait(_has_interfaces([battery.power]))
    battery.get_trait(traits.has_interfaces).set_interface_comp(battery)
    battery.add_trait(_has_footprint_pinmap(battery))
    logic_virt = lib.Component()
    logic_virt.high = high
    logic_virt.low = low
    logic_virt.add_trait(_has_interfaces([logic_virt.high, logic_virt.low]))
    logic_virt.get_trait(traits.has_interfaces).set_interface_comp(logic_virt)
    logic_virt.add_trait(_has_footprint_pinmap(logic_virt))
    for n in nand_ic.nands:
        n.add_trait(_has_footprint_pinmap(n))

    # make graph
    components = [
        led,
        pull_down_resistor,
        current_limiting_resistor,
        nand_ic,
        switch,
        battery,
        logic_virt,
        #TODO make composited comps add their subcomps automatically?
        *nand_ic.nands,
    ]

    t1_ = make_t1_netlist_from_graph(
            make_graph_from_components(components)
        )

    netlist = from_faebryk_t2_netlist(
        make_t2_netlist_from_t1(
            t1_
        )
    )

    print("Experiment netlist:")
    print(netlist)

    #from faebryk.exporters.netlist import render_graph
    #render_graph(t1_)

import sys
import logging

def main(argc, argv, argi):
    logging.basicConfig(level=logging.INFO)

    print("Running experiment")
    run_experiment()

if __name__ == "__main__":
    import os
    import sys
    root = os.path.join(os.path.dirname(__file__), '..')
    sys.path.append(root)
    main(len(sys.argv), sys.argv, iter(sys.argv))
