import collections.abc
import copy
import dataclasses
import os
import pathlib
import re
import tomllib
import typing


def load(path: str | bytes | os.PathLike[str] | os.PathLike[bytes]) -> Config:
    path = pathlib.Path(os.fsdecode(path))
    with open(path, mode="rb") as fp:
        toml = tomllib.load(fp)
    cfg = Config.from_toml(toml)
    cfg.prepend_path(path.parent)
    return cfg


@dataclasses.dataclass(kw_only=True)
class Config:
    login: LoginConfig
    search: list[SearchConfig] = dataclasses.field(default_factory=list)
    warn: WarnConfig = dataclasses.field(default_factory=lambda: WarnConfig())
    misc: MiscConfig = dataclasses.field(default_factory=lambda: MiscConfig())

    @classmethod
    def from_toml(
        cls, obj: object, *, loc: collections.abc.Sequence[int | str] | None = None
    ) -> typing.Self:
        if loc is None:
            loc = []

        obj = expect_dict()(obj, loc=loc)
        validate_search = expect_list(SearchConfig.from_toml)
        return cls(
            login=get_required(LoginConfig.from_toml, obj, "login", loc=loc),
            search=get_default(validate_search, obj, "search", [], loc=loc),
            warn=get_default(WarnConfig.from_toml, obj, "warn", WarnConfig(), loc=loc),
            misc=get_default(MiscConfig.from_toml, obj, "misc", MiscConfig(), loc=loc),
        )

    def prepend_path(
        self, base: str | bytes | os.PathLike[str] | os.PathLike[bytes]
    ) -> None:
        self.login.prepend_path(base)
        for search_elem in self.search:
            search_elem.prepend_path(base)


@dataclasses.dataclass(kw_only=True)
class LoginConfig:
    mail: str
    password: str
    cookieJar: str | bytes | os.PathLike[str] | os.PathLike[bytes] | None = None

    @classmethod
    def from_toml(
        cls, obj: object, *, loc: collections.abc.Sequence[int | str] | None = None
    ) -> typing.Self:
        if loc is None:
            loc = []

        obj = expect_dict()(obj, loc=loc)
        return cls(
            mail=get_required(expect_type(str), obj, "mail", loc=loc),
            password=get_required(expect_type(str), obj, "password", loc=loc),
            cookieJar=get_optional(expect_type(str), obj, "cookieJar", loc=loc),
        )

    def prepend_path(
        self, base: str | bytes | os.PathLike[str] | os.PathLike[bytes]
    ) -> None:
        base = os.fsdecode(base)
        if self.cookieJar is not None:
            self.cookieJar = pathlib.Path(base, os.fsdecode(self.cookieJar))


@dataclasses.dataclass(kw_only=True)
class SearchConfig:
    q: str
    targets: list[str] = dataclasses.field(
        default_factory=lambda: ["title", "description", "tags"]
    )
    sort: str = "+startTime"
    jsonFilter: str | bytes | os.PathLike[str] | os.PathLike[bytes] | None = None
    openTimeFrom: str | None = None
    openTimeTo: str | None = None
    startTimeFrom: str | None = None
    startTimeTo: str | None = None
    liveEndTimeFrom: str | None = None
    liveEndTimeTo: str | None = None
    ppv: bool | None = None

    @classmethod
    def from_toml(
        cls, obj: object, *, loc: collections.abc.Sequence[int | str] | None = None
    ) -> typing.Self:
        if loc is None:
            loc = []

        obj = expect_dict()(obj, loc=loc)
        return cls(
            q=get_required(expect_type(str), obj, "q", loc=loc),
            targets=get_default(
                expect_list(expect_type(str)),
                obj,
                "targets",
                ["title", "description", "tags"],
                loc=loc,
            ),
            sort=get_default(expect_type(str), obj, "sort", "+startTime", loc=loc),
            jsonFilter=get_optional(expect_type(str), obj, "jsonFilter", loc=loc),
            openTimeFrom=get_optional(expect_type(str), obj, "openTimeFrom", loc=loc),
            openTimeTo=get_optional(expect_type(str), obj, "openTimeTo", loc=loc),
            startTimeFrom=get_optional(expect_type(str), obj, "startTimeFrom", loc=loc),
            startTimeTo=get_optional(expect_type(str), obj, "startTimeTo", loc=loc),
            liveEndTimeFrom=get_optional(
                expect_type(str), obj, "liveEndTimeFrom", loc=loc
            ),
            liveEndTimeTo=get_optional(expect_type(str), obj, "liveEndTimeTo", loc=loc),
            ppv=get_optional(expect_type(bool), obj, "ppv", loc=loc),
        )

    def prepend_path(
        self, base: str | bytes | os.PathLike[str] | os.PathLike[bytes]
    ) -> None:
        base = os.fsdecode(base)
        if self.jsonFilter is not None:
            self.jsonFilter = pathlib.Path(base, os.fsdecode(self.jsonFilter))


@dataclasses.dataclass(kw_only=True)
class WarnConfig:
    tsNotSupported: bool = True
    tsRegistrationExpired: bool = True
    tsMaxReservation: bool = True

    @classmethod
    def from_toml(
        cls, obj: object, *, loc: collections.abc.Sequence[int | str] | None = None
    ) -> typing.Self:
        if loc is None:
            loc = []

        obj = expect_dict()(obj, loc=loc)
        return cls(
            tsNotSupported=get_default(
                expect_type(bool), obj, "tsNotSupported", True, loc=loc
            ),
            tsRegistrationExpired=get_default(
                expect_type(bool), obj, "tsRegistrationExpired", True, loc=loc
            ),
            tsMaxReservation=get_default(
                expect_type(bool), obj, "tsMaxReservation", True, loc=loc
            ),
        )


@dataclasses.dataclass(kw_only=True)
class MiscConfig:
    overwrite: bool = False
    timeout: int | None = None
    userAgent: str | None = None
    context: str | None = None

    @classmethod
    def from_toml(
        cls, obj: object, *, loc: collections.abc.Sequence[int | str] | None = None
    ) -> typing.Self:
        if loc is None:
            loc = []

        obj = expect_dict()(obj, loc=loc)
        return cls(
            overwrite=get_default(expect_type(bool), obj, "overwrite", False, loc=loc),
            timeout=get_optional(expect_type(int), obj, "timeout", loc=loc),
            userAgent=get_optional(expect_type(str), obj, "userAgent", loc=loc),
            context=get_optional(expect_type(str), obj, "context", loc=loc),
        )


def get_required[T](
    validate: Validator[T],
    cfg: dict[str, object],
    key: str,
    *,
    loc: collections.abc.Sequence[int | str] | None = None,
) -> T:
    if loc is None:
        loc = []
    loc = [*loc, key]

    try:
        obj = cfg[key]
    except KeyError:
        raise ConfigRequiredError(loc)
    return validate(obj, loc=loc)


def get_optional[T](
    validate: Validator[T],
    cfg: dict[str, object],
    key: str,
    *,
    loc: collections.abc.Sequence[int | str] | None = None,
) -> T | None:
    if loc is None:
        loc = []
    loc = [*loc, key]

    try:
        obj = cfg[key]
    except KeyError:
        return None
    return validate(obj, loc=loc)


def get_default[T](
    validate: Validator[T],
    cfg: dict[str, object],
    key: str,
    default: T,
    *,
    loc: collections.abc.Sequence[int | str] | None = None,
) -> T:
    if loc is None:
        loc = []
    loc = [*loc, key]

    try:
        obj = cfg[key]
    except KeyError:
        return copy.deepcopy(default)
    return validate(obj, loc=loc)


def expect_type[T](want_type: type[T]) -> Validator[T]:
    def validate(obj: object, *, loc: collections.abc.Sequence[int | str]) -> T:
        if not isinstance(obj, want_type) or type(obj) is not want_type:
            raise ConfigTypeError(loc, want_type, type(obj))
        return obj

    return validate


def expect_list[T](validate_elem: Validator[T]) -> Validator[list[T]]:
    def validate(obj: object, *, loc: collections.abc.Sequence[int | str]) -> list[T]:
        lst: list[object] = expect_type(list)(obj, loc=loc)

        new: list[T] = []
        for idx, elm in enumerate(lst):
            elm = validate_elem(elm, loc=[*loc, idx])
            new.append(elm)
        return new

    return validate


def expect_dict() -> Validator[dict[str, object]]:
    def validate(
        obj: object, *, loc: collections.abc.Sequence[int | str]
    ) -> dict[str, object]:
        obj = expect_type(dict)(obj, loc=loc)

        new: dict[str, object] = {}
        for key, val in obj.items():
            assert isinstance(key, str)
            new[key] = val
        return new

    return validate


class Validator[T](typing.Protocol):
    def __call__(
        self,
        obj: object,
        *,
        loc: collections.abc.Sequence[int | str],
    ) -> T: ...


class ConfigError(Exception):
    def __init__(self, loc: collections.abc.Sequence[int | str], *args: object) -> None:
        super().__init__(loc, *args)
        self.config_loc: list[int | str] = list(loc)

    def __str__(self) -> str:
        return "config: " + format_toml_loc(self.config_loc)


class ConfigRequiredError(ConfigError):
    def __str__(self) -> str:
        return super().__str__() + ": is required"


class ConfigTypeError(ConfigError):
    def __init__(
        self,
        loc: collections.abc.Sequence[int | str],
        want_type: type,
        got_type: type,
        *args: object,
    ) -> None:
        super().__init__(loc, want_type, got_type, *args)
        self.config_want_type: type = want_type
        self.config_got_type: type = got_type

    def __str__(self) -> str:
        return (
            super().__str__()
            + f": expected {self.config_want_type.__name__}, got {self.config_got_type.__name__}"
        )


def format_toml_loc(loc: collections.abc.Sequence[int | str]) -> str:
    fmt = []
    for sub in loc:
        if isinstance(sub, int):
            idx = format_toml_idx(sub)
            fmt.append(idx)
            continue
        if isinstance(sub, str):
            key = format_toml_key(sub)
            if len(fmt) > 0:
                fmt.append(".")
            fmt.append(key)
            continue
        typing.assert_never(sub)
    return "".join(fmt)


def format_toml_idx(idx: int) -> str:
    return f"[{idx:d}]"


def format_toml_key(key: str) -> str:
    bare_pat = re.compile(r"\A[A-Za-z0-9_-]+\z")
    bare_match = bare_pat.match(key)
    if bare_match is not None:
        return key
    return format_toml_key_quoted(key)


def format_toml_key_quoted(key: str) -> str:
    compact_escape_dict = {
        "\b": r"\b",
        "\t": r"\t",
        "\n": r"\n",
        "\f": r"\f",
        "\r": r"\r",
        '"': r"\"",
        "\\": "\\\\",
    }

    fmt_chr_list = []
    for raw_chr in key:
        fmt_chr = compact_escape_dict.get(raw_chr)
        if fmt_chr is not None:
            fmt_chr_list.append(fmt_chr)
            continue

        raw_ord = ord(raw_chr)
        if 0x00 <= raw_ord <= 0x1F or raw_ord == 0x7F:
            # Avoid using "\xHH" format for compatibility with v1.0.0,
            # as it was introduced in v1.1.0.
            fmt_chr = r"\u" f"{raw_ord:04X}"
            fmt_chr_list.append(fmt_chr)
            continue

        fmt_chr = raw_chr
        fmt_chr_list.append(fmt_chr)

    return '"' + "".join(fmt_chr_list) + '"'
