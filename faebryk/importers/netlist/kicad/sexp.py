# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from sexpdata import loads, SExpBase

logger = logging.getLogger("sexp")


def _cleanparsed(parsed):
    if isinstance(parsed, SExpBase):
        return parsed.value()

    if type(parsed) is list:
        return tuple(map(_cleanparsed, parsed))

    return parsed


def dumb_parse(obj):
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


def parse_sexp(sexp):
    parsed = loads(sexp)
    parsed = _cleanparsed(parsed)
    parsed = dumb_parse(parsed)

    return parsed
