# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.exporters.netlist import Vertex, Net, Component
from faebryk.libs.algorithm import ufds
from faebryk.libs.kicad.parser import parse_kicad_schematic, setup_dict


def to_faebryk_t2_netlist(kicad_schematic):
    # t2_netlist = [(properties, vertices=[(comp=(name, value, properties), pin)])]

    # kicad_netlist = {
    #   comps:  [(ref, value, fp, tstamp)],
    #   nets:   [(code, name, [node=(ref, pin)])],
    # }

    schematic = parse_kicad_schematic(kicad_schematic)

    import pprint
    #pprint.pprint(schematic, indent=4)
    from pathlib import Path
    path = Path("./build/faebryk_sch")
    path.write_text(pprint.pformat(schematic, indent=4))

    def subname_to_tpl(subname: str):
        split = subname.split("_")
        return split[-2], split[-1]

    pins = {
        #lib_name: pins
        name: {
            #modname: pins
            subname_to_tpl(subname): 
            subsym.get("pins", {})
            for subname, subsym in lib_sym["symbols"].items()
        }
        for name, lib_sym in schematic["lib_symbols"].items()
    }

    pprint.pprint(pins, indent=4)

    def get_pins(ref, sym, subsym, unit):
        convert = subsym.get("convert", 1)
        lib_name = subsym["lib_id"]
        base_coord = subsym["at"]
        mirror = subsym.get("mirror", None)
        # symbol coordinate system has inverted y-axis to sch coord system??
        mirror_vec = (1, -1) if mirror is None else (-1, -1) if mirror == "x" else (1, 1) if mirror == "y" else None
        assert (mirror_vec is not None)

        obj = {
            "ref": ref,
            "lib_name": lib_name,
        }

        raw_pins = {}

        for u in ["0", str(unit)]:
            for c in ["0", str(convert)]:
                raw_pins.update(pins[lib_name].get((u, c),{}))

        def translate_pin(pin):
            out = dict(pin)
            x,y = pin["at"]
            x,y = mirror_vec[0]*x, mirror_vec[1]*y

            import math
            angle = -base_coord[2]/360 * 2 * math.pi
            cos = math.cos(angle)
            sin = math.sin(angle)
            rx,ry = x*cos - y*sin, x*sin+y*cos
            out["at"] = (round(rx+base_coord[0],2), round(ry+base_coord[1],2))
            return out

        translated_pins = {
            pin_name: translate_pin(pin)
            for pin_name, pin in raw_pins.items()
        }

        obj["pins"] = translated_pins

        return obj


    sym_pins = [
        get_pins(ref, sym, subsym, unit)
        for ref, sym in schematic["symbols"].items()
        for unit, subsym in sym.items()
    ]

    pprint.pprint(sym_pins, indent=4)

    # organize by coords
    coords = {}
    #coord: [(ref, pin_name, pin)]
    for pins in sym_pins:
        for pin_name, pin in pins["pins"].items():
            coord = pin["at"]
            if coord not in coords:
                coords[coord] = []
            coords[coord].append((pins["ref"], pin_name, pin))

    pprint.pprint(coords, indent=4)

    # create the extra coords for the set
    for wire in schematic["wires"]:
        pts = wire["points"]
        for coord in pts:
            if coord not in coords:
                coords[coord] = []


    union = ufds()
    union.make_set(coords.keys())


    for wire in schematic["wires"]:
        pts = wire["points"]
        
        for coord in pts:
            union.op_union(pts[0], coord)

    merged = {}
    for coord, cpins in coords.items():
        ptr = union.op_find(coord)
        if ptr not in merged:
            merged[ptr] = []
        merged[ptr] += cpins
    
    print("-"*80)
    pprint.pprint(merged, indent=4)


    #components = {
    #    comp["ref"]: Component(
    #        name=comp["ref"],
    #        value=comp["value"],
    #        properties={"footprint": comp["footprint"]},
    #    )
    #    for comp in netlist["components"].values()
    #}

    #t2_netlist = [
    #    Net(
    #        properties={
    #            "name": net["name"],
    #        },
    #        vertices=[
    #            Vertex(
    #                component=components[node["ref"]],
    #                pin=node["pin"],
    #            )
    #            for node in net["nodes"]
    #        ],
    #    )
    #    for net in netlist["nets"].values()
    #]

    #return t2_netlist
    return None
