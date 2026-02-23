import unittest
import unittest.mock

import tsm.niconico.client
import tsm.niconico.utils
import tsm.niconico.exceptions


class TestNiconico(unittest.TestCase):
    def test_login_if_required(self):
        n = unittest.mock.Mock(spec_set=tsm.niconico.client.Niconico())
        n.mail = None
        n.password = None
        func = unittest.mock.Mock()
        tsm.niconico.client._login_if_required(func)(n)
        self.assertEqual(n.mock_calls, [])
        self.assertEqual(func.mock_calls, [unittest.mock.call(n)])

        n = unittest.mock.Mock(spec_set=tsm.niconico.client.Niconico())
        n.mail = None
        n.password = None
        func = unittest.mock.Mock(side_effect=tsm.niconico.exceptions.LoginRequired)
        with self.assertRaises(tsm.niconico.exceptions.LoginRequired):
            tsm.niconico.client._login_if_required(func)(n)
        self.assertEqual(n.mock_calls, [])
        self.assertEqual(func.mock_calls, [unittest.mock.call(n)])

        n = unittest.mock.Mock(spec_set=tsm.niconico.client.Niconico())
        n.mail = "email@example.com"
        n.password = "password"
        func = unittest.mock.Mock(
            side_effect=[tsm.niconico.exceptions.LoginRequired, None]
        )
        tsm.niconico.client._login_if_required(func)(n)
        self.assertEqual(n.mock_calls, [unittest.mock.call.login()])
        self.assertEqual(
            func.mock_calls, [unittest.mock.call(n), unittest.mock.call(n)]
        )

        n = unittest.mock.Mock(spec_set=tsm.niconico.client.Niconico())
        n.mail = "email@example.com"
        n.password = "password"
        func = unittest.mock.Mock(
            side_effect=[
                tsm.niconico.exceptions.LoginRequired,
                tsm.niconico.exceptions.LoginRequired,
            ]
        )
        with self.assertRaises(tsm.niconico.exceptions.LoginFailed):
            tsm.niconico.client._login_if_required(func)(n)
        self.assertEqual(n.mock_calls, [unittest.mock.call.login()])
        self.assertEqual(
            func.mock_calls, [unittest.mock.call(n), unittest.mock.call(n)]
        )

    def test_http_request(self):
        n = tsm.niconico.client.Niconico()
        n.timeout = None
        n._session = unittest.mock.Mock(spec_set=n._session)
        n._http_request("method", "url")
        self.assertEqual(
            n._session.mock_calls,
            [unittest.mock.call.request("method", "url", timeout=None)],
        )

        n = tsm.niconico.client.Niconico()
        n.timeout = 1
        n._session = unittest.mock.Mock(spec_set=n._session)
        n._http_request("method", "url")
        self.assertEqual(
            n._session.mock_calls,
            [unittest.mock.call.request("method", "url", timeout=1)],
        )

        n = tsm.niconico.client.Niconico()
        n.timeout = None
        n._session = unittest.mock.Mock(spec_set=n._session)
        n._http_request("method", "url", timeout=2)
        self.assertEqual(
            n._session.mock_calls,
            [unittest.mock.call.request("method", "url", timeout=2)],
        )

        n = tsm.niconico.client.Niconico()
        n.timeout = 1
        n._session = unittest.mock.Mock(spec_set=n._session)
        n._http_request("method", "url", timeout=2)
        self.assertEqual(
            n._session.mock_calls,
            [unittest.mock.call.request("method", "url", timeout=2)],
        )

    def test_login(self):
        n = tsm.niconico.client.Niconico()
        n.mail = None
        n.password = None
        n._http_request = unittest.mock.Mock(spec_set=n._http_request)
        with self.assertRaises(tsm.niconico.exceptions.LoginFailed):
            n.login()
        self.assertEqual(n._http_request.mock_calls, [])

        resp = unittest.mock.Mock()
        resp.cookies = []
        n = tsm.niconico.client.Niconico()
        n.mail = "mail@example.com"
        n.password = "password"
        n._http_request = unittest.mock.Mock(
            spec_set=n._http_request, return_value=resp
        )
        with self.assertRaises(tsm.niconico.exceptions.LoginFailed):
            n.login()
        self.assertEqual(
            n._http_request.mock_calls,
            [
                unittest.mock.call(
                    "post",
                    "https://account.nicovideo.jp/api/v1/login",
                    data={
                        "mail_tel": "mail@example.com",
                        "password": "password",
                    },
                    allow_redirects=False,
                )
            ],
        )
        self.assertEqual(resp.mock_calls, [unittest.mock.call.raise_for_status()])

        cookie = unittest.mock.Mock()
        cookie.name = "user_session"
        resp = unittest.mock.Mock()
        resp.cookies = [cookie]
        n = tsm.niconico.client.Niconico()
        n.mail = "mail@example.com"
        n.password = "password"
        n._http_request = unittest.mock.Mock(
            spec_set=n._http_request, return_value=resp
        )
        n.login()
        self.assertEqual(
            n._http_request.mock_calls,
            [
                unittest.mock.call(
                    "post",
                    "https://account.nicovideo.jp/api/v1/login",
                    data={
                        "mail_tel": "mail@example.com",
                        "password": "password",
                    },
                    allow_redirects=False,
                )
            ],
        )
        self.assertEqual(resp.mock_calls, [unittest.mock.call.raise_for_status()])


class TestNiconicoUtils(unittest.TestCase):
    def test_parse_id(self):
        for c in [(10, (None, 10)), ("10", (None, 10)), ("lv10", ("lv", 10))]:
            self.assertEqual(tsm.niconico.utils.parse_id(c[0]), c[1])

        with self.assertRaises(tsm.niconico.exceptions.InvalidContentID):
            tsm.niconico.utils.parse_id("lv")
