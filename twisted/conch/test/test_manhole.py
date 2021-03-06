# -*- test-case-name: twisted.conch.test.test_manhole -*-
# Copyright (c) 2001-2004 Twisted Matrix Laboratories.
# See LICENSE for details.

from __future__ import generators

import time

from twisted.trial import unittest
from twisted.internet import error, defer
from twisted.conch.test.test_recvline import _TelnetMixin, _SSHMixin, _StdioMixin, stdio, ssh
from twisted.conch import manhole

class ManholeLoopbackMixin:
    serverProtocol = manhole.ColoredManhole

    def wfd(self, d):
        return defer.waitForDeferred(d)

    def testSimpleExpression(self):
        done = self.recvlineClient.expect("done")

        self._testwrite(
            "1 + 1\n"
            "done")

        def finished(ign):
            self._assertBuffer(
                [">>> 1 + 1",
                 "2",
                 ">>> done"])

        return done.addCallback(finished)

    def testTripleQuoteLineContinuation(self):
        done = self.recvlineClient.expect("done")

        self._testwrite(
            "'''\n'''\n"
            "done")

        def finished(ign):
            self._assertBuffer(
                [">>> '''",
                 "... '''",
                 "'\\n'",
                 ">>> done"])

        return done.addCallback(finished)

    def testFunctionDefinition(self):
        done = self.recvlineClient.expect("done")

        self._testwrite(
            "def foo(bar):\n"
            "\tprint bar\n\n"
            "foo(42)\n"
            "done")

        def finished(ign):
            self._assertBuffer(
                [">>> def foo(bar):",
                 "...     print bar",
                 "... ",
                 ">>> foo(42)",
                 "42",
                 ">>> done"])

        return done.addCallback(finished)

    def testClassDefinition(self):
        done = self.recvlineClient.expect("done")

        self._testwrite(
            "class Foo:\n"
            "\tdef bar(self):\n"
            "\t\tprint 'Hello, world!'\n\n"
            "Foo().bar()\n"
            "done")

        def finished(ign):
            self._assertBuffer(
                [">>> class Foo:",
                 "...     def bar(self):",
                 "...         print 'Hello, world!'",
                 "... ",
                 ">>> Foo().bar()",
                 "Hello, world!",
                 ">>> done"])

        return done.addCallback(finished)

    def testException(self):
        done = self.recvlineClient.expect("done")

        self._testwrite(
            "1 / 0\n"
            "done")

        def finished(ign):
            self._assertBuffer(
                [">>> 1 / 0",
                 "Traceback (most recent call last):",
                 '  File "<console>", line 1, in ?',
                 "ZeroDivisionError: integer division or modulo by zero",
                 ">>> done"])

        return done.addCallback(finished)

    def testControlC(self):
        done = self.recvlineClient.expect("done")

        self._testwrite(
            "cancelled line" + manhole.CTRL_C +
            "done")

        def finished(ign):
            self._assertBuffer(
                [">>> cancelled line",
                 "KeyboardInterrupt",
                 ">>> done"])

        return done.addCallback(finished)

    def testControlBackslash(self):
        self._testwrite("cancelled line")
        partialLine = self.recvlineClient.expect("cancelled line")

        def gotPartialLine(ign):
            self._assertBuffer(
                [">>> cancelled line"])
            self._testwrite(manhole.CTRL_BACKSLASH)

            d = self.recvlineClient.onDisconnection
            return self.assertFailure(d, error.ConnectionDone)

        def gotClearedLine(ign):
            self._assertBuffer(
                [""])

        return partialLine.addCallback(gotPartialLine).addCallback(gotClearedLine)

    def testControlD(self):
        self._testwrite("1 + 1")
        helloWorld = self.wfd(self.recvlineClient.expect(r"\+ 1"))
        yield helloWorld
        helloWorld.getResult()
        self._assertBuffer([">>> 1 + 1"])

        self._testwrite(manhole.CTRL_D + " + 1")
        cleared = self.wfd(self.recvlineClient.expect(r"\+ 1"))
        yield cleared
        cleared.getResult()
        self._assertBuffer([">>> 1 + 1 + 1"])

        self._testwrite("\n")
        printed = self.wfd(self.recvlineClient.expect("3\n>>> "))
        yield printed
        printed.getResult()

        self._testwrite(manhole.CTRL_D)
        d = self.recvlineClient.onDisconnection
        disconnected = self.wfd(self.assertFailure(d, error.ConnectionDone))
        yield disconnected
        disconnected.getResult()
    testControlD = defer.deferredGenerator(testControlD)

    def testDeferred(self):
        self._testwrite(
            "from twisted.internet import defer, reactor\n"
            "d = defer.Deferred()\n"
            "d\n")

        deferred = self.wfd(self.recvlineClient.expect("<Deferred #0>"))
        yield deferred
        deferred.getResult()

        self._testwrite(
            "c = reactor.callLater(0.1, d.callback, 'Hi!')\n")
        delayed = self.wfd(self.recvlineClient.expect(">>> "))
        yield delayed
        delayed.getResult()

        called = self.wfd(self.recvlineClient.expect("Deferred #0 called back: 'Hi!'\n>>> "))
        yield called
        called.getResult()
        self._assertBuffer(
            [">>> from twisted.internet import defer, reactor",
             ">>> d = defer.Deferred()",
             ">>> d",
             "<Deferred #0>",
             ">>> c = reactor.callLater(0.1, d.callback, 'Hi!')",
             "Deferred #0 called back: 'Hi!'",
             ">>> "])

    testDeferred = defer.deferredGenerator(testDeferred)

class ManholeLoopbackTelnet(_TelnetMixin, unittest.TestCase, ManholeLoopbackMixin):
    pass

class ManholeLoopbackSSH(_SSHMixin, unittest.TestCase, ManholeLoopbackMixin):
    if ssh is None:
        skip = "Crypto requirements missing, can't run manhole tests over ssh"

class ManholeLoopbackStdio(_StdioMixin, unittest.TestCase, ManholeLoopbackMixin):
    if stdio is None:
        skip = "Terminal requirements missing, can't run manhole tests over stdio"
    else:
        serverProtocol = stdio.ConsoleManhole
