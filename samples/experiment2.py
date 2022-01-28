# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

# Test stuff ------------------------------------------------------------------
from networkx.algorithms import components


def make_t1_netlist_from_graph(comps):
    t1_netlist = [comp.get_comp() for comp in comps]

    return t1_netlist

def make_graph_from_components(components):
    import faebryk as fy
    import faebryk.library.library as lib
    import faebryk.library.traits as traits

    class wrapper():
        def __init__(self, component: lib.Component) -> None:
            self.component = component
            self._setup_non_rec()

        def _setup_non_rec(self):
            import random
            c = self.component
            self.real = c.has_trait(traits.has_footprint) and c.has_trait(traits.has_footprint_pinmap)
            self.name = "COMP{}".format(random.random())
            self.value = c.get_trait(traits.has_type_description).get_type_description()
            self.properties = {}
            if self.real:
                self.properties["footprint"] = \
                    c.get_trait(traits.has_footprint).get_footprint().get_trait(
                        traits.has_kicad_footprint).get_kicad_footprint()

        def _get_comp(self):
            return {
                "name": self.name,
                "value": self.value,
                "real": self.real,
                "properties": self.properties,
                "neighbors": []
            }
        
        def get_comp(self):
            # only executed once
            neighbors = {}
            #TODO
            #pseudo
            #for pin, interface in self.get_trait(traits.has_defined_footprint_pinmap).get_pin_map():
            #  for target_interface in interface.connections:
            #      if target_interface has trait[has_component]
            #          target_component = target_interface.get_trait(...).get_component()
            #          target_pinmap = target_component.get_trait(...).get_pin_map()
            #          target_pin = target_pinmap.items()[target_pinmap.values().index(target_interface)]       
            #          target_wrapped = find(i.component == target_component for i in wrapped_list) 
            #          self.neighbors[pin].append({
            #              "vertex": target_wrapped._get_comp(),
            #              "pin": target_pin
            #          })

            comp = self._get_comp()
            comp["neighbors"] = neighbors

            return comp

    wrapped_list = list(map(wrapper, components))
    for i in wrapped_list:
        i.wrapped_list = wrapped_list

    return wrapped_list


def run_experiment():
    import faebryk as fy
    import faebryk.library.library as lib
    import faebryk.library.traits as traits
    from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
    from faebryk.exporters.netlist import make_t2_netlist_from_t1

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
        spacing_mm=3,
        long_pads=False
    )))
    for smd_comp in [led, pull_down_resistor, current_limiting_resistor]:
        smd_comp.add_trait(traits.has_defined_footprint(lib.SMDTwoPin(
            lib.SMDTwoPin.Type._0805
        )))
    
    for resistor in [pull_down_resistor, current_limiting_resistor]:
        smd_comp.add_trait(traits.has_defined_footprint_pinmap(
            {
                1: resistor.interfaces[0],
                2: resistor.interfaces[1],
            }
        ))
    led.add_trait(traits.has_defined_footprint_pinmap(
        {
            1: led.anode,
            2: led.cathode,
        }
    )) 

    switch_fp = lib.Footprint()
    switch_fp.add_trait(lib.has_kicad_manual_footprint("Panasonic_EVQPUJ_EVQPUA"))
    switch.add_trait(traits.has_defined_footprint(switch_fp))
    switch.add_trait(traits.has_defined_footprint_pinmap(
        {
            1: switch.interfaces[0],
            2: switch.interfaces[1],
        }
    ))

    # make graph
    #TODO
    components = [
        led, 
        pull_down_resistor,
        current_limiting_resistor,
        nand_ic,
        switch,
        #battery, #NOT SURE
    ]

    netlist = from_faebryk_t2_netlist(
        make_t2_netlist_from_t1(
            make_t1_netlist_from_graph(
                make_graph_from_components(components)
            )
        )
    )

    print("Experiment netlist:")
    print(netlist)

    #from faebryk.exporters.netlist import render_graph
    #render_graph(make_t1_netlist_from_graph(comps))

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
