# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from abc import abstractmethod
import string
from textwrap import wrap
from typing import Any, Iterable, List, Type


class lazy:
    def __init__(self, expr):
        self.expr = expr

    def __str__(self):
        return str(self.expr())

    def __repr__(self):
        return repr(self.expr())


def kw2dict(**kw):
    return dict(kw)


class hashable_dict:
    def __init__(self, obj: dict):
        self.obj = obj

    def __hash__(self):
        return hash(sum(map(hash, self.obj.items())))

    def __repr__(self):
        return "{}({})".format(type(self), repr(self.obj))

    def __eq__(self, other):
        return hash(self) == hash(other)


def unique(it, key):
    seen = []
    out = []
    for i in it:
        v = key(i)
        if v in seen:
            continue
        seen.append(v)
        out.append(i)
    return out


def get_dict(obj, key, default):
    if key not in obj:
        obj[key] = default()

    return obj[key]


def flatten(obj, depth=1):
    if depth == 0:
        return obj
    return [flatten(nested, depth=depth - 1) for top in obj for nested in top]


class NotifiesOnPropertyChange(object):
    def __init__(self, callback) -> None:
        self.callback = callback

        # TODO dir -> vars?
        for name in dir(self):
            self.callback(name, getattr(self, name))

    def __setattr__(self, __name, __value) -> None:
        super().__setattr__(__name, __value)

        # before init
        if hasattr(self, "callback"):
            self.callback(__name, __value)


# def Holder(_type: Type):
#    def decorate(cls: Type):


def Holder(_type: Type):
    class wrapper(NotifiesOnPropertyChange):
        def __init__(self) -> None:
            self._list: List[_type] = []

            super().__init__(self._callback)

        def _callback(self, name: str, value: Any):
            if name.startswith("_"):
                return
            if isinstance(value, _type):
                self._list.append(value)
                self.handle_add(value)
                return

            if isinstance(value, Iterable):
                if not all(map(lambda x: isinstance(x, _type), value)):
                    # TODO maybe warning on any?
                    return

                self._list += value
                for instance in value:
                    self.handle_add(instance)
                return

        def get_all(self) -> List[_type]:
            # TODO fix list stuff to use this
            # return self._list

            out: List[_type] = []

            for name in dir(self):
                value = getattr(self, name)
                if name.startswith("_"):
                    continue
                if isinstance(value, _type):
                    out.append(value)
                    continue
                if isinstance(value, Iterable):
                    if not all(map(lambda x: isinstance(x, _type), value)):
                        continue
                    out += list(value)
                    continue

            return out

        def handle_add(self, obj: _type):
            pass

    return wrapper
    #    return type(f"{cls.__name__}Holder", (cls, wrapper,), {})

    # return decorate
