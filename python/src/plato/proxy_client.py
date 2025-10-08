import asyncio
import os
import subprocess
from typing import Optional
from urllib.parse import urlparse

# extra imports for tunneling
import base64
import ssl
import socket
import contextlib


class ProxyTunnel:
    """Manages an in-process HTTP CONNECT tunnel for database connections."""

    def __init__(self, job_group_id: str, host_port: int):
        self.job_group_id = job_group_id
        self.host_port = host_port

        # Keep the same attribute so your code doesn't break,
        # but we'll store the asyncio server here instead.
        self.process: Optional[subprocess.Popen] = None  # pyright: ignore[reportMissingTypeArgument]

        # Internals for the async server/tunnel
        self._server: Optional[asyncio.AbstractServer] = None
        self._client_tasks: set[asyncio.Task] = set()

    # ---------- helpers ----------

    @staticmethod
    def _set_keepalive(sock: socket.socket, idle_sec: int = 30) -> None:
        """macOS/BSD-friendly TCP keepalive: enable + set idle seconds."""
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        except OSError:
            return
        try:
            TCP_KEEPALIVE = getattr(socket, "TCP_KEEPALIVE", 0x10)  # macOS name
            sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, idle_sec)
        except OSError:
            pass  # best effort

    async def _open_http_connect(
        self,
        proxy_host: str,
        proxy_port: int,
        dest_host: str,
        dest_port: int,
        proxy_user: Optional[str],
        proxy_pass: Optional[str],
        use_tls_to_proxy: bool,
        timeout: float = 20.0,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open a tunneled connection to dest via proxy using HTTP CONNECT."""
        ssl_ctx = None
        if use_tls_to_proxy:
            ssl_ctx = ssl.create_default_context()

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                proxy_host,
                proxy_port,
                ssl=ssl_ctx,
                server_hostname=proxy_host if ssl_ctx else None,
            ),
            timeout=timeout,
        )

        # enable TCP keepalive on underlying socket
        sock = writer.get_extra_info("socket")
        if isinstance(sock, socket.socket):
            self._set_keepalive(sock, idle_sec=30)

        # Build CONNECT request (Basic auth if provided)
        auth = ""
        if proxy_user and proxy_pass:
            token = base64.b64encode(f"{proxy_user}:{proxy_pass}".encode()).decode()
            auth = f"Proxy-Authorization: Basic {token}\r\n"

        req = (
            f"CONNECT {dest_host}:{dest_port} HTTP/1.1\r\n"
            f"Host: {dest_host}:{dest_port}\r\n"
            f"{auth}"
            f"Proxy-Connection: keep-alive\r\n"
            f"Connection: keep-alive\r\n"
            f"\r\n"
        ).encode("ascii")
        writer.write(req)
        await writer.drain()

        # Read response headers
        header = b""
        while b"\r\n\r\n" not in header:
            chunk = await reader.read(4096)
            if not chunk:
                raise RuntimeError("Proxy closed before responding to CONNECT")
            header += chunk

        # Simple status check
        first_line = header.split(b"\r\n", 1)[0]
        parts = first_line.split()
        if len(parts) < 2 or parts[1] != b"200":
            # surface the first line for debugging
            raise RuntimeError(f"CONNECT failed: {first_line.decode(errors='ignore')}")

        return reader, writer

    async def _pipe(self, src: asyncio.StreamReader, dst: asyncio.StreamWriter):
        try:
            while True:
                data = await src.read(65536)
                if not data:
                    break
                dst.write(data)
                await dst.drain()
        finally:
            with contextlib.suppress(Exception):
                dst.close()
                await dst.wait_closed()

    async def _handle_client(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        *,
        proxy_host: str,
        proxy_port: int,
        proxy_user: str,
        proxy_pass: str,
        use_tls_to_proxy: bool,
        dest_host: str,
        dest_port: int,
    ):
        peer = client_writer.get_extra_info("peername")
        try:
            # Establish CONNECT tunnel via proxy to the destination
            server_reader, server_writer = await self._open_http_connect(
                proxy_host=proxy_host,
                proxy_port=proxy_port,
                dest_host=dest_host,
                dest_port=dest_port,
                proxy_user=proxy_user,
                proxy_pass=proxy_pass,
                use_tls_to_proxy=use_tls_to_proxy,
            )

            # Bi-directional piping
            await asyncio.gather(
                self._pipe(client_reader, server_writer),
                self._pipe(server_reader, client_writer),
            )
        except Exception as e:
            print(f"Tunnel handler error for {peer}: {e}")
            with contextlib.suppress(Exception):
                client_writer.close()
                await client_writer.wait_closed()

    # ---------- public API ----------

    async def start(self):
        """Start the proxy tunnel server (replaces the proxytunnel subprocess)."""
        base_url = os.getenv("PLATO_BASE_URL", "https://plato.so/api")
        parsed_url = urlparse(base_url)
        hostname = parsed_url.hostname or "plato.so"

        # Determine proxy URL host:port (your original logic)
        if hostname == "localhost" or hostname.startswith("127.0.0.1"):
            proxy_url = "localhost:9000"
        elif hostname == "plato.so":
            proxy_url = "proxy.plato.so:9000"
        else:
            parts = hostname.split(".", 1)
            if len(parts) == 2:
                subdomain, domain = parts
                proxy_url = f"{subdomain}.proxy.{domain}:9000"
            else:
                proxy_url = f"proxy.{hostname}:9000"

        # Parse proxy host/port
        if "://" in proxy_url:
            # tolerate schemes if someone sets them
            pu = urlparse(proxy_url)
            proxy_host = pu.hostname or "localhost"
            proxy_port = pu.port or 9000
        else:
            host, _, port = proxy_url.partition(":")
            proxy_host = host or "localhost"
            proxy_port = int(port or "9000")

        # -E equivalent: TLS to proxy unless explicitly disabled
        use_tls_to_proxy = os.getenv("PROXY_TLS", "1").lower() not in (
            "0",
            "false",
            "no",
        )

        proxy_user = f"{self.job_group_id}@22"
        proxy_pass = "password"

        print(f"Using proxy URL: {proxy_url} (from base URL: {base_url})")

        # Start local listener that mimics: -d 127.0.0.1:<db_port> -a <host_port>
        # i.e., we listen on host_port and forward through proxy to 127.0.0.1:db_port
        def handler(r, w):
            return self._handle_client(
                r,
                w,
                proxy_host=proxy_host,
                proxy_port=proxy_port,
                proxy_user=proxy_user,
                proxy_pass=proxy_pass,
                use_tls_to_proxy=use_tls_to_proxy,
                dest_host="127.0.0.1",
                dest_port=22,
            )

        # Bind on localhost for safety, same as proxytunnel's typical usage
        self._server = await asyncio.start_server(
            handler, host="127.0.0.1", port=self.host_port
        )
        addrs = ", ".join(str(s.getsockname()) for s in (self._server.sockets or []))

        # Mirror your previous logs
        print(
            f"Starting proxy tunnel listener on {addrs} -> 127.0.0.1:22 via {proxy_url} with user {proxy_user} and pass {proxy_pass} and ID {self.job_group_id}"
        )

        # Small delay to mirror your readiness wait and allow binding to settle
        await asyncio.sleep(0.2)

        # Sanity check: ensure server is active (no "poll" in async variant; just check sockets)
        if not self._server.sockets:
            raise RuntimeError("Proxy tunnel failed to start: no listening sockets")

        print(f"✅ Proxy tunnel established on port {self.host_port}")

    def stop(self):
        """Stop the proxy tunnel server."""
        # Keep old logging semantics
        if self._server is not None:
            print("Stopping proxy tunnel")

            # Stop accepting new connections
            self._server.close()
            try:
                # Best-effort sync close; in non-async context we can't await
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # schedule wait_closed
                    loop.create_task(self._server.wait_closed())
                else:
                    loop.run_until_complete(self._server.wait_closed())
            except RuntimeError:
                # no running loop; ignore
                pass

            self._server = None

            # Cancel any active client piping tasks
            for t in list(self._client_tasks):
                t.cancel()
            self._client_tasks.clear()

            print("✅ Proxy tunnel stopped")
