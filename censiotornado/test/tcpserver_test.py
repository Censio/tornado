from __future__ import absolute_import, division, print_function, with_statement
import socket

from censiotornado import gen
from censiotornado.iostream import IOStream
from censiotornado.log import app_log
from censiotornado.stack_context import NullContext
from censiotornado.tcpserver import TCPServer
from censiotornado.testing import AsyncTestCase, ExpectLog, bind_unused_port, gen_test


class TCPServerTest(AsyncTestCase):
    @gen_test
    def test_handle_stream_coroutine_logging(self):
        # handle_stream may be a coroutine and any exception in its
        # Future will be logged.
        class TestServer(TCPServer):
            @gen.coroutine
            def handle_stream(self, stream, address):
                yield gen.moment
                stream.close()
                1 / 0

        server = client = None
        try:
            sock, port = bind_unused_port()
            with NullContext():
                server = TestServer()
                server.add_socket(sock)
            client = IOStream(socket.socket())
            with ExpectLog(app_log, "Exception in callback"):
                yield client.connect(('localhost', port))
                yield client.read_until_close()
                yield gen.moment
        finally:
            if server is not None:
                server.stop()
            if client is not None:
                client.close()
