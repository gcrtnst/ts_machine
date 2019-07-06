import contextlib
import functools
import itertools
import json
import re
import sys
from argparse import ArgumentParser
from datetime import timedelta
from http.cookiejar import LWPCookieJar
from json import JSONDecodeError
from pathlib import Path

import dateutil.tz
import toml
from cerberus import Validator
from toml import TomlDecodeError

from niconico import (CommunicationError, ContentSearchError, LoginFailed,
                      Niconico, Timeout, TSAlreadyRegistered, TSMaxReservation,
                      TSNotSupported, TSRegistrationExpired)

_re_timedelta = re.compile(r'^(?P<minus>-?)((?P<weeks>[0-9]+)w)?'
                           r'((?P<days>[0-9]+)d)?((?P<hours>[0-9]+)h)?'
                           r'((?P<minutes>[0-9]+)m)?((?P<seconds>[0-9]+)s)?'
                           r'((?P<milliseconds>[0-9]+)ms)?'
                           r'((?P<microseconds>[0-9]+)us)?$')


def parse_timedelta(s):
    match = _re_timedelta.search(s)
    if not match:
        raise ValueError('invalid timedelta: "{}"'.format(s))

    kwargs = {}
    for key in ['weeks', 'days', 'hours', 'minutes',
                'seconds', 'milliseconds', 'microseconds']:
        value = match.group(key)
        if value is not None:
            kwargs[key] = int(value)
    if match.group('minus'):
        return -timedelta(**kwargs)
    return timedelta(**kwargs)


def _tsm_run(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except ContentSearchError as e:
            if e.meta['status'] == 400:
                raise
            self.print_err('error: {}'.format(e))
        except (CommunicationError, LoginFailed, Timeout) as e:
            self.print_err('error: {}'.format(e))
        return 1
    return wrapper


class TSMachine:
    def __init__(self):
        self._niconico = Niconico()
        self._niconico.tz = dateutil.tz.gettz()

        self.filters = {}
        self.overwrite = False
        self.warnings = {'ts_not_supported',
                         'ts_max_reservation', 'ts_registration_expired'}
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    @property
    def mail(self):
        return self._niconico.mail

    @mail.setter
    def mail(self, value):
        self._niconico.mail = value

    @property
    def password(self):
        return self._niconico.password

    @password.setter
    def password(self, value):
        self._niconico.password = value

    @property
    def cookies(self):
        return self._niconico.cookies

    @cookies.setter
    def cookies(self, value):
        self._niconico.cookies = value

    @property
    def timeout(self):
        return self._niconico.timeout

    @timeout.setter
    def timeout(self, value):
        self._niconico.timeout = value

    @property
    def user_agent(self):
        return self._niconico.user_agent

    @user_agent.setter
    def user_agent(self, value):
        self._niconico.user_agent = value

    @property
    def context(self):
        return self._niconico.context

    @context.setter
    def context(self, value):
        self._niconico.context = value

    @property
    def tz(self):
        return self._niconico.tz

    @tz.setter
    def tz(self, value):
        self._niconico.tz = value

    def close_connection(self):
        return self._niconico.close_connection()

    def __enter__(self):
        self._niconico.__enter__()
        return self

    def __exit__(self, *args):
        return self._niconico.__exit__(*args)

    def ts_register(self, live_id):
        self._niconico.ts_register(live_id, overwrite=self.overwrite)

    def contents_search_json_filter(self, now=None):
        filters = []
        if 'jsonFilter' in self.filters:
            filters.append(self.filters['jsonFilter'])
        for field, timefrom, timeto in [
                ('openTime', 'openTimeFrom', 'openTimeTo'),
                ('startTime', 'startTimeFrom', 'startTimeTo'),
                ('liveEndTime', 'liveEndTimeFrom', 'liveEndTimeTo'),
        ]:
            if timefrom not in self.filters and timeto not in self.filters:
                continue
            if now is None:
                now = self._niconico.server_time()

            f = {'type': 'range', 'field': field}
            if timefrom in self.filters:
                dt = now + parse_timedelta(self.filters[timefrom])
                f['from'] = dt.isoformat(timespec='seconds')
                f['include_lower'] = True
            if timeto in self.filters:
                dt = now + parse_timedelta(self.filters[timeto])
                f['to'] = dt.isoformat(timespec='seconds')
                f['include_upper'] = True
            filters.append(f)

        if len(filters) == 0:
            return None
        if len(filters) == 1:
            return filters[0]
        return {'type': 'and', 'filters': filters}

    def match_ppv(self, live_id, channel_id):
        if 'ppv' not in self.filters:
            return True
        is_ppv = (channel_id is not None
                  and self._niconico.is_ppv_live(live_id, channel_id))
        return is_ppv == self.filters['ppv']

    def iter_search(self, fields=set()):
        search_fields = {'contentId'} | set(fields)
        if 'ppv' in self.filters:
            search_fields.add('channelId')
        iter_contents = self._niconico.contents_search(
            self.filters['q'],
            service='live',
            targets=self.filters['targets'],
            fields=search_fields,
            json_filter=self.contents_search_json_filter(),
            sort=self.filters['sort'])

        for content in iter_contents:
            if 'ppv' in self.filters and not self.match_ppv(
                    content['contentId'], content['channelId']):
                continue
            yield {k: v for k, v in content.items() if k in fields}

    def print(self, *args, **kwargs):
        kwargs['file'] = self.stdout
        print(*args, **kwargs)

    def print_err(self, *args, **kwargs):
        kwargs['file'] = self.stderr
        print(*args, **kwargs)

    def print_diff(self, ts_list_before, ts_list_after):
        for ts in ts_list_after:
            if ts['vid'] in (ts['vid'] for ts in ts_list_before):
                continue
            self.print('added: ' + ts['vid'] + ': ' + ts['title'])

        for ts in ts_list_before:
            if ts['vid'] in (ts['vid'] for ts in ts_list_after):
                continue
            self.print('removed: ' + ts['vid'] + ': ' + ts['title'])

    @_tsm_run
    def run_search_only(self, n):
        iter_search = self.iter_search(fields={'contentId', 'title'})
        iter_search = itertools.islice(iter_search, n)
        for content in iter_search:
            self.print(content['contentId'] + ': ' + content['title'])
        return 0

    @_tsm_run
    def run_auto_reserve(self):
        ts_list_before = self._niconico.ts_list()
        for content in self.iter_search(fields={'contentId'}):
            if content['contentId'] in (ts['vid'] for ts in ts_list_before):
                continue
            try:
                self.ts_register(content['contentId'])
            except TSNotSupported as e:
                if 'ts_not_supported' in self.warnings:
                    self.print_err('warning: {}'.format(e))
                continue
            except TSAlreadyRegistered:
                continue
            except TSRegistrationExpired as e:
                if 'ts_registration_expired' in self.warnings:
                    self.print_err('warning: {}'.format(e))
                continue
            except TSMaxReservation as e:
                if 'ts_max_reservation' in self.warnings:
                    self.print_err('warning: {}'.format(e))
                break

        ts_list_after = self._niconico.ts_list()
        self.print_diff(ts_list_before, ts_list_after)
        return 0


config_schema = {
    'login': {
        'type': 'dict',
        'required': True,
        'schema': {
            'mail': {'type': 'string', 'required': True},
            'password': {'type': 'string', 'required': True},
            'cookieJar': {'type': 'string'},
        },
    },
    'search': {
        'type': 'dict',
        'required': True,
        'schema': {
            'q': {'type': 'string', 'required': True},
            'targets': {'type': 'list', 'valuesrules': {'type': 'string'},
                        'default': ['title', 'description', 'tags']},
            'sort': {'type': 'string', 'default': '+startTime'},
            'jsonFilter': {'type': 'string'},
            'openTimeFrom': {'type': 'string'},
            'openTimeTo': {'type': 'string'},
            'startTimeFrom': {'type': 'string'},
            'startTimeTo': {'type': 'string'},
            'liveEndTimeFrom': {'type': 'string'},
            'liveEndTimeTo': {'type': 'string'},
            'ppv': {'type': 'boolean'},
        },
    },
    'warn': {
        'type': 'dict',
        'default': {},
        'schema': {
            'tsNotSupported': {'type': 'boolean', 'default': True},
            'tsRegistrationExpired': {'type': 'boolean', 'default': True},
            'tsMaxReservation': {'type': 'boolean', 'default': True},
        },
    },
    'misc': {
        'type': 'dict',
        'default': {},
        'schema': {
            'overwrite': {'type': 'boolean', 'default': False},
            'timeout': {'type': 'number'},
            'userAgent': {'type': 'string'},
            'context': {'type': 'string'},
        },
    },
}


class ConfigError(Exception):
    pass


def load_config(path):
    path = Path(path)
    try:
        with path.open() as f:
            config = toml.load(f)
    except TomlDecodeError as e:
        raise ConfigError('config: toml: {}'.format(e))

    v = Validator(config_schema)
    if not v.validate(config):
        raise ConfigError('config: {}'.format(v.errors))
    config = v.document

    basepath = path.parent
    if 'cookieJar' in config['login']:
        config['login']['cookieJar'] = Path(
            basepath, config['login']['cookieJar'])
    if 'jsonFilter' in config['search']:
        config['search']['jsonFilter'] = Path(
            basepath, config['search']['jsonFilter'])
    return config


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
        if filename is None:
            return
        filename.touch(mode=filemode)
        jar.save(str(filename))


def main():
    argp = ArgumentParser()
    argp.add_argument(
        '-c', '--config', type=Path,
        default=Path('~', '.config', 'tsm', 'config.toml').expanduser(),
        help='TOML-formatted configuration file (default: %(default)s)')
    argp.add_argument(
        '-s', '--search', type=int, nargs='?', const=10, metavar='N',
        help=('search only mode; \n'
              'N specifies maximum number of programs to search \n'
              '(default: %(const)s)'))
    argv = argp.parse_args()

    try:
        config = load_config(argv.config)
    except OSError as e:
        sys.exit("error: config '{}': {}".format(argv.config, e.strerror))
    except ConfigError as e:
        sys.exit('error: ' + str(e))

    filters = config['search'].copy()
    if 'jsonFilter' in config['search']:
        try:
            with Path(config['search']['jsonFilter']).open() as f:
                filters['jsonFilter'] = json.load(f)
        except OSError as e:
            sys.exit("error: jsonFilter '{}': {}".format(
                config['search']['jsonFilter'], e.strerror))
        except JSONDecodeError as e:
            sys.exit("error: jsonFilter: {}".format(e))

    with lwp_cookiejar(filename=config['login'].get('cookieJar'),
                       filemode=0o600) as jar, TSMachine() as tsm:
        tsm.mail = config['login']['mail']
        tsm.password = config['login']['password']
        tsm.cookies = jar
        tsm.timeout = config['misc'].get('timeout')
        tsm.user_agent = config['misc'].get('userAgent')
        tsm.context = config['misc'].get('context')
        tsm.filters = filters
        tsm.overwrite = config['misc']['overwrite']
        tsm.warnings = set()
        if config['warn']['tsNotSupported']:
            tsm.warnings.add('ts_not_supported')
        if config['warn']['tsRegistrationExpired']:
            tsm.warnings.add('ts_registration_expired')
        if config['warn']['tsMaxReservation']:
            tsm.warnings.add('ts_max_reservation')
        if argv.search is not None:
            sys.exit(tsm.run_search_only(argv.search))
        sys.exit(tsm.run_auto_reserve())


if __name__ == '__main__':
    main()
