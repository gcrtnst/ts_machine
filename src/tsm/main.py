import argparse
import contextlib
import http.cookiejar
import json
import pathlib
import sys
import tomllib

import tsm
import tsm.config


@contextlib.contextmanager
def lwp_cookiejar(filename=None, filemode=0o666):
    if filename is not None:
        filename = pathlib.Path(filename)

    jar = http.cookiejar.LWPCookieJar()
    if filename is not None and filename.exists():
        jar.load(str(filename))
    try:
        yield jar
    finally:
        if filename is not None:
            filename.touch(mode=filemode)
            jar.save(str(filename))


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument(
        "-c",
        "--config",
        type=pathlib.Path,
        default=pathlib.Path("~", ".config", "tsm", "config.toml").expanduser(),
        help="TOML-formatted configuration file (default: %(default)s)",
    )
    argp.add_argument(
        "-s",
        "--search",
        type=int,
        nargs="?",
        const=10,
        metavar="N",
        help=(
            "search only mode; \n"
            "N specifies maximum number of programs to search \n"
            "(default: %(const)s)"
        ),
    )
    argv = argp.parse_args()

    try:
        config = tsm.config.load(argv.config)
    except OSError as e:
        sys.exit("error: config '{}': {}".format(argv.config, e.strerror))
    except tomllib.TOMLDecodeError as e:
        sys.exit("error: config: toml: {}".format(e))
    except tsm.config.ConfigError as e:
        sys.exit("error: config: {}".format(e))

    filter_list = []
    for filter_cfg in config.search:
        jsonFilter = None
        if filter_cfg.jsonFilter is not None:
            try:
                with open(filter_cfg.jsonFilter, mode="rb") as f:
                    jsonFilter = json.load(f)
            except OSError as e:
                sys.exit(
                    "error: jsonFilter '{}': {}".format(
                        filter_cfg.jsonFilter, e.strerror
                    )
                )
            except json.JSONDecodeError as e:
                sys.exit("error: jsonFilter: {}".format(e))

        filter_list.append(
            tsm.Filter(
                q=filter_cfg.q,
                targets=filter_cfg.targets,
                sort=filter_cfg.sort,
                jsonFilter=jsonFilter,
                openTimeFrom=filter_cfg.openTimeFrom,
                openTimeTo=filter_cfg.openTimeTo,
                startTimeFrom=filter_cfg.startTimeFrom,
                startTimeTo=filter_cfg.startTimeTo,
                liveEndTimeFrom=filter_cfg.liveEndTimeFrom,
                liveEndTimeTo=filter_cfg.liveEndTimeTo,
                ppv=filter_cfg.ppv,
            )
        )

    with (
        lwp_cookiejar(filename=config.login.cookieJar, filemode=0o600) as jar,
        tsm.TSMachine() as mac,
    ):
        mac.mail = config.login.mail
        mac.password = config.login.password
        mac.cookies = jar
        mac.timeout = config.misc.timeout
        mac.user_agent = config.misc.userAgent
        mac.context = config.misc.context
        mac.filter_list = filter_list
        mac.overwrite = config.misc.overwrite
        mac.warnings = set()
        if config.warn.tsNotSupported:
            mac.warnings.add("ts_not_supported")
        if config.warn.tsRegistrationExpired:
            mac.warnings.add("ts_registration_expired")
        if config.warn.tsMaxReservation:
            mac.warnings.add("ts_max_reservation")
        if argv.search is not None:
            sys.exit(mac.run_search_only(argv.search))
        sys.exit(mac.run_auto_reserve())


if __name__ == "__main__":
    main()
