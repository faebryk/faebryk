import logging
from dataclasses import dataclass, field
from enum import StrEnum, auto
from pathlib import Path
from typing import Optional

from dataclasses_json import CatchAll, Undefined, dataclass_json
from faebryk.libs.kicad.sexp_parser import SEXP_File, sexp_field

logger = logging.getLogger(__name__)


@dataclass_json(undefined=Undefined.INCLUDE)
@dataclass
class Project:
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

    @classmethod
    def load(cls, path: Path) -> "Project":
        return cls.from_json(path.read_text())

    def dump(self, path: Path):
        return path.write_text(self.to_json(indent=4))


# ---------------------------------------------------------------------
# Kicad SEXP subset
# only atom order is important
# multi-key dict


@dataclass
class C_Stroke:
    class E_type(StrEnum):
        solid = auto()

    width: str
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
    fp_circles: list[C_fp_circle] = field(**sexp_field(multidict=True))
    fp_texts: list[C_fp_text] = field(**sexp_field(multidict=True))
    pads: list[C_pad] = field(**sexp_field(multidict=True))
    model: C_model


@dataclass
class C_pcb_footprint(C_footprint):
    @dataclass
    class C_pad(C_footprint.C_pad):
        net: tuple[int, str] = field(kw_only=True)
        uuid: str = field(kw_only=True)

    at: tuple[float, float]
    uuid: str
    pads: list[C_pad] = field(**sexp_field(multidict=True))


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
                layerselection: int
                plot_on_all_layers_selection: int
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

        version: int
        generator: str
        generator_version: str
        general: C_general
        paper: str
        layers: list[C_layer]
        nets: list[C_net] = field(**sexp_field(multidict=True))
        footprints: list[C_footprint] = field(**sexp_field(multidict=True))

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
