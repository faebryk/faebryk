import sys
import logging
import re
import hashlib
import pprint
import parse
import black
import click

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("sym_gen")
logger.setLevel(logging.DEBUG)


def sanitize_name(raw):
    sanitized = raw
    # braces
    sanitized = sanitized.replace("(", "")
    sanitized = sanitized.replace(")", "")
    sanitized = sanitized.replace("[", "")
    sanitized = sanitized.replace("]", "")
    # seperators
    sanitized = sanitized.replace(".", "_")
    sanitized = sanitized.replace(",", "_")
    sanitized = sanitized.replace("/", "_")
    # special symbols
    sanitized = sanitized.replace("'", "")
    sanitized = sanitized.replace("*", "")
    sanitized = sanitized.replace("^", "p")
    sanitized = sanitized.replace("#", "h")
    sanitized = sanitized.replace("ϕ", "phase")
    sanitized = sanitized.replace("π", "pi")
    sanitized = sanitized.replace("&", "and")
    # inversion
    sanitized = sanitized.replace("~", "n")
    sanitized = sanitized.replace("{", "")
    sanitized = sanitized.replace("}", "")

    sanitized = sanitized.replace("->", "to")
    sanitized = sanitized.replace("<-", "from")
    # arithmetics
    sanitized = sanitized.replace(">", "gt")
    sanitized = sanitized.replace("<", "lt")
    sanitized = sanitized.replace("=", "eq")
    sanitized = sanitized.replace("+", "plus")
    sanitized = sanitized.replace("-", "minus")

    # rest
    def handle_unknown_invalid_symbold(match):
        logger.warning(
            "Replacing unknown invalid symbol {} in {} with _".format(
                match.group(0), raw
            )
        )
        return "_"

    sanitized = re.sub(r"[^a-zA-Z_0-9]", handle_unknown_invalid_symbold, sanitized)

    if re.match("^[a-zA-Z_]", sanitized) is None:
        sanitized = "_" + sanitized

    if re.match("^[a-zA-Z_]+[a-zA-Z_0-9]*$", sanitized) is not None:
        return sanitized

    to_escape = re.findall("[^a-zA-Z_0-9]", sanitized)
    if len(to_escape) > 0:
        return None, to_escape

    return sanitized


def generate_component(symbol, annotation_properties, keep_source):
    annotation = "\n    ".join(
        [f"{key}: {val}" for key, val in annotation_properties.items()]
    )
    raw_name = symbol["name"]
    name = sanitize_name(raw_name)
    if type(name) is tuple and name[0] is None:  # TODO use exception
        logger.error(f"Unescapable symbol name in {raw_name}: [{name[1]}]")

    parent = "Component"
    if "extends" in symbol:
        raw_parent = symbol["extends"]
        parent = sanitize_name(raw_parent)

    # interfaces
    raw_pins = {
        no: pin
        for symbol_2 in symbol.get("symbols", {}).values()
        for no, pin in symbol_2.get("pins", {}).items()
    }

    # not hidden pins
    pins = {no: pin for no, pin in raw_pins.items() if not pin["hide"]}

    # handle aliases
    for no, pin in raw_pins.items():
        match = [
            ppin
            for ppin in pins.values()
            if ppin["name"] == pin["name"] and ppin != pin
        ]
        if len(match) == 0:
            continue
        for ppin in match:
            ppin["aliases"].append(no)

        if no in pins:  # == if pin not hidden/filtered
            del pins[no]

    faebryk_if_map = {}
    unnamed_if_cnt = 0
    for no, pin in pins.items():
        if pin["name"] == "~":
            faebryk_if_map[no] = f"_unnamed[{unnamed_if_cnt}]"
            unnamed_if_cnt += 1
        else:
            pin_raw_name = pin["name"]
            pin_name = sanitize_name(pin_raw_name)
            if type(pin_name) is tuple and pin_name[0] is None:  # TODO use exception
                logger.error(
                    f"Unescapable pin name in pin {pin_raw_name}: [{pin_name[1]}] in symbol {name}"
                )
                return f"#Skipped invalid component {name}"

            faebryk_if_map[no] = pin_name

    ifs_exp = "\n        ".join(
        [
            f"self.IFs.{_if} = Electrical()"
            for pinno, _if in faebryk_if_map.items()
            if pins[pinno]["name"] != "~"
        ]
    )

    pinmap = dict(faebryk_if_map)
    for no, pin in faebryk_if_map.items():
        for aliased_no in pins[no]["aliases"]:
            pinmap[aliased_no] = pin

    # raw
    if keep_source:
        raw_symbol = pprint.pformat(symbol["_raw"], indent=4, width=88).replace(
            "\n", "\n        "
        )
    else:
        raw_symbol = "omitted"

    #
    class_traits = []
    instance_traits = []

    # footprint & footprint pinmap
    footprint_str = symbol["properties"]["Footprint"].replace('"', "")
    if footprint_str != "":
        footprint_trait = 'has_defined_footprint(KicadFootprint("{}"))'.format(
            footprint_str
        )
        class_traits.append(footprint_trait)
        pinmap_trait = "has_defined_footprint_pinmap({})".format(
            "{"
            + ", ".join([f'"{pinno}": self.IFs.{_if}' for pinno, _if in pinmap.items()])
            + "}"
        )
        instance_traits.append(pinmap_trait)

    #
    class_traits.append(
        'has_defined_kicad_ref("{}")'.format(symbol["properties"]["Reference"])
    )
    class_traits.append(f'has_defined_type_description("{raw_name}")')

    class_traits_exp = "\n        ".join(
        [f"self.add_trait({trait})" for trait in class_traits]
    )
    instance_traits_exp = "\n        ".join(
        [f"self.add_trait({trait})" for trait in instance_traits]
    )

    template = "\n".join(
        filter(
            lambda x: x is not None,
            [
                f"class {name}({parent}):",
                f'    """',
                f"    Generated by symbol_converter",
                f"    {annotation}",
                f"    source:",
                f"        {raw_symbol}",
                f'    """',
                f"",
                f"    def _setup_traits(self):",
                f"        super()._setup_traits()" if parent != "Component" else None,
                f"        {class_traits_exp}" if class_traits_exp != "" else None,
                f"        return",
                f"",
                f"    def _setup_interfaces(self):",
                f"        super()._setup_interfaces()"
                if parent != "Component"
                else None,
                f'        {f"self.IFs.add_all(times({unnamed_if_cnt}, Electrical))"}'
                if unnamed_if_cnt > 0
                else None,
                f"        {ifs_exp}" if ifs_exp != "" else None,
                f"        return",
                f"",
                f"    def __new__(cls, *args, **kwargs):",
                f"        self = super().__new__(cls)",
                f"        self._setup_traits()" if parent == "Component" else None,
                f"        return self",
                f"",
                f"    def __init__(self):",
                f"        super().__init__()",
                f"        self._setup_interfaces()" if parent == "Component" else None,
                f"        {instance_traits_exp}" if instance_traits_exp != "" else None,
                f"        return",
            ],
        )
    )
    return template


@click.command()
@click.option(
    "--keep-source",
    default=False,
    help="Insert netlist source into class as comment.",
    is_flag=True,
)
@click.argument("sourcefile", type=click.File("r"))
@click.argument("destfile", type=click.File("w"))
def main(sourcefile, destfile, keep_source):
    """
    Generates faebryk components from kicad symbols

    SOURCEPATH: Path to kicad symbol library file (.sym)

    DESTPATH: Path to generated file (.py)
    """

    logger.info("Parsing & Converting %s -> %s", sourcefile.name, destfile.name)

    raw_sexp = "".join(sourcefile.readlines())
    sourcefile.close()

    file_hash = hashlib.sha1(raw_sexp.encode("utf-8")).hexdigest()

    lib = parse.parse_symbol_lib(parse.parse_sexp(raw_sexp))
    logger.info("Found {} symbols".format(len(lib["symbols"])))

    components = [
        generate_component(
            symbol,
            {
                "filepath": sourcefile.name,
                "hash": file_hash,
            },
            keep_source,
        )
        for symbol in lib["symbols"].values()
    ]

    output = "\n".join(
        [
            '"""',
            "   Generated by symbol_converter",
            '"""',
            "",
            "from faebryk.library.core import Component",
            "from faebryk.library.library.interfaces import Electrical",
            "from faebryk.library.util import times",
            "from faebryk.library.traits.component import has_defined_footprint_pinmap, has_defined_footprint, has_defined_type_description",
            "from faebryk.library.kicad import has_defined_kicad_ref, KicadFootprint",
        ]
        + components
    )
    output = black.format_file_contents(output, fast=True, mode=black.Mode())

    destfile.write(output)


if __name__ == "__main__":
    main()
