# import sexp_parser
from sexpdata import loads, SExpBase
import re
import logging

logger = logging.getLogger("parse")


def _cleanparsed(parsed):
    if isinstance(parsed, SExpBase):
        return parsed.value()

    if type(parsed) is list:
        return tuple(map(_cleanparsed, parsed))

    return parsed


def setup_dict(obj, key):
    if key not in obj:
        obj[key] = {}

    return obj[key]


# -----------------------------------------------------------------------------


def parse_kicad_symbol_lib(sexp):
    parsed = loads(sexp)
    parsed = _cleanparsed(parsed)
    parsed = parse_symbol_lib(parsed)

    return parsed


def parse_kicad_netlist(sexp):
    parsed = loads(sexp)
    parsed = _cleanparsed(parsed)
    parsed = parse_netlist(parsed)

    return parsed


def parse_kicad_schematic(sexp):
    parsed = loads(sexp)
    parsed = _cleanparsed(parsed)
    parsed = parse_schematic(parsed)

    return parsed


# -----------------------------------------------------------------------------


def parse_symbol(obj):
    symbol = {}
    name = obj[1]
    symbol["name"] = name
    # symbol["_raw"] = obj
    # TODO reenable

    def parse_pin_name(obj):
        pin_names = {}
        for i in obj[1:]:
            if type(i) is tuple and i[0] in ["offset"]:
                pin_names[i[0]] = i[1]
            elif i == "hide":
                pin_names[i] = True
            else:
                assert False
        symbol["pin_names"] = pin_names

    def parse_property(obj):
        if "properties" not in symbol:
            symbol["properties"] = {}

        key = obj[1]
        val = obj[2]
        symbol["properties"][key] = val
        # rest dont care tbh

    def parse_symbol_2(obj):
        if "symbols" not in symbol:
            symbol["symbols"] = {}
        symbol_2 = {}
        name = obj[1]
        symbol_2["name"] = name

        def parse_pin(obj):
            if "pins" not in symbol_2:
                symbol_2["pins"] = {}

            pin = {}
            pin["type"] = obj[1]  # TODO not sure
            pin["hide"] = False
            pin["aliases"] = []
            key = None

            for i in obj[2:]:
                if i in [
                    "line",
                    "inverted",
                    "clock",
                    "inverted_clock",
                    "low",
                    "clock_low",
                    "input_low",
                    "output_low",
                    "falling_edge_clock",
                ]:
                    pass
                elif type(i) is tuple and i[0] in ["length"]:
                    pass
                elif type(i) is tuple and i[0] in "name":
                    pin["name"] = i[1]
                elif type(i) is tuple and i[0] in "at":
                    pin[i[0]] = i[1:3]
                elif type(i) is tuple and i[0] == "number":
                    key = i[1]
                    pin["number"] = i[1]
                elif type(i) is tuple and i[0] == "alternate":
                    # no idea what this is
                    pass
                elif i == "hide":
                    pin["hide"] = True
                else:
                    assert (
                        False
                    ), f"encountered unexpected token [{i}] in pin [{obj}] symbol [{symbol}]"

            symbol_2["pins"][key] = pin

        for i in obj[2:]:
            if type(i) is tuple and i[0] in ["pin"]:
                parse_pin(i)
            elif type(i) is tuple and i[0] in [
                "rectangle",
                "polyline",
                "text",
                "arc",
                "circle",
            ]:
                pass
            else:
                assert False, i

        symbol["symbols"][name] = symbol_2

    for i in obj[2:]:
        key = i[0]
        if key in ["pin_numbers", "in_bom", "on_board", "extends"]:
            symbol[key] = i[1]
        elif key == "pin_names":
            #parse_pin_name(i)
            pass #TODO test
        elif key == "property":
            parse_property(i)
        elif key == "symbol":
            parse_symbol_2(i)
        elif key == "power":
            #symbol[key] = True
            pass
        else:
            assert (
                False
            ), f"encountered unexpected token [{i}] in symbol [{name}]:[{obj}]"

    return symbol


# -----------------------------------------------------------------------------


def parse_symbol_lib(obj):
    assert obj[0] == "kicad_symbol_lib"
    lib = {}
    lib["symbols"] = {}

    for i in obj[1:]:
        key = i[0]
        if key in ["version", "generator"]:
            lib[key] = i[1]
        elif key == "symbol":
            symbol = parse_symbol(i)
            lib["symbols"][symbol["name"]] = symbol
        else:
            assert False, f"encountered unexpected token [{i}] in symbollib"

    return lib


def parse_netlist(obj):
    assert obj[0] == "export"
    netlist = {}

    def parse_components(obj):
        assert obj[0] == "components"
        components = {}

        def parse_comp(obj):
            assert obj[0] == "comp"
            comp = {}

            for i in obj[1:]:
                key = i[0]
                if key in [
                    "tstamp",
                    "tstamps",
                    "sheetpath",
                    "property",
                    "libsource",
                    "datasheet",
                ]:
                    pass
                elif key in ["ref", "value", "footprint"]:
                    comp[key] = i[1]
                else:
                    assert False, f"encountered unexpected token [{i}] in comp"

            components[comp["ref"]] = comp

        for i in obj[1:]:
            key = i[0]
            if key in ["comp"]:
                parse_comp(i)
            else:
                assert False, f"encountered unexpected token [{i}] in components"

        netlist["components"] = components

    def parse_nets(obj):
        assert obj[0] == "nets"
        nets = {}

        def parse_net(obj):
            assert obj[0] == "net"
            net = {}
            net["nodes"] = []

            def parse_node(obj):
                assert obj[0] == "node"
                node = {}

                for i in obj[1:]:
                    key = i[0]
                    if key in ["pintype", "pinfunction"]:
                        pass
                    elif key in ["ref", "pin"]:
                        node[key] = i[1]
                    else:
                        assert False, f"encountered unexpected token [{i}] in node"

                net["nodes"].append(node)

            for i in obj[1:]:
                key = i[0]
                if key in ["code"]:
                    pass
                elif key in ["name"]:
                    net[key] = i[1]
                elif key in ["node"]:
                    parse_node(i)
                else:
                    assert False, f"encountered unexpected token [{i}] in net"

            nets[net["name"]] = net

        for i in obj[1:]:
            key = i[0]
            if key in ["net"]:
                parse_net(i)
            else:
                assert False, f"encountered unexpected token [{i}] in components"

        netlist["nets"] = nets

    for i in obj[1:]:
        key = i[0]
        if key in ["version"]:
            netlist[key] = i[1]
        elif key in ["design"]:
            pass
        elif key in ["components"]:
            parse_components(i)
        elif key in ["nets"]:
            parse_nets(i)
        elif key in ["libparts", "libraries"]:
            pass
        else:
            assert False, f"encountered unexpected token [{i}] in netlist"

    return netlist


def parse_schematic(obj):
    assert obj[0] == "kicad_sch"
    schematic = {}
    schematic["wires"] = []
    schematic["symbols"] = {}

    def parse_wire(obj):
        assert obj[0] == "wire"
        wire = {}

        def parse_pts(obj):
            assert obj[0] == "pts"
            pts = []

            for i in obj[1:]:
                key = i[0]
                if key in ["xy"]:
                    pts.append((i[1], i[2]))
                else:
                    assert False, f"encountered unexpected token [{i}] in pts"

            wire["points"] = pts

        for i in obj[1:]:
            key = i[0]
            if key in ["stroke", "type", "color", "uuid"]:
                pass
            elif key in ["pts"]:
                parse_pts(i)
            else:
                assert False, f"encountered unexpected token [{i}] in wire"

        schematic["wires"].append(wire)

    def parse_sch_symbol(obj):
        assert obj[0] == "symbol"
        symbol = {}
        symbol["properties"] = {}

        for i in obj[1:]:
            key = i[0]
            if key in ["in_bom", "on_board", "fields_autoplaced", "uuid", "pin"]:
                pass
            elif key in ["at", "unit", "lib_id", "convert", "mirror"]:
                symbol[key] = i[1:] if len(i[1:]) > 1 else i[1]
            elif key in ["property"]:
                symbol["properties"][i[1]] = i[2]
            else:
                assert False, f"encountered unexpected token [{i}] in symbol"

        setup_dict(schematic["symbols"], symbol["properties"]["Reference"])[
            symbol["unit"]
        ] = symbol

    def parse_lib_symbols(obj):
        assert obj[0] == "lib_symbols"
        symbols = {}

        for i in obj[1:]:
            key = i[0]
            if key in ["symbol"]:
                symbol = parse_symbol(i)
                symbols[symbol["name"]] = symbol
            else:
                assert False, f"encountered unexpected token [{i}] in lib_symbols"

        schematic["lib_symbols"] = symbols

    for i in obj[1:]:
        key = i[0]
        if key in ["version"]:
            schematic[key] = i[1]
        elif key in ["lib_symbols"]:
            parse_lib_symbols(i)
        elif key in ["wire"]:
            parse_wire(i)
        elif key in ["symbol"]:
            parse_sch_symbol(i)
        elif key in [
            "generator",
            "uuid",
            "paper",
            "junction",
            "symbol_instances",
            "sheet_instances",
        ]:
            pass
        else:
            assert False, f"encountered unexpected token [{i}] in schematic"

    return schematic
