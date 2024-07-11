import logging
from dataclasses import Field, dataclass, fields, is_dataclass
from enum import Enum
from pathlib import Path
from types import GenericAlias
from typing import Any, Callable, TypeVar

import sexpdata
from faebryk.libs.sexp.util import prettify_sexp_string
from faebryk.libs.util import duplicates, groupby
from sexpdata import Symbol

logger = logging.getLogger(__name__)

# TODO: Should be its own repo

"""
This is a generic sexp-dataclass converter (similar to dataclass_json).
It is used to convert between dataclasses and sexp (s-expressions).
It only supports a specific subset of sexp that is used by KiCAD with following rules:
- Only atom order is important
- Multi-key dict is supported
"""


@dataclass
class sexp_field(dict[str, Any]):
    positional: bool = False
    multidict: bool = False
    key: Callable[[Any], Any] | None = None

    def __post_init__(self):
        super().__init__({"metadata": {"sexp": self}})

        assert not (self.positional and self.multidict)
        assert (self.key is None) or self.multidict, "Key only supported for multidict"

    @classmethod
    def from_field(cls, f: Field):
        out = f.metadata.get("sexp", cls())
        assert isinstance(out, cls)
        return out


T = TypeVar("T")


def _convert(val, t):
    if isinstance(t, GenericAlias) and t.__origin__ == list:
        return [_convert(_val, t.__args__[0]) for _val in val]
    if isinstance(t, GenericAlias) and t.__origin__ == tuple:
        return tuple(_convert(_val, _t) for _val, _t in zip(val, t.__args__))
    if t.__name__ == "Optional":
        return _convert(val, t.__args__[0]) if val is not None else None
    if t.__name__ == "Union":
        raise NotImplementedError(
            "Unions not supported, if you want to use '| None' use Optional instead"
        )
    if is_dataclass(t):
        return _decode(val, t)
    if issubclass(t, bool):
        assert val in [Symbol("yes"), Symbol("no")]
        return val == Symbol("yes")
    if isinstance(val, Symbol):
        return t(str(val))

    return t(val)


netlist_obj = str | Symbol | int | float | bool | list
netlist_type = list[netlist_obj]


def _decode(sexp: netlist_type, t: type[T]) -> T:
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"parse into: {t.__name__} {'-'*40}")
        logger.debug(f"sexp: {sexp}")

    # check if t is dataclass type
    if not hasattr(t, "__dataclass_fields__"):
        # is_dataclass(t) trips mypy
        raise TypeError(f"{t} is not a dataclass type")

    value_dict = {}

    # Fields
    fs = fields(t)
    key_fields = {f.name: f for f in fs if not sexp_field.from_field(f).positional}
    positional_fields = {
        i: f for i, f in enumerate(fs) if sexp_field.from_field(f).positional
    }

    # Values
    key_values = groupby(
        (
            val
            for val in sexp
            if isinstance(val, list)
            and len(val)
            and isinstance(key := val[0], Symbol)
            and (str(key) + "s" in key_fields or str(key) in key_fields)
        ),
        lambda val: str(val[0]) + "s"
        if str(val[0]) + "s" in key_fields
        else str(val[0]),
    )
    pos_values = {
        i: val
        for i, val in enumerate(sexp)
        if isinstance(val, (str, int, float, Symbol, bool))
        or (isinstance(val, list) and (not len(val) or not isinstance(val[0], Symbol)))
        # and i in positional_fields
        # and positional_fields[i].name not in value_dict
    }

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"key_fields: {list(key_fields.keys())}")
        logger.debug(
            f"positional_fields: {list(f.name for f in positional_fields.values())}"
        )
        logger.debug(f"key_values: {list(key_values.keys())}")
        logger.debug(f"pos_values: {pos_values}")

    # Parse
    for s_name, f in key_fields.items():
        name = f.name
        sp = sexp_field.from_field(f)
        if s_name not in key_values:
            if sp.multidict:
                value_dict[name] = []
            # will be automatically filled by factory
            continue

        def _parse_single(kval, t_):
            logger.debug(f"key_val: {kval}")
            val: list[list[str | Symbol | int | float | bool]] = kval[1:]
            assert all(
                isinstance(v, (str, int, float, Symbol, bool, list)) for v in val
            )

            return _convert(
                val[0] if len(val) == 1 and not isinstance(val[0], list) else val,
                t_,
            )

        values = key_values[s_name]
        if sp.multidict:
            if isinstance(f.type, GenericAlias) and f.type.__origin__ is list:
                val_t = f.type.__args__[0]
                value_dict[name] = [_parse_single(_val, val_t) for _val in values]
            elif isinstance(f.type, GenericAlias) and f.type.__origin__ is dict:
                if not sp.key:
                    raise ValueError(f"Key function required for multidict: {f.name}")
                key_t = f.type.__args__[0]
                val_t = f.type.__args__[1]
                converted_values = [_parse_single(_val, val_t) for _val in values]
                values_with_key = [(sp.key(_val), _val) for _val in converted_values]

                if not all(isinstance(k, key_t) for k, _ in values_with_key):
                    raise KeyError(
                        f"Key function returned invalid type in field {f.name}:"
                        f" {key_t=} types={[v[0] for v in values_with_key]}"
                    )
                if d := duplicates(values_with_key, key=lambda v: v[0]):
                    raise ValueError(f"Duplicate keys: {d}")
                value_dict[name] = dict(values_with_key)
            else:
                raise NotImplementedError(f"Multidict not supported for {f.type}")
        else:
            assert len(values) == 1, f"Duplicate key: {name}"
            value_dict[name] = _parse_single(values[0], f.type)

    for (i1, f), (i2, v) in zip(positional_fields.items(), pos_values.items()):
        name = f.name
        value_dict[name] = _convert(v, f.type)

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"value_dict: {value_dict}")

    try:
        return t(**value_dict)
    except TypeError as e:
        raise TypeError(f"Failed to create {t} with {value_dict}") from e


def _convert2(val: Any) -> netlist_obj | None:
    if val is None:
        return None
    if is_dataclass(val):
        return _encode(val)
    if isinstance(val, list):
        return [_convert2(v) for v in val]
    if isinstance(val, tuple):
        return [_convert2(v) for v in val]
    if isinstance(val, dict):
        return [_convert2(v) for v in val.values()]
    if isinstance(val, Enum):
        return Symbol(val)
    if isinstance(val, bool):
        return Symbol("yes" if val else "no")
    if isinstance(val, float):
        if val.is_integer():
            return int(val)
        return val
    if isinstance(val, (str, int)):
        return val

    return str(val)


def _encode(t) -> netlist_type:
    if not is_dataclass(t):
        raise TypeError(f"{t} is not a dataclass type")

    sexp: netlist_type = []

    def _append(_val):
        if val is None:
            return
        sexp.append(_val)

    for f in fields(t):
        name = f.name
        val = getattr(t, name)
        sp = sexp_field.from_field(f)

        if sp.positional:
            _append(_convert2(val))
            continue

        def _append_kv(name, v):
            converted = _convert2(v)
            if converted is None:
                return
            if isinstance(converted, list):
                _append([Symbol(name), *converted])
                return
            _append([Symbol(name), converted])

        if sp.multidict:
            if isinstance(val, list):
                assert f.type.__origin__ is list
                _val = val
            elif isinstance(val, dict):
                assert f.type.__origin__ is dict
                _val = val
                _val = val.values()
            else:
                raise TypeError()
            for v in _val:
                _append_kv(f.name.removesuffix("s"), v)
        else:
            _append_kv(f.name, val)

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Dumping {type(t).__name__} {'-'*40}")
        logger.debug(f"Obj: {t}")
        logger.debug(f"Sexp: {sexp}")

    return sexp


def loads(s: str | Path | list, t: type[T]) -> T:
    text = s
    sexp = s
    if isinstance(s, Path):
        text = s.read_text()
    if isinstance(text, str):
        sexp = sexpdata.loads(text)

    return _decode([sexp], t)


def dumps(obj, path: Path | None = None) -> str:
    sexp = _encode(obj)[0]
    text = sexpdata.dumps(sexp)
    text = prettify_sexp_string(text)
    if path:
        path.write_text(text)
    return text


def insert(root, node):
    key = type(node).__name__.removeprefix("C_")

    if key + "s" in root:
        target = getattr(root, key + "s")
        assert isinstance(target, list)
        target.append(node)
        return

    raise ValueError()


class SEXP_File:
    @classmethod
    def loads(cls, path_or_string_or_data: Path | str | list):
        return loads(path_or_string_or_data, cls)

    def dumps(self, path: Path | None = None):
        return dumps(self, path)


# TODO move
class JSON_File:
    @classmethod
    def loads(cls: type[T], path: Path | str) -> T:
        text = path
        if isinstance(path, Path):
            text = path.read_text()
        return cls.from_json(text)

    def dumps(self, path: Path | None = None):
        text = self.to_json(indent=4)
        if path:
            path.write_text(text)
        return text
