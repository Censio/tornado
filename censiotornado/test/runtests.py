#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, with_statement
import gc
import locale  # system locale module, not tornado.locale
import logging
import operator
import textwrap
import sys
from censiotornado.httpclient import AsyncHTTPClient
from censiotornado.httpserver import HTTPServer
from censiotornado.ioloop import IOLoop
from censiotornado.netutil import Resolver
from censiotornado.options import define, options, add_parse_callback
from censiotornado.test.util import unittest

try:
    reduce  # py2
except NameError:
    from functools import reduce  # py3

TEST_MODULES = [
    'censiotornado.httputil.doctests',
    'censiotornado.iostream.doctests',
    'censiotornado.util.doctests',
    'censiotornado.test.asyncio_test',
    'censiotornado.test.auth_test',
    'censiotornado.test.concurrent_test',
    'censiotornado.test.curl_httpclient_test',
    'censiotornado.test.escape_test',
    'censiotornado.test.gen_test',
    'censiotornado.test.http1connection_test',
    'censiotornado.test.httpclient_test',
    'censiotornado.test.httpserver_test',
    'censiotornado.test.httputil_test',
    'censiotornado.test.import_test',
    'censiotornado.test.ioloop_test',
    'censiotornado.test.iostream_test',
    'censiotornado.test.locale_test',
    'censiotornado.test.locks_test',
    'censiotornado.test.netutil_test',
    'censiotornado.test.log_test',
    'censiotornado.test.options_test',
    'censiotornado.test.process_test',
    'censiotornado.test.queues_test',
    'censiotornado.test.simple_httpclient_test',
    'censiotornado.test.stack_context_test',
    'censiotornado.test.tcpclient_test',
    'censiotornado.test.tcpserver_test',
    'censiotornado.test.template_test',
    'censiotornado.test.testing_test',
    'censiotornado.test.twisted_test',
    'censiotornado.test.util_test',
    'censiotornado.test.web_test',
    'censiotornado.test.websocket_test',
    'censiotornado.test.windows_test',
    'censiotornado.test.wsgi_test',
]


def all():
    return unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES)


class TornadoTextTestRunner(unittest.TextTestRunner):
    def run(self, test):
        result = super(TornadoTextTestRunner, self).run(test)
        if result.skipped:
            skip_reasons = set(reason for (test, reason) in result.skipped)
            self.stream.write(textwrap.fill(
                "Some tests were skipped because: %s" %
                ", ".join(sorted(skip_reasons))))
            self.stream.write("\n")
        return result


class LogCounter(logging.Filter):
    """Counts the number of WARNING or higher log records."""
    def __init__(self, *args, **kwargs):
        # Can't use super() because logging.Filter is an old-style class in py26
        logging.Filter.__init__(self, *args, **kwargs)
        self.warning_count = self.error_count = 0

    def filter(self, record):
        if record.levelno >= logging.ERROR:
            self.error_count += 1
        elif record.levelno >= logging.WARNING:
            self.warning_count += 1
        return True


def main():
    # The -W command-line option does not work in a virtualenv with
    # python 3 (as of virtualenv 1.7), so configure warnings
    # programmatically instead.
    import warnings
    # Be strict about most warnings.  This also turns on warnings that are
    # ignored by default, including DeprecationWarnings and
    # python 3.2's ResourceWarnings.
    warnings.filterwarnings("error")
    # setuptools sometimes gives ImportWarnings about things that are on
    # sys.path even if they're not being used.
    warnings.filterwarnings("ignore", category=ImportWarning)
    # Tornado generally shouldn't use anything deprecated, but some of
    # our dependencies do (last match wins).
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("error", category=DeprecationWarning,
                            module=r"tornado\..*")
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
    warnings.filterwarnings("error", category=PendingDeprecationWarning,
                            module=r"tornado\..*")
    # The unittest module is aggressive about deprecating redundant methods,
    # leaving some without non-deprecated spellings that work on both
    # 2.7 and 3.2
    warnings.filterwarnings("ignore", category=DeprecationWarning,
                            message="Please use assert.* instead")
    # unittest2 0.6 on py26 reports these as PendingDeprecationWarnings
    # instead of DeprecationWarnings.
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning,
                            message="Please use assert.* instead")
    # Twisted 15.0.0 triggers some warnings on py3 with -bb.
    warnings.filterwarnings("ignore", category=BytesWarning,
                            module=r"twisted\..*")
    # The __aiter__ protocol changed in python 3.5.2.
    # Silence the warning until we can drop 3.5.[01].
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning,
                            message=".*legacy __aiter__ protocol")

    logging.getLogger("tornado.access").setLevel(logging.CRITICAL)

    define('httpclient', type=str, default=None,
           callback=lambda s: AsyncHTTPClient.configure(
               s, defaults=dict(allow_ipv6=False)))
    define('httpserver', type=str, default=None,
           callback=HTTPServer.configure)
    define('ioloop', type=str, default=None)
    define('ioloop_time_monotonic', default=False)
    define('resolver', type=str, default=None,
           callback=Resolver.configure)
    define('debug_gc', type=str, multiple=True,
           help="A comma-separated list of gc module debug constants, "
           "e.g. DEBUG_STATS or DEBUG_COLLECTABLE,DEBUG_OBJECTS",
           callback=lambda values: gc.set_debug(
               reduce(operator.or_, (getattr(gc, v) for v in values))))
    define('locale', type=str, default=None,
           callback=lambda x: locale.setlocale(locale.LC_ALL, x))

    def configure_ioloop():
        kwargs = {}
        if options.ioloop_time_monotonic:
            from censiotornado.platform.auto import monotonic_time
            if monotonic_time is None:
                raise RuntimeError("monotonic clock not found")
            kwargs['time_func'] = monotonic_time
        if options.ioloop or kwargs:
            IOLoop.configure(options.ioloop, **kwargs)
    add_parse_callback(configure_ioloop)

    log_counter = LogCounter()
    add_parse_callback(
        lambda: logging.getLogger().handlers[0].addFilter(log_counter))

    import censiotornado.testing
    kwargs = {}
    if sys.version_info >= (3, 2):
        # HACK:  unittest.main will make its own changes to the warning
        # configuration, which may conflict with the settings above
        # or command-line flags like -bb.  Passing warnings=False
        # suppresses this behavior, although this looks like an implementation
        # detail.  http://bugs.python.org/issue15626
        kwargs['warnings'] = False
    kwargs['testRunner'] = TornadoTextTestRunner
    try:
        censiotornado.testing.main(**kwargs)
    finally:
        # The tests should run clean; consider it a failure if they logged
        # any warnings or errors. We'd like to ban info logs too, but
        # we can't count them cleanly due to interactions with LogTrapTestCase.
        if log_counter.warning_count > 0 or log_counter.error_count > 0:
            logging.error("logged %d warnings and %d errors",
                          log_counter.warning_count, log_counter.error_count)
            sys.exit(1)

if __name__ == '__main__':
    main()
