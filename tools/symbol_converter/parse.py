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


def parse_sexp(sexp):
    parsed = loads(sexp)
    parsed = _cleanparsed(parsed)

    return parsed


# DUMB WAY
def parse_symbol_lib(obj):
    assert obj[0] == "kicad_symbol_lib"
    lib = {}

    def parse_symbol(obj):
        if "symbols" not in lib:
            lib["symbols"] = {}
        symbol = {}
        name = obj[1]
        symbol["name"] = name
        symbol["_raw"] = obj

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
                    elif type(i) is tuple and i[0] in ["at", "length"]:
                        pass
                    elif type(i) is tuple and i[0] == "name":
                        pin["name"] = i[1]
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
                parse_pin_name(i)
            elif key == "property":
                parse_property(i)
            elif key == "symbol":
                parse_symbol_2(i)
            elif key == "power":
                symbol[key] = True
            else:
                assert (
                    False
                ), f"encountered unexpected token [{i}] in symbol [{name}]:[{obj}]"

        lib["symbols"][name] = symbol

    for i in obj[1:]:
        key = i[0]
        if key in ["version", "generator"]:
            lib[key] = i[1]
        elif key == "symbol":
            parse_symbol(i)
        else:
            assert False, f"encountered unexpected token [{i}] in symbollib"

    return lib
