# flake8: noqa
from __future__ import absolute_import, division, print_function, with_statement
from censiotornado.test.util import unittest


class ImportTest(unittest.TestCase):
    def test_import_everything(self):
        # Some of our modules are not otherwise tested.  Import them
        # all (unless they have external dependencies) here to at
        # least ensure that there are no syntax errors.
        import censiotornado.auth
        import censiotornado.autoreload
        import censiotornado.concurrent
        import censiotornado.escape
        import censiotornado.gen
        import censiotornado.http1connection
        import censiotornado.httpclient
        import censiotornado.httpserver
        import censiotornado.httputil
        import censiotornado.ioloop
        import censiotornado.iostream
        import censiotornado.locale
        import censiotornado.log
        import censiotornado.netutil
        import censiotornado.options
        import censiotornado.process
        import censiotornado.simple_httpclient
        import censiotornado.stack_context
        import censiotornado.tcpserver
        import censiotornado.tcpclient
        import censiotornado.template
        import censiotornado.testing
        import censiotornado.util
        import censiotornado.web
        import censiotornado.websocket
        import censiotornado.wsgi

    # for modules with dependencies, if those dependencies can be loaded,
    # load them too.

    def test_import_pycurl(self):
        try:
            import pycurl  # type: ignore
        except ImportError:
            pass
        else:
            import censiotornado.curl_httpclient
