# Test stuff ------------------------------------------------------------------
def make_t1_netlist_from_graph(comps):
    t1_netlist = [comp.get_comp() for comp in comps]

    return t1_netlist


from library import *
from netlist.kicad_netlist import from_faebryk_t2_netlist
from netlist.netlist import make_t2_netlist_from_t1
def run_experiment():
    gnd = VirtualComponent(
        name="GND",
        pins=[1],
    )

    vcc = VirtualComponent(
        name="+3V3",
        pins=[1],
    )

    comps = [gnd, vcc]
    netlist = from_faebryk_t2_netlist(
        make_t2_netlist_from_t1(
            make_t1_netlist_from_graph(comps)
        )
    )

    print("Experiment netlist:")
    print(netlist)