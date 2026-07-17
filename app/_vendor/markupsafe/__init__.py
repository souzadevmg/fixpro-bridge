"""MarkupSafe 3.0.3 pure-Python implementation, copyright Pallets."""

from __future__ import annotations

import collections.abc as cabc
import string
import typing as t

from ._native import _escape_inner

if t.TYPE_CHECKING:
    import typing_extensions as te


class _HasHTML(t.Protocol):
    def __html__(self, /) -> str: ...


class _TPEscape(t.Protocol):
    def __call__(self, s: t.Any, /) -> Markup: ...


def escape(s: t.Any, /) -> Markup:
    if type(s) is str:
        return Markup(_escape_inner(s))
    if hasattr(s, "__html__"):
        return Markup(s.__html__())
    return Markup(_escape_inner(str(s)))


def escape_silent(s: t.Any | None, /) -> Markup:
    if s is None:
        return Markup()
    return escape(s)


def soft_str(s: t.Any, /) -> str:
    if not isinstance(s, str):
        return str(s)
    return s


class Markup(str):
    __slots__ = ()

    def __new__(
        cls, object: t.Any = "", encoding: str | None = None, errors: str = "strict"
    ) -> te.Self:
        if hasattr(object, "__html__"):
            object = object.__html__()
        if encoding is None:
            return super().__new__(cls, object)
        return super().__new__(cls, object, encoding, errors)

    def __html__(self, /) -> te.Self:
        return self

    def __add__(self, value: str | _HasHTML, /) -> te.Self:
        if isinstance(value, str) or hasattr(value, "__html__"):
            return self.__class__(super().__add__(self.escape(value)))
        return NotImplemented

    def __radd__(self, value: str | _HasHTML, /) -> te.Self:
        if isinstance(value, str) or hasattr(value, "__html__"):
            return self.escape(value).__add__(self)
        return NotImplemented

    def __mul__(self, value: t.SupportsIndex, /) -> te.Self:
        return self.__class__(super().__mul__(value))

    def __rmul__(self, value: t.SupportsIndex, /) -> te.Self:
        return self.__class__(super().__mul__(value))

    def __mod__(self, value: t.Any, /) -> te.Self:
        if isinstance(value, tuple):
            value = tuple(_MarkupEscapeHelper(x, self.escape) for x in value)
        elif hasattr(type(value), "__getitem__") and not isinstance(value, str):
            value = _MarkupEscapeHelper(value, self.escape)
        else:
            value = (_MarkupEscapeHelper(value, self.escape),)
        return self.__class__(super().__mod__(value))

    def __repr__(self, /) -> str:
        return f"{self.__class__.__name__}({super().__repr__()})"

    def join(self, iterable: cabc.Iterable[str | _HasHTML], /) -> te.Self:
        return self.__class__(super().join(map(self.escape, iterable)))

    def split(self, /, sep: str | None = None, maxsplit: t.SupportsIndex = -1) -> list[te.Self]:
        return [self.__class__(value) for value in super().split(sep, maxsplit)]

    def rsplit(self, /, sep: str | None = None, maxsplit: t.SupportsIndex = -1) -> list[te.Self]:
        return [self.__class__(value) for value in super().rsplit(sep, maxsplit)]

    def splitlines(self, /, keepends: bool = False) -> list[te.Self]:
        return [self.__class__(value) for value in super().splitlines(keepends)]

    def unescape(self, /) -> str:
        from html import unescape
        return unescape(str(self))

    def striptags(self, /) -> str:
        value = str(self)
        while (start := value.find("<!--")) != -1:
            if (end := value.find("-->", start)) == -1:
                break
            value = f"{value[:start]}{value[end + 3:]}"
        while (start := value.find("<")) != -1:
            if (end := value.find(">", start)) == -1:
                break
            value = f"{value[:start]}{value[end + 1:]}"
        return self.__class__(" ".join(value.split())).unescape()

    @classmethod
    def escape(cls, s: t.Any, /) -> te.Self:
        result = escape(s)
        if result.__class__ is not cls:
            return cls(result)
        return result

    def __getitem__(self, key: t.SupportsIndex | slice, /) -> te.Self:
        return self.__class__(super().__getitem__(key))

    def capitalize(self, /) -> te.Self:
        return self.__class__(super().capitalize())

    def title(self, /) -> te.Self:
        return self.__class__(super().title())

    def lower(self, /) -> te.Self:
        return self.__class__(super().lower())

    def upper(self, /) -> te.Self:
        return self.__class__(super().upper())

    def replace(self, old: str, new: str, count: t.SupportsIndex = -1, /) -> te.Self:
        return self.__class__(super().replace(old, self.escape(new), count))

    def ljust(self, width: t.SupportsIndex, fillchar: str = " ", /) -> te.Self:
        return self.__class__(super().ljust(width, self.escape(fillchar)))

    def rjust(self, width: t.SupportsIndex, fillchar: str = " ", /) -> te.Self:
        return self.__class__(super().rjust(width, self.escape(fillchar)))

    def lstrip(self, chars: str | None = None, /) -> te.Self:
        return self.__class__(super().lstrip(chars))

    def rstrip(self, chars: str | None = None, /) -> te.Self:
        return self.__class__(super().rstrip(chars))

    def center(self, width: t.SupportsIndex, fillchar: str = " ", /) -> te.Self:
        return self.__class__(super().center(width, self.escape(fillchar)))

    def strip(self, chars: str | None = None, /) -> te.Self:
        return self.__class__(super().strip(chars))

    def translate(self, table: cabc.Mapping[int, str | int | None], /) -> str:
        return self.__class__(super().translate(table))

    def expandtabs(self, /, tabsize: t.SupportsIndex = 8) -> te.Self:
        return self.__class__(super().expandtabs(tabsize))

    def swapcase(self, /) -> te.Self:
        return self.__class__(super().swapcase())

    def zfill(self, width: t.SupportsIndex, /) -> te.Self:
        return self.__class__(super().zfill(width))

    def casefold(self, /) -> te.Self:
        return self.__class__(super().casefold())

    def removeprefix(self, prefix: str, /) -> te.Self:
        return self.__class__(super().removeprefix(prefix))

    def removesuffix(self, suffix: str) -> te.Self:
        return self.__class__(super().removesuffix(suffix))

    def partition(self, sep: str, /) -> tuple[te.Self, te.Self, te.Self]:
        left, middle, right = super().partition(sep)
        cls = self.__class__
        return cls(left), cls(middle), cls(right)

    def rpartition(self, sep: str, /) -> tuple[te.Self, te.Self, te.Self]:
        left, middle, right = super().rpartition(sep)
        cls = self.__class__
        return cls(left), cls(middle), cls(right)

    def format(self, *args: t.Any, **kwargs: t.Any) -> te.Self:
        formatter = EscapeFormatter(self.escape)
        return self.__class__(formatter.vformat(self, args, kwargs))

    def format_map(self, mapping: cabc.Mapping[str, t.Any], /) -> te.Self:
        formatter = EscapeFormatter(self.escape)
        return self.__class__(formatter.vformat(self, (), mapping))

    def __html_format__(self, format_spec: str, /) -> te.Self:
        if format_spec:
            raise ValueError("Unsupported format specification for Markup.")
        return self


class EscapeFormatter(string.Formatter):
    __slots__ = ("escape",)

    def __init__(self, escape_function: _TPEscape) -> None:
        self.escape = escape_function
        super().__init__()

    def format_field(self, value: t.Any, format_spec: str) -> str:
        if hasattr(value, "__html_format__"):
            result = value.__html_format__(format_spec)
        elif hasattr(value, "__html__"):
            if format_spec:
                raise ValueError("HTML objects with format specs need __html_format__.")
            result = value.__html__()
        else:
            result = super().format_field(value, str(format_spec))
        return str(self.escape(result))


class _MarkupEscapeHelper:
    __slots__ = ("obj", "escape")

    def __init__(self, obj: t.Any, escape_function: _TPEscape) -> None:
        self.obj = obj
        self.escape = escape_function

    def __getitem__(self, key: t.Any, /) -> te.Self:
        return self.__class__(self.obj[key], self.escape)

    def __str__(self, /) -> str:
        return str(self.escape(self.obj))

    def __repr__(self, /) -> str:
        return str(self.escape(repr(self.obj)))

    def __int__(self, /) -> int:
        return int(self.obj)

    def __float__(self, /) -> float:
        return float(self.obj)
