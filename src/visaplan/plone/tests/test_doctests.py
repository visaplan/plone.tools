# -*- coding: utf-8 -*- äöü vim: ts=8 sts=4 sw=4 si et tw=72 cc=+8
import doctest
import mymodule1, mymodule2

def load_tests(loader, tests, ignore):
    # https://docs.python.org/2/library/unittest.html#load-tests-protocol
    for mod in (
            mymodule1, mymodule2,
            ):
        tests.addTests(doctest.DocTestSuite(mod))
    return tests
