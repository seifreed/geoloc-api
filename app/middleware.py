"""Middleware ASGI: límite de tamaño del body (anti-DoS por memoria).

Cuenta los bytes a medida que llegan, así cubre tanto Content-Length como
Transfer-Encoding: chunked. Bufferiza como mucho `max_bytes` y luego reenvía
el body a la app; si se excede, responde 413 sin pasar la petición.
"""
import json

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_BODY_BYTES = 1_048_576  # 1 MB


class SecurityHeadersMiddleware:
    """Añade cabeceras de seguridad a cada respuesta (defensa en profundidad)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(raw=message["headers"])
                headers["x-content-type-options"] = "nosniff"
            await send(message)

        await self.app(scope, receive, send_with_headers)


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # atajo: si Content-Length ya supera el límite, rechaza sin leer el body
        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                await self._reject(send, 400, "invalid Content-Length")
                return
            if declared > self.max_bytes:
                await self._reject(send)
                return

        # lee y cuenta los bytes reales (cubre chunked sin Content-Length)
        body = b""
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] != "http.request":
                break
            body += message.get("body", b"")
            more_body = message.get("more_body", False)
            if len(body) > self.max_bytes:
                await self._reject(send)
                return

        await self.app(scope, self._replay(body), send)

    @staticmethod
    def _replay(body: bytes) -> Receive:
        done = False

        async def receive() -> Message:
            nonlocal done
            if done:
                return {"type": "http.disconnect"}
            done = True
            return {"type": "http.request", "body": body, "more_body": False}

        return receive

    @staticmethod
    async def _reject(
        send: Send, status: int = 413, detail: str = "request body too large"
    ) -> None:
        payload = json.dumps({"detail": detail}).encode()
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": payload})
