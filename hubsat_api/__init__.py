"""Cliente HubSat: timeout obrigatório, sem retry automático de escritas."""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping
from dataclasses import dataclass
from .operations import OPERATIONS, PYTHON_NAMES


class HubSatApiError(Exception):
    def __init__(self, status: int, payload: Any = None, retry_after: str | None = None):
        payload = payload if isinstance(payload, dict) else {}
        error = payload.get("error")
        error = error if isinstance(error, dict) else {}
        super().__init__(error.get("message") or payload.get("message") or f"HTTP {status}")
        self.status = status
        self.code = error.get("code") or payload.get("code") or "HTTP_ERROR"
        self.request_id = error.get("request_id") or payload.get("requestId")
        self.retry_after = retry_after


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class HubSatResponse:
    status: int
    headers: Mapping[str, str]
    data: Any


class HubSatClient:
    def __init__(self, token: str, base_url: str = "https://api.hubsat.com.br/api/integracao", timeout: float = 30):
        url = urllib.parse.urlsplit(base_url)
        local = url.hostname in ("localhost", "127.0.0.1", "::1")
        if (url.scheme != "https" and not (url.scheme == "http" and local)) or url.username or url.password or url.query or url.fragment:
            raise ValueError("base_url exige HTTPS sem credenciais, query ou fragmento; HTTP somente em loopback.")
        if not isinstance(token, str) or not re.fullmatch(r"hub_[a-f0-9]{48}", token):
            raise ValueError("Informe um token HubSat válido.")
        if not isinstance(timeout, (int, float)) or not 0 < timeout < float("inf"):
            raise ValueError("Timeout inválido.")
        self.__token = token
        self.__base_url = base_url.rstrip("/")
        self.__timeout = timeout
        # Não herdar proxies de ambiente: destinos/credenciais são explícitos.
        self.__opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())

    @property
    def base_url(self):
        return self.__base_url

    @property
    def timeout(self):
        return self.__timeout

    def call(self, operation_id: str, **kwargs) -> Any:
        return self.call_with_response(operation_id, **kwargs).data

    def call_with_response(self, operation_id: str, *, path: Mapping[str, Any] | None = None,
             query: Mapping[str, Any] | None = None, body: Any = None,
             idempotency_key: str | None = None, if_none_match: str | None = None) -> HubSatResponse:
        if operation_id not in OPERATIONS:
            raise ValueError("Operação desconhecida.")
        operation = OPERATIONS[operation_id]
        path = path or {}

        def segment(match):
            key = match.group(1)
            value = path.get(key)
            if value is None or str(value) in ("", ".", ".."):
                raise ValueError(f"Parâmetro obrigatório: {key}")
            return urllib.parse.quote(str(value), safe="")

        route = re.sub(r"\{([^}]+)\}", segment, operation["path"])
        values = {}
        for key, value in (query or {}).items():
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                value = ",".join(str(item) for item in value)
            elif isinstance(value, bool):
                value = str(value).lower()
            values[key] = value
        if values:
            route += "?" + urllib.parse.urlencode(values)
        headers = {"Authorization": "Bearer " + self.__token, "Accept": "application/json, application/octet-stream",
                   "User-Agent": "HubSatSDK-Python/1"}
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if if_none_match is not None:
            headers["If-None-Match"] = if_none_match
        request = urllib.request.Request(self.base_url + route, data=data, headers=headers, method=operation["method"])
        try:
            with self.__opener.open(request, timeout=self.timeout) as response:
                if response.status == 204:
                    return HubSatResponse(response.status, dict(response.headers), None)
                data = response.read()
                payload = json.loads(data) if "json" in response.headers.get("Content-Type", "") else data
                return HubSatResponse(response.status, dict(response.headers), payload)
        except urllib.error.HTTPError as error:
            with error:
                if error.code == 304:
                    return HubSatResponse(error.code, dict(error.headers), None)
                try:
                    payload = json.loads(error.read())
                except (ValueError, UnicodeError):
                    payload = {}
                raise HubSatApiError(error.code, payload, error.headers.get("Retry-After")) from None

    def __getattr__(self, name):
        operation = PYTHON_NAMES.get(name)
        if operation is None:
            raise AttributeError(name)
        return lambda **kwargs: self.call(operation, **kwargs)


__all__ = ["HubSatClient", "HubSatApiError", "HubSatResponse"]
