import logging
from dataclasses import Field, dataclass, fields, is_dataclass
from pathlib import Path
from types import GenericAlias
from typing import Any, TypeVar

import sexpdata
from faebryk.libs.util import groupby
from sexpdata import Symbol

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Kicad SEXP subset
# only atom order is important
# multi-key dict


@dataclass
class sexp_field(dict[str, Any]):
    positional: bool = False
    multidict: bool = False

    def __post_init__(self):
        super().__init__({"metadata": {"sexp": self}})

        assert not (self.positional and self.multidict)

    @classmethod
    def from_field(cls, f: Field):
        out = f.metadata.get("sexp", cls())
        assert isinstance(out, cls)
        return out


T = TypeVar("T")


def _convert(_v, _t):
    if isinstance(_t, GenericAlias) and _t.__origin__ == list:
        return [_convert(__v, _t.__args__[0]) for __v in _v]
    elif isinstance(_t, GenericAlias) and _t.__origin__ == tuple:
        return tuple(_convert(__v, __t) for __v, __t in zip(_v, _t.__args__))
    elif _t.__name__ == "Optional":
        return _convert(_v, _t.__args__[0]) if _v is not None else None
    elif _t.__name__ == "Union":
        raise NotImplementedError(
            "Unions not supported, if you want to use '| None' use Optional instead"
        )
    elif is_dataclass(_t):
        return _parse(_v, _t)
    elif isinstance(_v, Symbol):
        return _t(str(_v))
    else:
        return _t(_v)


def _parse(sexp: list[str | Symbol | int | float | bool], t: type[T]) -> T:
    logger.debug(f"parse into: {t.__name__} {'-'*40}")
    logger.debug(f"sexp: {sexp}")

    # check if t is dataclass type
    if not hasattr(t, "__dataclass_fields__"):
        raise TypeError(f"{t} is not a dataclass type")

    value_dict = {}

    # Fields
    fs = fields(t)
    simple_key_fields = {
        Symbol(f.name): f
        for f in fs
        if not (sf := sexp_field.from_field(f)).positional and not sf.multidict
    }
    multi_key_fields = {f.name: f for f in fs if sexp_field.from_field(f).multidict}
    positional_fields = {
        i: f for i, f in enumerate(fs) if sexp_field.from_field(f).positional
    }

    logger.debug(f"simple_key_fields: {list(simple_key_fields.keys())}")
    logger.debug(f"multi_key_fields: {list(multi_key_fields.keys())}")
    logger.debug(
        f"positional_fields: {list(f.name for f in positional_fields.values())}"
    )

    # Values
    key_values = {
        val[0]: val
        for val in sexp
        if isinstance(val, list)
        and len(val)
        and isinstance(key := val[0], Symbol)
        and key in simple_key_fields
    }
    multi_key_values = groupby(
        (
            val
            for val in sexp
            if isinstance(val, list)
            and len(val)
            and isinstance(key := val[0], Symbol)
            and str(key) + "s" in multi_key_fields
        ),
        lambda val: str(val[0]) + "s",
    )
    pos_values = {
        i: val
        for i, val in enumerate(sexp)
        if isinstance(val, (str, int, float, Symbol, bool))
        or (isinstance(val, list) and (not len(val) or not isinstance(val[0], Symbol)))
        # and i in positional_fields
        # and positional_fields[i].name not in value_dict
    }

    logger.debug(f"key_values: {list(key_values.keys())}")
    logger.debug(f"pos_values: {pos_values}")

    # Parse
    for s_name, f in simple_key_fields.items():
        name = f.name
        if s_name not in key_values:
            # TODO remove
            logger.warning(f"missing key: {s_name}")
            # will be automatically filled by factory
            continue

        val: list[str | Symbol | int | float | bool] = key_values[s_name][1:]
        assert all(isinstance(v, (str, int, float, Symbol, bool, list)) for v in val)

        value_dict[name] = _convert(
            val[0] if len(val) == 1 and not isinstance(val[0], list) else val, f.type
        )

    for s_name, f in multi_key_fields.items():
        name = f.name
        if s_name not in multi_key_values:
            # TODO remove
            logger.warning(f"missing key: {s_name}")
            # will be automatically filled by factory
            continue

        out = []
        for _val in multi_key_values[s_name]:
            logger.debug(f"multi_key_values: {_val}")
            val: list[list[str | Symbol | int | float | bool]] = _val[1:]
            assert all(
                isinstance(v, (str, int, float, Symbol, bool, list)) for v in val
            )

            assert isinstance(f.type, GenericAlias)
            out.append(
                _convert(
                    val[0] if len(val) == 1 and not isinstance(val[0], list) else val,
                    f.type.__args__[0],
                )
            )
        value_dict[name] = out

    for (i1, f), (i2, v) in zip(positional_fields.items(), pos_values.items()):
        name = f.name
        value_dict[name] = _convert(v, f.type)

    logger.debug(f"value_dict: {value_dict}")

    return t(**value_dict)


def loads(s: str | Path | list, t: type[T]) -> T:
    text = s
    sexp = s
    if isinstance(s, Path):
        text = s.read_text()
    if isinstance(text, str):
        sexp = sexpdata.loads(text)

    return _parse([sexp], t)


class SEXP_File:
    @classmethod
    def loads(cls, path_or_string_or_data: Path | str | list):
        return loads(path_or_string_or_data, cls)

    def dump(self, obj):
        raise NotImplementedError()
