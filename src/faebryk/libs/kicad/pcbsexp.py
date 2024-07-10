import logging
from dataclasses import dataclass, field
from enum import StrEnum, auto
from pathlib import Path
from typing import Optional

from dataclasses_json import CatchAll, Undefined, dataclass_json
from faebryk.libs.kicad.sexp_parser import JSON_File, SEXP_File, sexp_field

logger = logging.getLogger(__name__)


@dataclass_json(undefined=Undefined.INCLUDE)
@dataclass
class Project(JSON_File):
    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class _pcbnew:
        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class _last_paths:
            gencad: str = ""
            idf: str = ""
            netlist: str = ""
            plot: str = ""
            pos_files: str = ""
            specctra_dsn: str = ""
            step: str = ""
            svg: str = ""
            vrml: str = ""
            unknown: CatchAll = None

        last_paths: "_last_paths" = field(default_factory=_last_paths)
        unknown: CatchAll = None

    pcbnew: "_pcbnew" = field(default_factory=_pcbnew)
    unknown: CatchAll = None


# ---------------------------------------------------------------------
# Kicad SEXP subset
# only atom order is important
# multi-key dict


@dataclass
class C_Stroke:
    class E_type(StrEnum):
        solid = auto()

    width: float
    type: E_type


@dataclass
class C_effects:
    @dataclass
    class C_font:
        size: tuple[float, float]
        thickness: Optional[float] = None

    font: C_font


@dataclass
class C_footprint:
    class E_attr(StrEnum):
        smd = auto()
        through_hole = auto()

    @dataclass
    class C_property:
        name: str = field(**sexp_field(positional=True))
        value: str = field(**sexp_field(positional=True))
        at: tuple[float, float, float]
        layer: str
        uuid: str
        effects: C_effects
        hide: bool = False

    @dataclass
    class C_pad:
        class E_type(StrEnum):
            thru_hole = auto()
            smd = auto()

        class E_shape(StrEnum):
            circle = auto()
            rect = auto()
            roundrect = auto()

        name: str = field(**sexp_field(positional=True))
        type: E_type = field(**sexp_field(positional=True))
        shape: E_shape = field(**sexp_field(positional=True))
        at: tuple[float, float, float]
        size: tuple[float, float]
        layers: list[str]
        drill: Optional[float] = None
        remove_unused_layers: bool = False

    @dataclass
    class C_model:
        path: Path = field(**sexp_field(positional=True))

        @dataclass
        class C_offset:
            xyz: tuple[float, float, float]

        @dataclass
        class C_scale:
            xyz: tuple[float, float, float]

        @dataclass
        class C_rotate:
            xyz: tuple[float, float, float]

        offset: C_offset
        scale: C_scale
        rotate: C_rotate

    @dataclass
    class C_fp_line:
        start: tuple[float, float]
        end: tuple[float, float]
        stroke: C_Stroke
        layer: str
        uuid: str

    @dataclass
    class C_fp_circle:
        class E_fill(StrEnum):
            none = auto()

        center: tuple[float, float]
        end: tuple[float, float]
        stroke: C_Stroke
        fill: E_fill
        layer: str
        uuid: str

    @dataclass
    class C_fp_arc:
        start: tuple[float, float]
        mid: tuple[float, float]
        end: tuple[float, float]
        stroke: C_Stroke
        layer: str
        uuid: str

    @dataclass
    class C_fp_text:
        class E_type(StrEnum):
            user = auto()

        type: E_type = field(**sexp_field(positional=True))
        text: str = field(**sexp_field(positional=True))
        at: tuple[float, float, float]
        layer: str
        uuid: str
        effects: C_effects

    name: str = field(**sexp_field(positional=True))
    layer: str
    propertys: list[C_property] = field(**sexp_field(multidict=True))
    attr: E_attr
    fp_lines: list[C_fp_line] = field(**sexp_field(multidict=True))
    fp_arcs: list[C_fp_arc] = field(**sexp_field(multidict=True))
    fp_circles: list[C_fp_circle] = field(**sexp_field(multidict=True))
    fp_texts: list[C_fp_text] = field(**sexp_field(multidict=True))
    pads: list[C_pad] = field(**sexp_field(multidict=True))
    model: C_model


@dataclass
class C_kicad_pcb_file(SEXP_File):
    @dataclass
    class C_kicad_pcb:
        @dataclass
        class C_general:
            thickness: float
            legacy_teardrops: bool

        @dataclass
        class C_layer:
            class E_type(StrEnum):
                signal = auto()
                user = auto()

            number: int = field(**sexp_field(positional=True))
            name: str = field(**sexp_field(positional=True))
            type: E_type = field(**sexp_field(positional=True))
            alias: Optional[str] = field(**sexp_field(positional=True), default=None)

        @dataclass
        class C_setup:
            @dataclass
            class C_pcbplotparams:
                layerselection: str
                plot_on_all_layers_selection: str
                disableapertmacros: bool
                usegerberextensions: bool
                usegerberattributes: bool
                usegerberadvancedattributes: bool
                creategerberjobfile: bool
                dashed_line_dash_ratio: float
                dashed_line_gap_ratio: float
                svgprecision: int
                plotframeref: bool
                viasonmask: bool
                mode: int
                useauxorigin: bool
                hpglpennumber: int
                hpglpenspeed: int
                hpglpendiameter: float
                pdf_front_fp_property_popups: bool
                pdf_back_fp_property_popups: bool
                dxfpolygonmode: bool
                dxfimperialunits: bool
                dxfusepcbnewfont: bool
                psnegative: bool
                psa4output: bool
                plotreference: bool
                plotvalue: bool
                plotfptext: bool
                plotinvisibletext: bool
                sketchpadsonfab: bool
                subtractmaskfromsilk: bool
                outputformat: int
                mirror: bool
                drillshape: int
                scaleselection: int
                outputdirectory: str

            pad_to_mask_clearance: int
            allow_soldermask_bridges_in_footprints: bool
            pcbplotparams: C_pcbplotparams

        @dataclass
        class C_net:
            number: int = field(**sexp_field(positional=True))
            name: str = field(**sexp_field(positional=True))

        @dataclass
        class C_pcb_footprint(C_footprint):
            @dataclass
            class C_pad(C_footprint.C_pad):
                net: tuple[int, str] = field(kw_only=True)
                uuid: str = field(kw_only=True)

            at: tuple[float, float]
            uuid: str
            pads: list[C_pad] = field(**sexp_field(multidict=True))

        version: int
        generator: str
        generator_version: str
        general: C_general
        paper: str
        layers: list[C_layer]
        setup: C_setup
        nets: list[C_net] = field(**sexp_field(multidict=True))
        footprints: list[C_pcb_footprint] = field(**sexp_field(multidict=True))

    kicad_pcb: C_kicad_pcb


@dataclass
class C_kicad_footprint_file(SEXP_File):
    @dataclass
    class C_footprint_in_file(C_footprint):
        descr: str
        tags: list[str]
        version: str
        generator: str
        generator_version: str

    footprint: C_footprint


@dataclass
class C_fields:
    @dataclass
    class C_field:
        name: str
        value: Optional[str] = field(**sexp_field(positional=True), default=None)

    field: list[C_field] = field(**sexp_field(multidict=True))


@dataclass
class C_kicad_netlist_file(SEXP_File):
    @dataclass
    class C_netlist:
        @dataclass
        class C_components:
            @dataclass
            class C_component:
                @dataclass
                class C_property:
                    name: str
                    value: str

                @dataclass
                class C_libsource:
                    lib: str
                    part: str
                    description: str

                @dataclass
                class C_sheetpath:
                    names: str
                    tstamps: str

                ref: str
                value: str
                footprint: str
                fields: C_fields
                libsource: C_libsource
                propertys: list[C_property] = field(**sexp_field(multidict=True))
                sheetpath: C_sheetpath
                tstamps: str

            comps: list[C_component] = field(**sexp_field(multidict=True))

        @dataclass
        class C_nets:
            @dataclass
            class C_net:
                @dataclass
                class C_node:
                    ref: str
                    pin: str
                    pintype: str
                    pinfunction: Optional[str] = None

                code: int
                name: str
                node: list[C_node] = field(**sexp_field(multidict=True))

            nets: list[C_net] = field(**sexp_field(multidict=True))

        @dataclass
        class C_design:
            @dataclass
            class C_sheet:
                @dataclass
                class C_title_block:
                    @dataclass
                    class C_comment:
                        number: str
                        value: str

                    title: str
                    company: str
                    rev: str
                    date: str
                    source: str
                    comment: list[C_comment] = field(**sexp_field(multidict=True))

                number: str
                name: str
                tstamps: str
                title_block: C_title_block

            source: str
            date: str
            tool: str
            sheet: C_sheet

        @dataclass
        class C_libparts:
            @dataclass
            class C_libpart:
                @dataclass
                class C_footprints:
                    @dataclass
                    class C_fp:
                        fp: str = field(**sexp_field(positional=True))

                    fps: list[C_fp] = field(**sexp_field(multidict=True))

                @dataclass
                class C_pins:
                    @dataclass
                    class C_pin:
                        num: str
                        name: str
                        type: str

                    pin: list[C_pin] = field(**sexp_field(multidict=True))

                lib: str
                part: str
                fields: C_fields
                pins: Optional[C_pins] = None
                footprints: Optional[C_footprints] = None

            libparts: list[C_libpart] = field(**sexp_field(multidict=True))

        @dataclass
        class C_libraries:
            # TODO
            pass

        version: str
        design: C_design
        components: C_components
        libparts: C_libparts
        libraries: C_libraries
        nets: C_nets

    export: C_netlist
