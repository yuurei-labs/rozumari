try:
    from collections.abc import Awaitable, Callable
except Exception:
    pass

import asyncio
import gc
import json
import time

from lib.config import Config
from lib.logger import Logger
from lib.singleton import Singleton


class Api(Singleton):
    def __init__(self) -> None:
        """Initialize the API client and load its configuration."""
        super().__init__()
        self._logger = Logger("API")

        config = Config().api
        self._base_url = config.get("url", "")
        self._api_key = config.get("token", "")

    async def request(
        self, method: str, path: str, *, data: dict | None = None
    ) -> dict:
        """Send an HTTP request and parse the JSON response.

        Args:
            method: HTTP request method.
            path: API endpoint path.
            data: Optional JSON request payload.

        Returns:
            Parsed JSON response, or an empty dictionary if the response is empty.

        Raises:
            OSError: If the connection fails or the server returns an HTTP error.
            ValueError: If the response contains invalid JSON.
        """
        gc.collect()
        body = json.dumps(data) if data is not None else None
        reader, writer = await self._open_stream(method, path, body=body)

        try:
            raw = await reader.read()
            res = json.loads(raw.decode("utf-8")) if raw else {}
            del raw
            return res
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            gc.collect()

    async def get(self, path: str, *, query: dict | None = None) -> dict:
        """Send an HTTP GET request.

        Args:
            path: API endpoint path.
            query: Optional query parameters.

        Returns:
            Parsed JSON response.

        Raises:
            OSError: If the connection fails or the server returns an HTTP error.
            ValueError: If the response contains invalid JSON.
        """
        if query:
            params = "&".join(f"{k}={v}" for k, v in query.items())
            path = f"{path}?{params}"
        return await self.request("GET", path)

    async def post(self, path: str, *, body: dict | None = None) -> dict:
        """Send an HTTP POST request.

        Args:
            path: API endpoint path.
            body: Optional JSON request payload.

        Returns:
            Parsed JSON response.

        Raises:
            OSError: If the connection fails or the server returns an HTTP error.
            ValueError: If the response contains invalid JSON.
        """
        return await self.request("POST", path, data=body)

    async def subcribe(
        self,
        path: str,
        on_data: "Callable[[str], Awaitable[None]]",
        *,
        reconnect_after: int = 0,
        retry_delay: int = 3,
        timeout: int = 30,
    ) -> None:
        """Subscribe to an SSE endpoint and process incoming events.

        Automatically reconnects when the connection is closed or an error occurs,
        using exponential backoff with a maximum delay of 30 seconds.

        Args:
            path: SSE endpoint path.
            on_data: Asynchronous callback invoked with each event payload.
            reconnect_after: Maximum connection lifetime in seconds. Set to 0
                to keep the connection alive indefinitely.
            retry_delay: Initial reconnection delay in seconds.
            timeout: Maximum time to wait for incoming data in seconds.

        Raises:
            asyncio.CancelledError: If the subscription task is cancelled.
        """
        headers = {
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }

        retry = retry_delay

        while True:
            gc.collect()
            writer, reader = None, None

            try:
                self._logger.info(f"Subscribing: {path}")
                reader, writer = await self._open_stream(
                    "GET", path, extra_headers=headers
                )

                started_at = time.ticks_ms()

                while True:
                    if reconnect_after > 0:
                        elapsed = time.ticks_diff(time.ticks_ms(), started_at)

                        if elapsed >= reconnect_after * 1000:
                            self._logger.info("SSE connection lifetime reached.")
                            break

                    line = await asyncio.wait_for(reader.readline(), timeout)

                    if not line:
                        break

                    decoded = line.decode("utf-8").strip()

                    if decoded.startswith("data:"):
                        payload = decoded[5:].strip()
                        await on_data(payload)
                        del payload

                    retry = retry_delay

            except asyncio.CancelledError:
                raise

            except Exception as e:
                self._logger.error(f"SSE disconnected: {e}")

            finally:
                if writer:
                    try:
                        writer.close()
                        await writer.wait_closed()
                    except Exception:
                        pass

                del reader
                del writer
                gc.collect()

            self._logger.info(f"Retrying SSE in {retry}s...")
            await asyncio.sleep(retry)
            retry = min(retry * 2, 30)

    def _parse_url(self, path: str) -> tuple[str, int, str, bool]:
        """Parse the configured base URL and endpoint path.

        Args:
            path: API endpoint path.

        Returns:
            A tuple containing the hostname, port, request path, and SSL flag.
        """
        url = f"{self._base_url}/{path.lstrip('/')}"
        proto, _, rest = url.partition("://")
        is_ssl = proto.lower() == "https"
        host_port, _, req_path = rest.partition("/")
        req_path = "/" + req_path

        if ":" in host_port:
            host, port_str = host_port.split(":", 1)
            port = int(port_str)
        else:
            host = host_port
            port = 443 if is_ssl else 80

        return host, port, req_path, is_ssl

    async def _open_stream(
        self,
        method: str,
        path: str,
        *,
        body: str | None = None,
        extra_headers: dict | None = None,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Establish an HTTP connection and send a request.

        Args:
            method: HTTP request method.
            path: API endpoint path.
            body: Optional serialized request body.
            extra_headers: Optional additional HTTP headers.

        Returns:
            A tuple containing the response reader and connection writer.
            The caller is responsible for closing the writer.

        Raises:
            OSError: If the connection fails or the server returns an HTTP error.
            ValueError: If the response status code is invalid.
        """
        host, port, req_path, is_ssl = self._parse_url(path)

        reader, writer = await asyncio.open_connection(
            host, port, ssl=is_ssl if is_ssl else None
        )

        headers = {
            "Host": host,
            "x-api-key": self._api_key,
            "Authorization": f"Bearer {self._api_key}",
            "Connection": "close",
        }

        if extra_headers:
            headers.update(extra_headers)

        if body is not None:
            body_bytes = body.encode("utf-8")
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(body_bytes))
        else:
            body_bytes = b""

        req_lines = [f"{method} {req_path} HTTP/1.1"]
        for k, v in headers.items():
            req_lines.append(f"{k}: {v}")
        req_header = "\r\n".join(req_lines) + "\r\n\r\n"

        writer.write(req_header.encode("utf-8"))
        if body_bytes:
            writer.write(body_bytes)
        await writer.drain()

        status_line = await reader.readline()
        if not status_line:
            writer.close()
            await writer.wait_closed()
            raise OSError("Empty HTTP response")

        parts = status_line.decode("utf-8").split(" ", 2)
        status_code = int(parts[1]) if len(parts) > 1 else 0

        while True:
            line = await reader.readline()
            if not line or line == b"\r\n":
                break

        if status_code >= 400:
            writer.close()
            await writer.wait_closed()
            raise OSError(f"HTTP Error {status_code}")

        return reader, writer
