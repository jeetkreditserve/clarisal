from __future__ import annotations

import json
import ssl
from dataclasses import dataclass
from http.cookies import SimpleCookie
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import (
    BaseHandler,
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    HTTPSHandler,
    Request,
    build_opener,
)


class RequestError(Exception):
    pass


@dataclass
class HTTPDigestAuth:
    username: str
    password: str


class Response:
    def __init__(self, *, status_code: int, headers, body: bytes):
        self.status_code = status_code
        self.headers = headers
        self._body = body
        self.cookies = self._parse_cookies(headers)

    @staticmethod
    def _parse_cookies(headers):
        cookie_header = headers.get('Set-Cookie', '') if headers else ''
        cookie = SimpleCookie()
        if cookie_header:
            cookie.load(cookie_header)
        return {key: morsel.value for key, morsel in cookie.items()}

    def json(self):
        if not self._body:
            return {}
        return json.loads(self._body.decode('utf-8'))

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RequestError(f'HTTP {self.status_code}')


def _build_opener(*, auth: HTTPDigestAuth | None = None, verify: bool = True):
    handlers: list[BaseHandler] = []
    context = ssl.create_default_context() if verify else ssl._create_unverified_context()  # noqa: SLF001  # nosec B323
    handlers.append(HTTPSHandler(context=context))
    if auth is not None:
        password_mgr = HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, uri=(), user=auth.username, passwd=auth.password)
        handlers.append(HTTPDigestAuthHandler(password_mgr))
    return build_opener(*handlers)


def _build_url(url: str, params: dict | None = None) -> str:
    if not params:
        return url
    query = urlencode({key: value for key, value in params.items() if value is not None})
    separator = '&' if '?' in url else '?'
    return f'{url}{separator}{query}'


def get(url: str, *, headers: dict | None = None, params: dict | None = None, timeout: int = 15, auth: HTTPDigestAuth | None = None, verify: bool = True):
    request = Request(_build_url(url, params), headers=headers or {}, method='GET')
    opener = _build_opener(auth=auth, verify=verify)
    try:
        with opener.open(request, timeout=timeout) as response:
            return Response(status_code=response.getcode(), headers=response.headers, body=response.read())
    except HTTPError as exc:
        return Response(status_code=exc.code, headers=exc.headers, body=exc.read())
    except URLError as exc:
        raise RequestError(str(exc)) from exc


def post(url: str, *, headers: dict | None = None, data: dict | None = None, json_body: dict | None = None, timeout: int = 15, verify: bool = True):
    request_headers = dict(headers or {})
    payload = None
    if json_body is not None:
        request_headers.setdefault('Content-Type', 'application/json')
        payload = json.dumps(json_body).encode('utf-8')
    elif data is not None:
        request_headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
        payload = urlencode(data).encode('utf-8')
    request = Request(url, data=payload, headers=request_headers, method='POST')
    opener = _build_opener(verify=verify)
    try:
        with opener.open(request, timeout=timeout) as response:
            return Response(status_code=response.getcode(), headers=response.headers, body=response.read())
    except HTTPError as exc:
        return Response(status_code=exc.code, headers=exc.headers, body=exc.read())
    except URLError as exc:
        raise RequestError(str(exc)) from exc
