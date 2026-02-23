import copy
import pathlib
import tempfile
import tomllib
import typing
import unittest

import tsm.config


class TestLoad(unittest.TestCase):
    def test(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            put_path = pathlib.Path(base, "config.toml")
            with open(put_path, mode="w", encoding="utf-8", errors="strict") as fp:
                fp.write("""
[login]
mail = "mail@example.com"
password = "PASSWORD"
cookieJar = "cookiejar.txt"

[[search]]
q = "ゲーム"
targets = ["tagsExact"]
jsonFilter = "filters.json"

[misc]
overwrite = true
timeout = 300
userAgent = "ts_machine (https://github.com/gcrtnst/ts_machine)"
context = "ts_machine (https://github.com/gcrtnst/ts_machine)"
""")
            exp_cfg = tsm.config.Config(
                login=tsm.config.LoginConfig(
                    mail="mail@example.com",
                    password="PASSWORD",
                    cookieJar=pathlib.Path(base, "cookiejar.txt"),
                ),
                search=[
                    tsm.config.SearchConfig(
                        q="ゲーム",
                        targets=["tagsExact"],
                        jsonFilter=pathlib.Path(base, "filters.json"),
                    )
                ],
                misc=tsm.config.MiscConfig(
                    overwrite=True,
                    timeout=300,
                    userAgent="ts_machine (https://github.com/gcrtnst/ts_machine)",
                    context="ts_machine (https://github.com/gcrtnst/ts_machine)",
                ),
            )

            got_cfg = tsm.config.load(put_path)
            self.assertEqual(got_cfg, exp_cfg)


class TestConfigFromTOML(unittest.TestCase):
    def test_normal(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put", object),
                ("exp", tsm.config.Config),
            ],
        )

        for tc in [
            tt(
                "minimal",
                {"login": {"mail": "mail@example.com", "password": "PASSWORD"}},
                tsm.config.Config(
                    login=tsm.config.LoginConfig(
                        mail="mail@example.com", password="PASSWORD"
                    )
                ),
            ),
            tt(
                "full",
                {
                    "login": {
                        "mail": "mail@example.com",
                        "password": "PASSWORD",
                        "cookieJar": "cookiejar.txt",
                    },
                    "search": [
                        {
                            "q": "ゲーム",
                            "targets": ["tagsExact"],
                            "sort": "-startTime",
                            "jsonFilter": "filters.json",
                            "openTimeFrom": "1h10m",
                            "openTimeTo": "1h20m",
                            "startTimeFrom": "2h10m",
                            "startTimeTo": "2h20m",
                            "liveEndTimeFrom": "3h10m",
                            "liveEndTimeTo": "3h20m",
                            "ppv": False,
                        }
                    ],
                    "warn": {
                        "tsNotSupported": False,
                        "tsRegistrationExpired": False,
                        "tsMaxReservation": False,
                    },
                    "misc": {
                        "overwrite": True,
                        "timeout": 300,
                        "userAgent": "ts_machine_ua (https://github.com/gcrtnst/ts_machine)",
                        "context": "ts_machine_ctx (https://github.com/gcrtnst/ts_machine)",
                    },
                },
                tsm.config.Config(
                    login=tsm.config.LoginConfig(
                        mail="mail@example.com",
                        password="PASSWORD",
                        cookieJar="cookiejar.txt",
                    ),
                    search=[
                        tsm.config.SearchConfig(
                            q="ゲーム",
                            targets=["tagsExact"],
                            sort="-startTime",
                            jsonFilter="filters.json",
                            openTimeFrom="1h10m",
                            openTimeTo="1h20m",
                            startTimeFrom="2h10m",
                            startTimeTo="2h20m",
                            liveEndTimeFrom="3h10m",
                            liveEndTimeTo="3h20m",
                            ppv=False,
                        )
                    ],
                    warn=tsm.config.WarnConfig(
                        tsNotSupported=False,
                        tsRegistrationExpired=False,
                        tsMaxReservation=False,
                    ),
                    misc=tsm.config.MiscConfig(
                        overwrite=True,
                        timeout=300,
                        userAgent="ts_machine_ua (https://github.com/gcrtnst/ts_machine)",
                        context="ts_machine_ctx (https://github.com/gcrtnst/ts_machine)",
                    ),
                ),
            ),
        ]:
            with self.subTest(tc.msg):
                got = tsm.config.Config.from_toml(tc.put)
                self.assertEqual(got, tc.exp)

    def test_error_dict(self) -> None:
        with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
            tsm.config.Config.from_toml([], loc=["config"])
        self.assertEqual(ctx.exception.config_loc, ["config"])
        self.assertEqual(ctx.exception.config_want_type, dict)
        self.assertEqual(ctx.exception.config_got_type, list)

    def test_error_required(self) -> None:
        with self.assertRaises(tsm.config.ConfigRequiredError) as ctx:
            tsm.config.Config.from_toml({}, loc=["config"])
        self.assertEqual(ctx.exception.config_loc, ["config", "login"])

    def test_error_type(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put_obj", object),
                ("put_loc", list[int | str] | None),
                ("exp_loc", list[int | str]),
                ("exp_type_want", type),
                ("exp_type_got", type),
            ],
        )

        for tc in [
            tt(
                "login type",
                {"login": "login"},
                ["table"],
                ["table", "login"],
                dict,
                str,
            ),
            tt(
                "login type, noloc",
                {"login": "login"},
                None,
                ["login"],
                dict,
                str,
            ),
            tt(
                "search type",
                {
                    "login": {"mail": "mail@example.com", "password": "PASSWORD"},
                    "search": {"q": "ゲーム"},
                },
                ["table"],
                ["table", "search"],
                list,
                dict,
            ),
            tt(
                "search type, noloc",
                {
                    "login": {"mail": "mail@example.com", "password": "PASSWORD"},
                    "search": {"q": "ゲーム"},
                },
                None,
                ["search"],
                list,
                dict,
            ),
            tt(
                "warn type",
                {
                    "login": {"mail": "mail@example.com", "password": "PASSWORD"},
                    "warn": "warn",
                },
                ["table"],
                ["table", "warn"],
                dict,
                str,
            ),
            tt(
                "warn type, noloc",
                {
                    "login": {"mail": "mail@example.com", "password": "PASSWORD"},
                    "warn": "warn",
                },
                None,
                ["warn"],
                dict,
                str,
            ),
            tt(
                "misc type",
                {
                    "login": {"mail": "mail@example.com", "password": "PASSWORD"},
                    "misc": "misc",
                },
                ["table"],
                ["table", "misc"],
                dict,
                str,
            ),
            tt(
                "misc type, noloc",
                {
                    "login": {"mail": "mail@example.com", "password": "PASSWORD"},
                    "misc": "misc",
                },
                None,
                ["misc"],
                dict,
                str,
            ),
        ]:
            with self.subTest(tc.msg):
                with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
                    tsm.config.Config.from_toml(tc.put_obj, loc=tc.put_loc)
                self.assertEqual(ctx.exception.config_loc, tc.exp_loc)
                self.assertEqual(ctx.exception.config_want_type, tc.exp_type_want)
                self.assertEqual(ctx.exception.config_got_type, tc.exp_type_got)


class TestConfigPrependPath(unittest.TestCase):
    def test(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put_cfg", tsm.config.Config),
                ("put_base", pathlib.Path),
                ("exp_cfg", tsm.config.Config),
            ],
        )

        with tempfile.TemporaryDirectory() as base:
            for tc in [
                tt(
                    "normal",
                    tsm.config.Config(
                        login=tsm.config.LoginConfig(
                            mail="mail@example.com",
                            password="PASSWORD",
                            cookieJar="cookiejar.txt",
                        ),
                        search=[
                            tsm.config.SearchConfig(
                                q="一番",
                                jsonFilter="1.json",
                            ),
                            tsm.config.SearchConfig(
                                q="二番",
                                jsonFilter="2.json",
                            ),
                            tsm.config.SearchConfig(
                                q="三番",
                                jsonFilter="3.json",
                            ),
                        ],
                    ),
                    pathlib.Path(base),
                    tsm.config.Config(
                        login=tsm.config.LoginConfig(
                            mail="mail@example.com",
                            password="PASSWORD",
                            cookieJar=pathlib.Path(base, "cookiejar.txt"),
                        ),
                        search=[
                            tsm.config.SearchConfig(
                                q="一番",
                                jsonFilter=pathlib.Path(base, "1.json"),
                            ),
                            tsm.config.SearchConfig(
                                q="二番",
                                jsonFilter=pathlib.Path(base, "2.json"),
                            ),
                            tsm.config.SearchConfig(
                                q="三番",
                                jsonFilter=pathlib.Path(base, "3.json"),
                            ),
                        ],
                    ),
                ),
                tt(
                    "minimal",
                    tsm.config.Config(
                        login=tsm.config.LoginConfig(
                            mail="mail@example.com",
                            password="PASSWORD",
                            cookieJar="cookiejar.txt",
                        ),
                        search=[],
                    ),
                    pathlib.Path(base),
                    tsm.config.Config(
                        login=tsm.config.LoginConfig(
                            mail="mail@example.com",
                            password="PASSWORD",
                            cookieJar=pathlib.Path(base, "cookiejar.txt"),
                        ),
                        search=[],
                    ),
                ),
            ]:
                with self.subTest(tc.msg):
                    cfg = copy.deepcopy(tc.put_cfg)
                    cfg.prepend_path(tc.put_base)
                    self.assertEqual(cfg, tc.exp_cfg)


class TestLoginConfigFromTOML(unittest.TestCase):
    def test_normal(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put", object),
                ("exp", tsm.config.LoginConfig),
            ],
        )

        for tc in [
            tt(
                "full",
                {
                    "mail": "mail@example.com",
                    "password": "PASSWORD",
                    "cookieJar": "path/to/jar",
                },
                tsm.config.LoginConfig(
                    mail="mail@example.com",
                    password="PASSWORD",
                    cookieJar="path/to/jar",
                ),
            ),
            tt(
                "default",
                {
                    "mail": "mail@example.com",
                    "password": "PASSWORD",
                },
                tsm.config.LoginConfig(
                    mail="mail@example.com",
                    password="PASSWORD",
                ),
            ),
        ]:
            with self.subTest(tc.msg):
                got = tsm.config.LoginConfig.from_toml(tc.put)
                self.assertEqual(got, tc.exp)

    def test_error_dict(self) -> None:
        with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
            tsm.config.LoginConfig.from_toml([], loc=["login"])
        self.assertEqual(ctx.exception.config_loc, ["login"])
        self.assertEqual(ctx.exception.config_want_type, dict)
        self.assertEqual(ctx.exception.config_got_type, list)

    def test_error_required(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put_obj", object),
                ("put_loc", list[int | str] | None),
                ("exp_loc", list[int | str]),
            ],
        )

        for tc in [
            tt(
                "missing mail",
                {"password": "PASSWORD"},
                ["table"],
                ["table", "mail"],
            ),
            tt(
                "missing mail, noloc",
                {"password": "PASSWORD"},
                None,
                ["mail"],
            ),
            tt(
                "missing password",
                {"mail": "mail@example.com"},
                ["table"],
                ["table", "password"],
            ),
            tt(
                "missing password, noloc",
                {"mail": "mail@example.com"},
                None,
                ["password"],
            ),
        ]:
            with self.subTest(tc.msg):
                with self.assertRaises(tsm.config.ConfigRequiredError) as ctx:
                    tsm.config.LoginConfig.from_toml(tc.put_obj, loc=tc.put_loc)
                self.assertEqual(ctx.exception.config_loc, tc.exp_loc)

    def test_error_type(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put_obj", object),
                ("put_loc", list[int | str] | None),
                ("exp_loc", list[int | str]),
                ("exp_type_want", type),
                ("exp_type_got", type),
            ],
        )

        for tc in [
            tt(
                "mail type",
                {"mail": 1, "password": "PASSWORD"},
                ["table"],
                ["table", "mail"],
                str,
                int,
            ),
            tt(
                "mail type, noloc",
                {"mail": 1, "password": "PASSWORD"},
                None,
                ["mail"],
                str,
                int,
            ),
            tt(
                "password type",
                {"mail": "example.com", "password": 1},
                ["table"],
                ["table", "password"],
                str,
                int,
            ),
            tt(
                "password type, noloc",
                {"mail": "example.com", "password": 1},
                None,
                ["password"],
                str,
                int,
            ),
            tt(
                "cookieJar type",
                {"mail": "example.com", "password": "PASSWORD", "cookieJar": 1},
                ["table"],
                ["table", "cookieJar"],
                str,
                int,
            ),
            tt(
                "cookieJar type, noloc",
                {"mail": "example.com", "password": "PASSWORD", "cookieJar": 1},
                None,
                ["cookieJar"],
                str,
                int,
            ),
        ]:
            with self.subTest(tc.msg):
                with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
                    tsm.config.LoginConfig.from_toml(tc.put_obj, loc=tc.put_loc)
                self.assertEqual(ctx.exception.config_loc, tc.exp_loc)
                self.assertEqual(ctx.exception.config_want_type, tc.exp_type_want)
                self.assertEqual(ctx.exception.config_got_type, tc.exp_type_got)


class TestLoginConfigPrependPath(unittest.TestCase):
    def test(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put_cfg", tsm.config.LoginConfig),
                ("put_base", pathlib.Path),
                ("exp_cfg", tsm.config.LoginConfig),
            ],
        )

        with tempfile.TemporaryDirectory() as base:
            for tc in [
                tt(
                    "exists",
                    tsm.config.LoginConfig(
                        mail="mail@example.com",
                        password="PASSWORD",
                        cookieJar="cookiejar.txt",
                    ),
                    pathlib.Path(base),
                    tsm.config.LoginConfig(
                        mail="mail@example.com",
                        password="PASSWORD",
                        cookieJar=pathlib.Path(base, "cookiejar.txt"),
                    ),
                ),
                tt(
                    "none",
                    tsm.config.LoginConfig(
                        mail="mail@example.com",
                        password="PASSWORD",
                    ),
                    pathlib.Path(base),
                    tsm.config.LoginConfig(
                        mail="mail@example.com",
                        password="PASSWORD",
                    ),
                ),
            ]:
                with self.subTest(tc.msg):
                    cfg = copy.deepcopy(tc.put_cfg)
                    cfg.prepend_path(tc.put_base)
                    self.assertEqual(cfg, tc.exp_cfg)


class TestSearchConfigFromTOML(unittest.TestCase):
    def test_normal(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put", object),
                ("exp", tsm.config.SearchConfig),
            ],
        )

        for tc in [
            tt(
                "full",
                {
                    "q": "ゲーム",
                    "targets": ["tagsExact"],
                    "sort": "-startTime",
                    "jsonFilter": "filters.json",
                    "openTimeFrom": "30m",
                    "openTimeTo": "1h",
                    "startTimeFrom": "1h30m",
                    "startTimeTo": "2h",
                    "liveEndTimeFrom": "2h30m",
                    "liveEndTimeTo": "3h",
                    "ppv": True,
                },
                tsm.config.SearchConfig(
                    q="ゲーム",
                    targets=["tagsExact"],
                    sort="-startTime",
                    jsonFilter="filters.json",
                    openTimeFrom="30m",
                    openTimeTo="1h",
                    startTimeFrom="1h30m",
                    startTimeTo="2h",
                    liveEndTimeFrom="2h30m",
                    liveEndTimeTo="3h",
                    ppv=True,
                ),
            ),
            tt(
                "default",
                {"q": "ゲーム"},
                tsm.config.SearchConfig(q="ゲーム"),
            ),
        ]:
            with self.subTest(tc.msg):
                got = tsm.config.SearchConfig.from_toml(tc.put)
                self.assertEqual(got, tc.exp)

    def test_error_dict(self) -> None:
        with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
            tsm.config.SearchConfig.from_toml([], loc=["search"])
        self.assertEqual(ctx.exception.config_loc, ["search"])
        self.assertEqual(ctx.exception.config_want_type, dict)
        self.assertEqual(ctx.exception.config_got_type, list)

    def test_error_required(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put_obj", object),
                ("put_loc", list[int | str] | None),
                ("exp_loc", list[int | str]),
            ],
        )

        for tc in [
            tt(
                "missing q",
                {
                    "targets": ["tagsExact"],
                    "sort": "-startTime",
                    "jsonFilter": "filters.json",
                    "openTimeFrom": "30m",
                    "openTimeTo": "1h",
                    "startTimeFrom": "1h30m",
                    "startTimeTo": "2h",
                    "liveEndTimeFrom": "2h30m",
                    "liveEndTimeTo": "3h",
                    "ppv": True,
                },
                ["table"],
                ["table", "q"],
            ),
            tt(
                "missing q, noloc",
                {
                    "targets": ["tagsExact"],
                    "sort": "-startTime",
                    "jsonFilter": "filters.json",
                    "openTimeFrom": "30m",
                    "openTimeTo": "1h",
                    "startTimeFrom": "1h30m",
                    "startTimeTo": "2h",
                    "liveEndTimeFrom": "2h30m",
                    "liveEndTimeTo": "3h",
                    "ppv": True,
                },
                None,
                ["q"],
            ),
        ]:
            with self.subTest(tc.msg):
                with self.assertRaises(tsm.config.ConfigRequiredError) as ctx:
                    tsm.config.SearchConfig.from_toml(tc.put_obj, loc=tc.put_loc)
                self.assertEqual(ctx.exception.config_loc, tc.exp_loc)

    def test_error_type(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put_obj", object),
                ("put_loc", list[int | str] | None),
                ("exp_loc", list[int | str]),
                ("exp_type_want", type),
                ("exp_type_got", type),
            ],
        )

        for tc in [
            tt(
                "q type",
                {"q": 52149},
                ["table"],
                ["table", "q"],
                str,
                int,
            ),
            tt(
                "q type, noloc",
                {"q": 52149},
                None,
                ["q"],
                str,
                int,
            ),
            tt(
                "targets type",
                {"q": "ゲーム", "targets": [52149]},
                ["table"],
                ["table", "targets", 0],
                str,
                int,
            ),
            tt(
                "targets type, noloc",
                {"q": "ゲーム", "targets": [52149]},
                None,
                ["targets", 0],
                str,
                int,
            ),
            tt(
                "sort type",
                {"q": "ゲーム", "sort": 52149},
                ["table"],
                ["table", "sort"],
                str,
                int,
            ),
            tt(
                "sort type, noloc",
                {"q": "ゲーム", "sort": 52149},
                None,
                ["sort"],
                str,
                int,
            ),
            tt(
                "jsonFilter type",
                {"q": "ゲーム", "jsonFilter": 52149},
                ["table"],
                ["table", "jsonFilter"],
                str,
                int,
            ),
            tt(
                "jsonFilter type, noloc",
                {"q": "ゲーム", "jsonFilter": 52149},
                None,
                ["jsonFilter"],
                str,
                int,
            ),
            tt(
                "openTimeFrom type",
                {"q": "ゲーム", "openTimeFrom": 52149},
                ["table"],
                ["table", "openTimeFrom"],
                str,
                int,
            ),
            tt(
                "openTimeFrom type, noloc",
                {"q": "ゲーム", "openTimeFrom": 52149},
                None,
                ["openTimeFrom"],
                str,
                int,
            ),
            tt(
                "openTimeTo type",
                {"q": "ゲーム", "openTimeTo": 52149},
                ["table"],
                ["table", "openTimeTo"],
                str,
                int,
            ),
            tt(
                "openTimeTo type, noloc",
                {"q": "ゲーム", "openTimeTo": 52149},
                None,
                ["openTimeTo"],
                str,
                int,
            ),
            tt(
                "startTimeFrom type",
                {"q": "ゲーム", "startTimeFrom": 52149},
                ["table"],
                ["table", "startTimeFrom"],
                str,
                int,
            ),
            tt(
                "startTimeFrom type, noloc",
                {"q": "ゲーム", "startTimeFrom": 52149},
                None,
                ["startTimeFrom"],
                str,
                int,
            ),
            tt(
                "startTimeTo type",
                {"q": "ゲーム", "startTimeTo": 52149},
                ["table"],
                ["table", "startTimeTo"],
                str,
                int,
            ),
            tt(
                "startTimeTo type, noloc",
                {"q": "ゲーム", "startTimeTo": 52149},
                None,
                ["startTimeTo"],
                str,
                int,
            ),
            tt(
                "liveEndTimeFrom type",
                {"q": "ゲーム", "liveEndTimeFrom": 52149},
                ["table"],
                ["table", "liveEndTimeFrom"],
                str,
                int,
            ),
            tt(
                "liveEndTimeFrom type, noloc",
                {"q": "ゲーム", "liveEndTimeFrom": 52149},
                None,
                ["liveEndTimeFrom"],
                str,
                int,
            ),
            tt(
                "liveEndTimeTo type",
                {"q": "ゲーム", "liveEndTimeTo": 52149},
                ["table"],
                ["table", "liveEndTimeTo"],
                str,
                int,
            ),
            tt(
                "liveEndTimeTo type, noloc",
                {"q": "ゲーム", "liveEndTimeTo": 52149},
                None,
                ["liveEndTimeTo"],
                str,
                int,
            ),
            tt(
                "ppv type",
                {"q": "ゲーム", "ppv": 52149},
                ["table"],
                ["table", "ppv"],
                bool,
                int,
            ),
            tt(
                "ppv type, noloc",
                {"q": "ゲーム", "ppv": 52149},
                None,
                ["ppv"],
                bool,
                int,
            ),
        ]:
            with self.subTest(tc.msg):
                with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
                    tsm.config.SearchConfig.from_toml(tc.put_obj, loc=tc.put_loc)
                self.assertEqual(ctx.exception.config_loc, tc.exp_loc)
                self.assertEqual(ctx.exception.config_want_type, tc.exp_type_want)
                self.assertEqual(ctx.exception.config_got_type, tc.exp_type_got)


class TestSearchConfigPrependPath(unittest.TestCase):
    def test(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put_cfg", tsm.config.SearchConfig),
                ("put_base", pathlib.Path),
                ("exp_cfg", tsm.config.SearchConfig),
            ],
        )

        with tempfile.TemporaryDirectory() as base:
            for tc in [
                tt(
                    "exists",
                    tsm.config.SearchConfig(
                        q="ゲーム",
                        jsonFilter="filters.json",
                    ),
                    pathlib.Path(base),
                    tsm.config.SearchConfig(
                        q="ゲーム",
                        jsonFilter=pathlib.Path(
                            base,
                            "filters.json",
                        ),
                    ),
                ),
                tt(
                    "none",
                    tsm.config.SearchConfig(q="ゲーム"),
                    pathlib.Path(base),
                    tsm.config.SearchConfig(q="ゲーム"),
                ),
            ]:
                with self.subTest(tc.msg):
                    cfg = copy.deepcopy(tc.put_cfg)
                    cfg.prepend_path(tc.put_base)
                    self.assertEqual(cfg, tc.exp_cfg)


class TestWarnConfigFromTOML(unittest.TestCase):
    def test_normal(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put", object),
                ("exp", tsm.config.WarnConfig),
            ],
        )

        for tc in [
            tt(
                "full",
                {
                    "tsNotSupported": False,
                    "tsRegistrationExpired": False,
                    "tsMaxReservation": False,
                },
                tsm.config.WarnConfig(
                    tsNotSupported=False,
                    tsRegistrationExpired=False,
                    tsMaxReservation=False,
                ),
            ),
            tt(
                "default",
                {},
                tsm.config.WarnConfig(),
            ),
        ]:
            with self.subTest(tc.msg):
                got = tsm.config.WarnConfig.from_toml(tc.put)
                self.assertEqual(got, tc.exp)

    def test_error_dict(self) -> None:
        with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
            tsm.config.WarnConfig.from_toml([], loc=["warn"])
        self.assertEqual(ctx.exception.config_loc, ["warn"])
        self.assertEqual(ctx.exception.config_want_type, dict)
        self.assertEqual(ctx.exception.config_got_type, list)

    def test_error_type(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put_obj", object),
                ("put_loc", list[int | str] | None),
                ("exp_loc", list[int | str]),
                ("exp_type_want", type),
                ("exp_type_got", type),
            ],
        )

        for tc in [
            tt(
                "tsNotSupported type",
                {"tsNotSupported": 0},
                ["table"],
                ["table", "tsNotSupported"],
                bool,
                int,
            ),
            tt(
                "tsNotSupported type, noloc",
                {"tsNotSupported": 0},
                None,
                ["tsNotSupported"],
                bool,
                int,
            ),
            tt(
                "tsRegistrationExpired type",
                {"tsRegistrationExpired": 0},
                ["table"],
                ["table", "tsRegistrationExpired"],
                bool,
                int,
            ),
            tt(
                "tsRegistrationExpired type, noloc",
                {"tsRegistrationExpired": 0},
                None,
                ["tsRegistrationExpired"],
                bool,
                int,
            ),
            tt(
                "tsMaxReservation type",
                {"tsMaxReservation": 0},
                ["table"],
                ["table", "tsMaxReservation"],
                bool,
                int,
            ),
            tt(
                "tsMaxReservation type, noloc",
                {"tsMaxReservation": 0},
                None,
                ["tsMaxReservation"],
                bool,
                int,
            ),
        ]:
            with self.subTest(tc.msg):
                with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
                    tsm.config.WarnConfig.from_toml(tc.put_obj, loc=tc.put_loc)
                self.assertEqual(ctx.exception.config_loc, tc.exp_loc)
                self.assertEqual(ctx.exception.config_want_type, tc.exp_type_want)
                self.assertEqual(ctx.exception.config_got_type, tc.exp_type_got)


class TestMiscConfigFromTOML(unittest.TestCase):
    def test_normal(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put", object),
                ("exp", tsm.config.MiscConfig),
            ],
        )

        for tc in [
            tt(
                "full",
                {
                    "overwrite": True,
                    "timeout": 300,
                    "userAgent": "ts_machine_ua (https://github.com/gcrtnst/ts_machine)",
                    "context": "ts_machine_ctx (https://github.com/gcrtnst/ts_machine)",
                },
                tsm.config.MiscConfig(
                    overwrite=True,
                    timeout=300,
                    userAgent="ts_machine_ua (https://github.com/gcrtnst/ts_machine)",
                    context="ts_machine_ctx (https://github.com/gcrtnst/ts_machine)",
                ),
            ),
            tt(
                "default",
                {},
                tsm.config.MiscConfig(),
            ),
        ]:
            with self.subTest(tc.msg):
                got = tsm.config.MiscConfig.from_toml(tc.put)
                self.assertEqual(got, tc.exp)

    def test_error_dict(self) -> None:
        with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
            tsm.config.MiscConfig.from_toml([], loc=["misc"])
        self.assertEqual(ctx.exception.config_loc, ["misc"])
        self.assertEqual(ctx.exception.config_want_type, dict)
        self.assertEqual(ctx.exception.config_got_type, list)

    def test_error_type(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put_obj", object),
                ("put_loc", list[int | str] | None),
                ("exp_loc", list[int | str]),
                ("exp_type_want", type),
                ("exp_type_got", type),
            ],
        )

        for tc in [
            tt(
                "overwrite type",
                {"overwrite": 1},
                ["table"],
                ["table", "overwrite"],
                bool,
                int,
            ),
            tt(
                "overwrite type, noloc",
                {"overwrite": 1},
                None,
                ["overwrite"],
                bool,
                int,
            ),
            tt(
                "timeout type",
                {"timeout": "300"},
                ["table"],
                ["table", "timeout"],
                int,
                str,
            ),
            tt(
                "timeout type, noloc",
                {"timeout": "300"},
                None,
                ["timeout"],
                int,
                str,
            ),
            tt(
                "userAgent type",
                {"userAgent": False},
                ["table"],
                ["table", "userAgent"],
                str,
                bool,
            ),
            tt(
                "userAgent type, noloc",
                {"userAgent": False},
                None,
                ["userAgent"],
                str,
                bool,
            ),
            tt(
                "context type",
                {"context": False},
                ["table"],
                ["table", "context"],
                str,
                bool,
            ),
            tt(
                "context type, noloc",
                {"context": False},
                None,
                ["context"],
                str,
                bool,
            ),
        ]:
            with self.subTest(tc.msg):
                with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
                    tsm.config.MiscConfig.from_toml(tc.put_obj, loc=tc.put_loc)
                self.assertEqual(ctx.exception.config_loc, tc.exp_loc)
                self.assertEqual(ctx.exception.config_want_type, tc.exp_type_want)
                self.assertEqual(ctx.exception.config_got_type, tc.exp_type_got)


class TestGetRequired(unittest.TestCase):
    def test_ok(self) -> None:
        validate = tsm.config.expect_type(str)
        self.assertEqual(
            tsm.config.get_required(validate, {"key": "test"}, "key"),
            "test",
        )

    def test_ng(self) -> None:
        validate = tsm.config.expect_type(str)
        loc = ["table"]
        with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
            tsm.config.get_required(validate, {"key": 0}, "key", loc=loc)
        self.assertEqual(ctx.exception.config_loc, ["table", "key"])
        self.assertIsNot(ctx.exception.config_loc, loc)
        self.assertIs(ctx.exception.config_want_type, str)
        self.assertIs(ctx.exception.config_got_type, int)

    def test_ng_noloc(self) -> None:
        validate = tsm.config.expect_type(str)
        with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
            tsm.config.get_required(validate, {"key": 0}, "key")
        self.assertEqual(ctx.exception.config_loc, ["key"])
        self.assertIs(ctx.exception.config_want_type, str)
        self.assertIs(ctx.exception.config_got_type, int)

    def test_ng_none(self) -> None:
        validate = tsm.config.expect_type(str)
        loc = ["table"]
        with self.assertRaises(tsm.config.ConfigRequiredError) as ctx:
            tsm.config.get_required(validate, {}, "key", loc=loc)
        self.assertEqual(ctx.exception.config_loc, ["table", "key"])
        self.assertIsNot(ctx.exception.config_loc, loc)

    def test_ng_none_noloc(self) -> None:
        validate = tsm.config.expect_type(str)
        with self.assertRaises(tsm.config.ConfigRequiredError) as ctx:
            tsm.config.get_required(validate, {}, "key")
        self.assertEqual(ctx.exception.config_loc, ["key"])


class TestGetOptional(unittest.TestCase):
    def test_ok(self) -> None:
        validate = tsm.config.expect_type(str)
        self.assertEqual(
            tsm.config.get_optional(validate, {"key": "test"}, "key"),
            "test",
        )

    def test_ok_none(self) -> None:
        validate = tsm.config.expect_type(str)
        self.assertIs(
            tsm.config.get_optional(validate, {}, "key"),
            None,
        )

    def test_ng(self) -> None:
        validate = tsm.config.expect_type(str)
        loc = ["table"]
        with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
            tsm.config.get_optional(validate, {"key": 0}, "key", loc=loc)
        self.assertEqual(ctx.exception.config_loc, ["table", "key"])
        self.assertIsNot(ctx.exception.config_loc, loc)
        self.assertIs(ctx.exception.config_want_type, str)
        self.assertIs(ctx.exception.config_got_type, int)

    def test_ng_noloc(self) -> None:
        validate = tsm.config.expect_type(str)
        with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
            tsm.config.get_optional(validate, {"key": 0}, "key")
        self.assertEqual(ctx.exception.config_loc, ["key"])
        self.assertIs(ctx.exception.config_want_type, str)
        self.assertIs(ctx.exception.config_got_type, int)


class TestGetDefault(unittest.TestCase):
    def test_ok_scalar(self) -> None:
        validate = tsm.config.expect_type(str)
        self.assertEqual(
            tsm.config.get_default(validate, {"key": "test"}, "key", "default"),
            "test",
        )

    def test_ok_scalar_none(self) -> None:
        validate = tsm.config.expect_type(str)
        self.assertEqual(
            tsm.config.get_default(validate, {}, "key", "default"),
            "default",
        )

    def test_ok_list(self) -> None:
        validate = tsm.config.expect_list(tsm.config.expect_type(str))
        put = ["foo", "bar", "baz"]
        got = tsm.config.get_default(validate, {"key": put}, "key", ["default"])
        self.assertEqual(got, put)
        self.assertIsNot(got, put)

    def test_ok_list_none(self) -> None:
        validate = tsm.config.expect_list(tsm.config.expect_type(str))
        put = ["foo", "bar", "baz"]
        got = tsm.config.get_default(validate, {}, "key", put)
        self.assertEqual(got, put)
        self.assertIsNot(got, put)

    def test_ng(self) -> None:
        validate = tsm.config.expect_type(str)
        loc = ["table"]
        with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
            tsm.config.get_default(validate, {"key": 0}, "key", "default", loc=loc)
        self.assertEqual(ctx.exception.config_loc, ["table", "key"])
        self.assertIsNot(ctx.exception.config_loc, loc)
        self.assertIs(ctx.exception.config_want_type, str)
        self.assertIs(ctx.exception.config_got_type, int)

    def test_ng_noloc(self) -> None:
        validate = tsm.config.expect_type(str)
        with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
            tsm.config.get_default(validate, {"key": 0}, "key", "default")
        self.assertEqual(ctx.exception.config_loc, ["key"])
        self.assertIs(ctx.exception.config_want_type, str)
        self.assertIs(ctx.exception.config_got_type, int)


class TestExpectType(unittest.TestCase):
    def test_ok_str(self) -> None:
        self.assertEqual(
            tsm.config.expect_type(str)("str", loc=["obj"]),
            "str",
        )

    def test_ok_int(self) -> None:
        self.assertEqual(
            tsm.config.expect_type(int)(52149, loc=["obj"]),
            52149,
        )

    def test_ok_bool(self) -> None:
        self.assertEqual(
            tsm.config.expect_type(bool)(True, loc=["obj"]),
            True,
        )

    def test_ng_int2str(self) -> None:
        validate = tsm.config.expect_type(str)
        with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
            validate(52149, loc=["obj"])
        self.assertEqual(ctx.exception.config_loc, ["obj"])
        self.assertEqual(ctx.exception.config_want_type, str)
        self.assertEqual(ctx.exception.config_got_type, int)

    def test_ng_bool2int(self) -> None:
        validate = tsm.config.expect_type(int)
        with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
            validate(True, loc=["obj"])
        self.assertEqual(ctx.exception.config_loc, ["obj"])
        self.assertEqual(ctx.exception.config_want_type, int)
        self.assertEqual(ctx.exception.config_got_type, bool)


class TestExpectList(unittest.TestCase):
    def test_ok(self) -> None:
        validate = tsm.config.expect_list(tsm.config.expect_type(str))
        put = ["foo", "bar", "baz"]
        got = validate(put, loc=["obj"])
        self.assertEqual(got, put)
        self.assertIsNot(got, put)

    def test_ng_obj(self) -> None:
        validate = tsm.config.expect_list(tsm.config.expect_type(str))
        with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
            validate("list", loc=["obj"])
        self.assertEqual(ctx.exception.config_loc, ["obj"])
        self.assertEqual(ctx.exception.config_want_type, list)
        self.assertEqual(ctx.exception.config_got_type, str)

    def test_ng_elm(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put_type", type),
                ("put_obj", object),
                ("put_loc", list[int | str]),
                ("exp_loc", list[int | str]),
                ("exp_type_want", type),
                ("exp_type_got", type),
            ],
        )

        for tc in [
            tt(
                "index 0",
                str,
                [52149, "bar", "baz"],
                ["table", "key"],
                ["table", "key", 0],
                str,
                int,
            ),
            tt(
                "index 1",
                str,
                ["foo", 52149, "baz"],
                ["table", "key"],
                ["table", "key", 1],
                str,
                int,
            ),
            tt(
                "index 2",
                str,
                ["foo", "bar", 52149],
                ["table", "key"],
                ["table", "key", 2],
                str,
                int,
            ),
        ]:
            with self.subTest(tc.msg):
                validate = tsm.config.expect_list(tsm.config.expect_type(tc.put_type))
                with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
                    validate(tc.put_obj, loc=tc.put_loc)
                self.assertEqual(ctx.exception.config_loc, tc.exp_loc)
                self.assertEqual(ctx.exception.config_want_type, tc.exp_type_want)
                self.assertEqual(ctx.exception.config_got_type, tc.exp_type_got)


class TestExpectDict(unittest.TestCase):
    def test_ok(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put_obj", object),
                ("put_loc", list[int | str]),
            ],
        )

        validate = tsm.config.expect_dict()
        for tc in [
            tt(
                "normal",
                {"a": "A", "b": "B", "c": "C"},
                ["table", "key"],
            ),
            tt(
                "empty",
                {},
                ["table", "key"],
            ),
        ]:
            with self.subTest(tc.msg):
                got_obj = validate(tc.put_obj, loc=tc.put_loc)
                self.assertEqual(got_obj, tc.put_obj)
                self.assertIsNot(got_obj, tc.put_obj)

    def test_ng_obj(self) -> None:
        validate = tsm.config.expect_dict()
        with self.assertRaises(tsm.config.ConfigTypeError) as ctx:
            validate("dict", loc=["obj"])
        self.assertEqual(ctx.exception.config_loc, ["obj"])
        self.assertEqual(ctx.exception.config_want_type, dict)
        self.assertEqual(ctx.exception.config_got_type, str)

    def test_ng_key(self) -> None:
        if not __debug__:
            self.skipTest("assertions are disabled")

        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put_obj", object),
                ("put_loc", list[int | str]),
            ],
        )

        validate = tsm.config.expect_dict()
        for tc in [
            tt(
                "key 1",
                {1: "A", "2": "B", "3": "C"},
                ["table", "key"],
            ),
            tt(
                "key 2",
                {"1": "A", 2: "B", "3": "C"},
                ["table", "key"],
            ),
            tt(
                "key 3",
                {"1": "A", "2": "B", 3: "C"},
                ["table", "key"],
            ),
        ]:
            with self.subTest(tc.msg):
                with self.assertRaises(AssertionError):
                    validate(tc.put_obj, loc=tc.put_loc)


class TestConfigErrorInit(unittest.TestCase):
    def test(self) -> None:
        loc = ["table", "key"]
        args = (loc, "extra")
        exc = tsm.config.ConfigError(*args)
        self.assertEqual(exc.config_loc, loc)
        self.assertIsNot(exc.config_loc, loc)
        self.assertEqual(exc.args, args)


class TestConfigErrorStr(unittest.TestCase):
    def test(self) -> None:
        exc = tsm.config.ConfigError(["server", "example.com"])
        self.assertEqual(str(exc), 'config: server."example.com"')


class TestConfigRequiredErrorStr(unittest.TestCase):
    def test(self) -> None:
        exc = tsm.config.ConfigRequiredError(["server", "example.com"])
        self.assertEqual(str(exc), 'config: server."example.com": is required')


class TestConfigTypeErrorInit(unittest.TestCase):
    def test(self) -> None:
        loc = ["table", "key"]
        want_type = str
        got_type = int
        args = (loc, want_type, got_type, "extra")
        exc = tsm.config.ConfigTypeError(*args)
        self.assertEqual(exc.config_loc, loc)
        self.assertIsNot(exc.config_loc, loc)
        self.assertEqual(exc.config_want_type, want_type)
        self.assertEqual(exc.config_got_type, got_type)
        self.assertEqual(exc.args, args)


class TestConfigTypeErrorStr(unittest.TestCase):
    def test(self) -> None:
        self.assertEqual(
            str(tsm.config.ConfigTypeError(["server", "example.com"], str, int)),
            'config: server."example.com": expected str, got int',
        )


class TestFormatTOMLLoc(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(
            tsm.config.format_toml_loc([]),
            "",
        )

    def test_output(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put", list[int | str]),
                ("exp", str),
            ],
        )

        for tc in [
            tt(
                "str",
                ["server", "example.com", "C:\\"],
                'server."example.com"."C:\\\\"',
            ),
            tt(
                "int",
                ["arr", 2, 3, "key"],
                "arr[2][3].key",
            ),
        ]:
            with self.subTest(tc.msg):
                got = tsm.config.format_toml_loc(tc.put)
                self.assertEqual(got, tc.exp)

    def test_parse(self) -> None:
        raw_loc = ["server", "example.com", "C:\\"]
        raw_obj = {"server": {"example.com": {"C:\\": "OK"}}}

        fmt_loc = tsm.config.format_toml_loc(raw_loc)
        fmt_obj = f'{fmt_loc} = "OK"'
        got_obj = tomllib.loads(fmt_obj)
        self.assertEqual(got_obj, raw_obj)


class TestFormatTOMLIdx(unittest.TestCase):
    def test(self) -> None:
        self.assertEqual(
            tsm.config.format_toml_idx(52149),
            "[52149]",
        )


class TestFormatTOMLKey(unittest.TestCase):
    def test_output(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put_key", str),
                ("exp_key", str),
            ],
        )

        for tc in [
            # bare
            tt("bare/alphabetic", "name", "name"),
            tt("bare/alphanumeric", "Key28", "Key28"),
            tt("bare/underscore", "my_key_name", "my_key_name"),
            tt("bare/dash", "dashed-key", "dashed-key"),
            tt("bare/numbers only", "1234", "1234"),
            # quoted
            tt("quoted/dot", "example.com", '"example.com"'),
            tt("quoted/space", "key name", '"key name"'),
            tt("quoted/symbol", "(parentheses)", '"(parentheses)"'),
            tt("quoted/ip", "127.0.0.1", '"127.0.0.1"'),
            tt("quoted/empty", "", '""'),
            # escape
            tt("escape/quote", 'quote"key', '"quote\\"key"'),
            tt("escape/backslash", "C:\\path", '"C:\\\\path"'),
            tt("escape/compact escape", "line\nbreak", '"line\\nbreak"'),
            tt("escape/unicode escape", "VT \v", '"VT \\u000B"'),
            # unicode
            tt("unicode/🍎", "🍎", '"🍎"'),
            tt("unicode/日本語", "日本語", '"日本語"'),
        ]:
            with self.subTest(tc.msg):
                got_key = tsm.config.format_toml_key(tc.put_key)
                self.assertEqual(got_key, tc.exp_key)

    def test_parse(self) -> None:
        tt = typing.NamedTuple("tt", [("msg", str), ("raw_key", str)])

        for tc in [
            # bare
            tt("bare/alphabetic", "name"),
            tt("bare/alphanumeric", "Key28"),
            tt("bare/underscore", "my_key_name"),
            tt("bare/dash", "dashed-key"),
            tt("bare/numbers only", "1234"),
            # quoted
            tt("quoted/dot", "example.com"),
            tt("quoted/space", "key name"),
            tt("quoted/symbol", "(parentheses)"),
            tt("quoted/ip", "127.0.0.1"),
            tt("quoted/empty", ""),
            # escape
            tt("escape/quote", 'quote"key'),
            tt("escape/backslash", "C:\\path"),
            tt("escape/compact escape", "line\nbreak"),
            tt("escape/unicode escape", "VT \v"),
            # unicode
            tt("unicode/🍎", "🍎"),
            tt("unicode/日本語", "日本語"),
        ]:
            with self.subTest(tc.msg):
                fmt_key = tsm.config.format_toml_key(tc.raw_key)

                raw_obj = {tc.raw_key: "OK"}
                fmt_obj = f'{fmt_key} = "OK"'
                got_obj = tomllib.loads(fmt_obj)
                self.assertEqual(got_obj, raw_obj)


class TestFormatTOMLKeyQuoted(unittest.TestCase):
    def test_output(self) -> None:
        tt = typing.NamedTuple(
            "tt",
            [
                ("msg", str),
                ("put_key", str),
                ("exp_key", str),
            ],
        )

        for tc in [
            tt("alphabetic", "name", '"name"'),
            tt("dot", "example.com", '"example.com"'),
            tt("quote", 'quote"key', '"quote\\"key"'),
        ]:
            with self.subTest(tc.msg):
                got_key = tsm.config.format_toml_key_quoted(tc.put_key)
                self.assertEqual(got_key, tc.exp_key)

    def test_parse(self) -> None:
        tt = typing.NamedTuple("tt", [("msg", str), ("raw_key", str)])

        for tc in [
            tt("alphabetic", "name"),
            tt("dot", "example.com"),
            tt("quote", 'quote"key'),
        ]:
            with self.subTest(tc.msg):
                fmt_key = tsm.config.format_toml_key_quoted(tc.raw_key)

                raw_obj = {tc.raw_key: "OK"}
                fmt_obj = f'{fmt_key} = "OK"'
                got_obj = tomllib.loads(fmt_obj)
                self.assertEqual(got_obj, raw_obj)
