# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import inspect
import logging
from abc import abstractmethod
from collections import defaultdict
from textwrap import indent
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    SupportsFloat,
    SupportsInt,
    Type,
    TypeVar,
    get_origin,
)

logger = logging.getLogger(__name__)


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


def unique_ref(it):
    return unique(it, id)


def duplicates(it, key):
    return {k: v for k, v in groupby(it, key).items() if len(v) > 1}


def get_dict(obj, key, default):
    if key not in obj:
        obj[key] = default()

    return obj[key]


def flatten(obj: Iterable, depth=1) -> List:
    if depth == 0:
        return list(obj)
    if not isinstance(obj, Iterable):
        return [obj]
    return [nested for top in obj for nested in flatten(top, depth=depth - 1)]


T = TypeVar("T")
U = TypeVar("U")


def get_key(haystack: dict[T, U], needle: U) -> T:
    return find(haystack.items(), lambda x: x[1] == needle)[0]


class KeyErrorNotFound(KeyError): ...


class KeyErrorAmbiguous(KeyError): ...


def find(haystack: Iterable[T], needle: Callable[[T], bool]) -> T:
    results = list(filter(needle, haystack))
    if not results:
        raise KeyErrorNotFound()
    if len(results) != 1:
        raise KeyErrorAmbiguous()
    return results[0]


def find_or(haystack: Iterable[T], needle: Callable[[T], bool], default: T) -> T:
    try:
        return find(haystack, needle)
    except KeyErrorNotFound:
        return default


def groupby(it: Iterable[T], key: Callable[[T], U]) -> dict[U, list[T]]:
    out = defaultdict(list)
    for i in it:
        out[key(i)].append(i)
    return out


def nested_enumerate(it: Iterable) -> list[tuple[list[int], Any]]:
    out: list[tuple[list[int], Any]] = []
    for i, obj in enumerate(it):
        if not isinstance(obj, Iterable):
            out.append(([i], obj))
            continue
        for j, _obj in nested_enumerate(obj):
            out.append(([i] + j, _obj))

    return out


class NotifiesOnPropertyChange(object):
    def __init__(self, callback) -> None:
        self._callback = callback

        # TODO dir -> vars?
        for name in dir(self):
            self._callback(name, getattr(self, name))

    def __setattr__(self, __name, __value) -> None:
        super().__setattr__(__name, __value)

        # before init
        if hasattr(self, "_callback"):
            self._callback(__name, __value)


T = TypeVar("T")
P = TypeVar("P")


class _wrapper(NotifiesOnPropertyChange, Generic[T, P]):
    @abstractmethod
    def __init__(self, parent: P) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> list[T]:
        raise NotImplementedError

    @abstractmethod
    def handle_add(self, name: str, obj: T):
        raise NotImplementedError

    @abstractmethod
    def get_parent(self) -> P:
        raise NotImplementedError

    @abstractmethod
    def extend_list(self, list_name: str, *objs: T) -> None:
        raise NotImplementedError


def Holder(_type: Type[T], _ptype: Type[P]) -> Type[_wrapper[T, P]]:
    _T = TypeVar("_T")
    _P = TypeVar("_P")

    class __wrapper(_wrapper[_T, _P]):
        def __init__(self, parent: P) -> None:
            self._list: list[T] = []
            self._type = _type
            self._parent: P = parent

            NotifiesOnPropertyChange.__init__(self, self._callback)

        def _callback(self, name: str, value: Any):
            if name.startswith("_"):
                return

            if callable(value):
                return

            if isinstance(value, self._type):
                self._list.append(value)
                self.handle_add(name, value)
                return

            if isinstance(value, Iterable):
                e_objs = nested_enumerate(value)
                objs = [x[1] for x in e_objs]
                assert all(map(lambda x: isinstance(x, self._type), objs))

                self._list += objs
                for i_list, instance in e_objs:
                    i_acc = "".join(f"[{i}]" for i in i_list)
                    self.handle_add(f"{name}{i_acc}", instance)
                return

            raise Exception(
                f"Invalid property added for {name=} {value=} of type {type(value)},"
                + f"expected {_type} or iterable thereof"
            )

        def extend_list(self, list_name: str, *objs: T) -> None:
            if not hasattr(self, list_name):
                setattr(self, list_name, [])
            for obj in objs:
                # emulate property setter
                list_obj = getattr(self, list_name)
                idx = len(list_obj)
                list_obj.append(obj)
                self._list.append(obj)
                self.handle_add(f"{list_name}[{idx}]", obj)

        def get_all(self) -> list[T]:
            # check for illegal list modifications
            for name in sorted(dir(self)):
                value = getattr(self, name)
                if name.startswith("_"):
                    continue
                if callable(value):
                    continue
                if isinstance(value, self._type):
                    continue
                if isinstance(value, Iterable):
                    assert set(flatten(value, -1)).issubset(set(self._list))
                    continue

            return self._list

        def handle_add(self, name: str, obj: T) -> None: ...

        def get_parent(self) -> P:
            return self._parent

        def repr(self):
            return f"{type(self).__name__}({self._list})"

    return __wrapper[T, P]


def NotNone(x):
    assert x is not None
    return x


T = TypeVar("T")


def cast_assert(t: type[T], obj) -> T:
    assert isinstance(obj, t)
    return obj


def times(cnt: SupportsInt, lamb: Callable[[], T]) -> list[T]:
    return [lamb() for _ in range(int(cnt))]


T = TypeVar("T")
U = TypeVar("U")


@staticmethod
def is_type_pair(
    param1: Any, param2: Any, type1: type[T], type2: type[U]
) -> Optional[tuple[T, U]]:
    o1 = get_origin(type1) or type1
    o2 = get_origin(type2) or type2
    if isinstance(param1, o1) and isinstance(param2, o2):
        return param1, param2
    if isinstance(param2, o1) and isinstance(param1, o2):
        return param2, param1
    return None


def is_type_set_subclasses(type_subclasses: set[type], types: set[type]) -> bool:
    hits = {t: any(issubclass(s, t) for s in type_subclasses) for t in types}
    return all(hits.values()) and all(
        any(issubclass(s, t) for t in types) for s in type_subclasses
    )


def round_str(value: SupportsFloat, n=8):
    """
    Round a float to n decimals and strip trailing zeros.
    """
    f = round(float(value), n)
    return str(f).rstrip("0").rstrip(".")


def _print_stack(stack):
    from colorama import Fore

    for frame_info in stack:
        frame = frame_info[0]
        if "venv" in frame_info.filename:
            continue
        if "faebryk" not in frame_info.filename:
            continue
        # if frame_info.function not in ["_connect_across_hierarchies"]:
        #    continue
        yield (
            f"{Fore.RED} Frame in {frame_info.filename} at line {frame_info.lineno}:"
            f"{Fore.BLUE} {frame_info.function} {Fore.RESET}"
        )

        def pretty_val(value):
            if isinstance(value, dict):
                import pprint

                return (
                    ("\n" if len(value) > 1 else "")
                    + pprint.pformat(
                        {pretty_val(k): pretty_val(v) for k, v in value.items()},
                        indent=2,
                        width=120,
                    )
                ).replace("\n", f"\n    {Fore.RESET}")
            elif isinstance(value, type):
                return f"<class {value.__name__}>"
            return value

        for name, value in frame.f_locals.items():
            yield f"  {Fore.GREEN}{name}{Fore.RESET} = {pretty_val(value)}"


def print_stack(stack):
    return "\n".join(_print_stack(stack))


# Get deepest values in nested dict:
def flatten_dict(d: dict):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from flatten_dict(v)
        else:
            yield (k, v)


def split_recursive_stack(
    stack: Iterable[inspect.FrameInfo],
) -> tuple[list[inspect.FrameInfo], int, list[inspect.FrameInfo]]:
    """
    Handles RecursionError by splitting the stack into three parts:
    - recursion: the repeating part of the stack indicating the recursion.
    - stack_towards_recursion: the part of the stack after the recursion
        has been detected.

    :param stack: The stack obtained from inspect.stack()
    :return: tuple (recursion, recursion_depth, stack_towards_recursion)
    """

    def find_loop_len(sequence):
        for loop_len in range(1, len(sequence) // 2 + 1):
            if len(sequence) % loop_len:
                continue
            is_loop = True
            for i in range(0, len(sequence), loop_len):
                if sequence[i : i + loop_len] != sequence[:loop_len]:
                    is_loop = False
                    break
            if is_loop:
                return loop_len

        return 0

    def find_last_longest_most_frequent_looping_sequence_in_beginning(stack):
        stack = list(stack)

        loops = []

        # iterate over all possible beginnings
        for i in range(len(stack)):
            # iterate over all possible endings
            # try to maximize length of looping sequence
            for j in reversed(range(i + 1, len(stack) + 1)):
                # determine length of loop within this range
                loop_len = find_loop_len(stack[i:j])
                if loop_len:
                    # check if skipped beginning is partial loop
                    if stack[:i] != stack[j - i : j]:
                        continue
                    loops.append((i, j, loop_len))
                    continue

        # print(loops)
        max_loop = max(loops, key=lambda x: (x[1] - x[0], x[1]), default=None)
        return max_loop

    stack = list(stack)

    # Get the full stack representation as a list of strings
    full_stack = [f"{frame.filename}:{frame.positions}" for frame in stack]

    max_loop = find_last_longest_most_frequent_looping_sequence_in_beginning(full_stack)
    assert max_loop
    i, j, depth = max_loop

    return stack[i : i + depth], depth, stack[j:]


CACHED_RECUSION_ERRORS = set()


def try_avoid_endless_recursion(f: Callable[..., str]):
    import sys

    def _f_no_rec(*args, **kwargs):
        limit = sys.getrecursionlimit()
        target = 100
        sys.setrecursionlimit(target)
        try:
            return f(*args, **kwargs)
        except RecursionError:
            sys.setrecursionlimit(target + 1000)

            rec, depth, non_rec = split_recursive_stack(inspect.stack()[1:])
            recursion_error_str = indent(
                "\n".join(
                    [
                        f"{frame.filename}:{frame.lineno} {frame.code_context}"
                        for frame in rec
                    ]
                    + [f"... repeats {depth} times ..."]
                    + [
                        f"{frame.filename}:{frame.lineno} {frame.code_context}"
                        for frame in non_rec
                    ]
                ),
                "   ",
            )

            if recursion_error_str in CACHED_RECUSION_ERRORS:
                logger.error(
                    f"Recursion error: {f.__name__} {f.__code__.co_filename}:"
                    + f"{f.__code__.co_firstlineno}: DUPLICATE"
                )
            else:
                CACHED_RECUSION_ERRORS.add(recursion_error_str)
                logger.error(
                    f"Recursion error: {f.__name__} {f.__code__.co_filename}:"
                    + f"{f.__code__.co_firstlineno}"
                )
                logger.error(recursion_error_str)

            return "<RECURSION ERROR WHILE CONVERTING TO STR>"
        finally:
            sys.setrecursionlimit(limit)

    return _f_no_rec


def zip_non_locked(left: Iterable[T], right: Iterable[U]):
    TS = TypeVar("TS")
    US = TypeVar("US")

    # Theoretically supports any amount of iters,
    #  but for type hinting limit to two for now

    class _Iter(Iterator[tuple[TS, US]]):
        class _NONDEFAULT: ...

        def __init__(self, args: list[Iterable]):
            self.iters = [iter(arg) for arg in args]
            self.stopped = False
            self.stepped = False
            self.values = [None for _ in self.iters]

        def next(self, i: int, default: Any = _NONDEFAULT):
            try:
                self.advance(i)
                return self.values[i]
            except StopIteration as e:
                self.stopped = True
                if default is not self._NONDEFAULT:
                    return default
                raise e

        def advance(self, i: int):
            self.values[i] = next(self.iters[i])
            self.stepped = True

        def advance_all(self):
            self.stepped = True
            try:
                self.values = [next(iter) for iter in self.iters]
            except StopIteration:
                self.stopped = True

        def __next__(self):
            if not self.stepped:
                self.advance_all()
            if self.stopped:
                raise StopIteration()
            self.stepped = False

            return tuple(self.values)

    return _Iter[T, U]([left, right])


def try_or(func: Callable[..., T], default: T, catch: type[Exception] = Exception) -> T:
    try:
        return func()
    except catch:
        return default
