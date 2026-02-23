import contextlib
import json
import sys
import tomllib
from argparse import ArgumentParser
from http.cookiejar import LWPCookieJar
from json import JSONDecodeError
from pathlib import Path
from tomllib import TOMLDecodeError

from . import config as tsm_config
from .tsm import TSMachine, Filter


@contextlib.contextmanager
def lwp_cookiejar(filename=None, filemode=0o666):
    if filename is not None:
        filename = Path(filename)

    jar = LWPCookieJar()
    if filename is not None and filename.exists():
        jar.load(str(filename))
    try:
        yield jar
    finally:
        if filename is not None:
            filename.touch(mode=filemode)
            jar.save(str(filename))


def main():
    argp = ArgumentParser()
    argp.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path("~", ".config", "tsm", "config.toml").expanduser(),
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
        config = tsm_config.load(argv.config)
    except OSError as e:
        sys.exit("error: config '{}': {}".format(argv.config, e.strerror))
    except TOMLDecodeError as e:
        sys.exit("error: config: toml: {}".format(e))
    except tsm_config.ConfigError as e:
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
            except JSONDecodeError as e:
                sys.exit("error: jsonFilter: {}".format(e))

        filter_list.append(
            Filter(
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
        TSMachine() as tsm,
    ):
        tsm.mail = config.login.mail
        tsm.password = config.login.password
        tsm.cookies = jar
        tsm.timeout = config.misc.timeout
        tsm.user_agent = config.misc.userAgent
        tsm.context = config.misc.context
        tsm.filter_list = filter_list
        tsm.overwrite = config.misc.overwrite
        tsm.warnings = set()
        if config.warn.tsNotSupported:
            tsm.warnings.add("ts_not_supported")
        if config.warn.tsRegistrationExpired:
            tsm.warnings.add("ts_registration_expired")
        if config.warn.tsMaxReservation:
            tsm.warnings.add("ts_max_reservation")
        if argv.search is not None:
            sys.exit(tsm.run_search_only(argv.search))
        sys.exit(tsm.run_auto_reserve())


if __name__ == "__main__":
    main()
