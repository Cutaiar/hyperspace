"""What a write to a setting says: that there was one (undo's subscription).

`mark()` moves one process-wide number, `serial()`. Every road that moves a
param's **base** or a row of the table marks; a performer's offset, written
each frame through `Param.apply`, does not. `undo.Undo.tick` reads the number
and takes its fingerprint only when it moved, so an idle frame costs a
comparison instead of a read of every setting.

A param's base with no source on it *is* its object's attribute, and not
everything that writes the object goes through `Param.set` (the mouse's
reset, a look's load, a fractal's dive, an integrator). So the objects
themselves say they were written:

- `Observed`: a base class. Writing an attribute that a param reads (a
  **cell**) marks; any other attribute is an ordinary write.
- `ObservedDict`: the same for a dict, whatever method changes it.

`cell` and `key` are the (get, put) pair of a param on one. `get` carries the
cell's name (`get.cell`), which is what tells undo it need not be read every
frame. `put` writes round the hook: `Param.set` marks for itself, and
`Param.apply` calls the same `put` for an offset, which is no edit. A param
whose getter carries no cell (a list's item, the analyzer's live chain, a
value worked out from others) is read every frame by undo, as all were.

A leaf: imports nothing from the package."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# kept across a hot reload of this module, which re-executes it over the same
# globals: the number must never go back, and a class executed again must
# still know the cells its live objects' params read
_serial: int = globals().get("_serial", 0)
_names: dict[tuple[str, str], set[str]] = globals().get("_names", {})
_MISSING = object()


def mark() -> None:
    """A setting was, or may have been, written. Called **after** the write:
    another thread's fingerprint taken between the two would see the mark
    and not the value."""
    global _serial
    _serial += 1


def serial() -> int:
    """Moves with every `mark`. Only ever compared with an earlier reading."""
    return _serial


class Observed:
    """An object whose cells mark when they are written."""

    _cells: set[str] = set()       # noqa: RUF012 — each class's own (`__init_subclass__`)

    def __init_subclass__(cls, **kw) -> None:
        super().__init_subclass__(**kw)
        own = _names.setdefault((cls.__module__, cls.__qualname__), set())
        for base in cls.__mro__[1:]:
            own |= getattr(base, "_cells", set())
        cls._cells = own

    def __setattr__(self, name: str, value: Any) -> None:
        if name not in self._cells:
            object.__setattr__(self, name, value)
            return
        old = vars(self).get(name, _MISSING)
        object.__setattr__(self, name, value)
        if old is not value and old is not _MISSING:     # (missing: being built)
            try:
                same = bool(old == value)
            except Exception:  # noqa: BLE001 — values that will not compare: a write
                same = False
            if not same:
                mark()

    def __delattr__(self, name: str) -> None:
        object.__delattr__(self, name)
        if name in self._cells:
            mark()


def _marked(name: str) -> Callable:
    inner = getattr(dict, name)

    def method(self, *a, **kw):
        try:
            return inner(self, *a, **kw)
        finally:
            mark()

    method.__name__ = name
    return method


class ObservedDict(dict):
    """A dict whose every change marks."""

    for _m in ("__setitem__", "__delitem__", "__ior__", "clear", "pop", "popitem",
               "setdefault", "update"):
        locals()[_m] = _marked(_m)
    del _m


def watch(cls: type[Observed], *names: str) -> None:
    """`names` are cells of `cls` and of every class made from it after this."""
    cls._cells.update(names)


def getter(obj: Any, name: str) -> Callable[[], Any]:
    """A read of `obj.name`, a cell when `obj` can say it was written: an
    `Observed`, and a plain attribute of its own (a property reads other
    things; a class's default is not yet the object's)."""
    get: Any = lambda: getattr(obj, name)
    static = next((vars(c)[name] for c in type(obj).__mro__ if name in vars(c)), None)
    if (isinstance(obj, Observed) and name in vars(obj) and not hasattr(type(static), "__set__")
            and not hasattr(type(static), "__get__")):
        type(obj)._cells.add(name)
        get.cell = (id(obj), name)
    return get


def cell(obj: Any, name: str, cast: Callable[[Any], Any] | None = None
         ) -> tuple[Callable[[], Any], Callable[[Any], None]]:
    """The (get, put) of a param on `obj.name`, `cast` on the way in. On no
    `Observed` they are a plain getattr and setattr."""
    get = getter(obj, name)
    write = object.__setattr__ if hasattr(get, "cell") else setattr
    if cast is None:
        return get, lambda v: write(obj, name, v)
    return get, lambda v: write(obj, name, cast(v))


def key(d: dict, k: str) -> tuple[Callable[[], Any], Callable[[Any], None]]:
    """The (get, put) of a param on `d[k]`: a cell on an `ObservedDict`."""
    get: Any = lambda: d[k]
    if isinstance(d, ObservedDict):
        get.cell = (id(d), k)
    return get, lambda v: dict.__setitem__(d, k, v)
