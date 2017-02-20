#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import sys

sys.path.append("..")

import unittest
import handlers


class TestHandlers(unittest.TestCase):
    def test_create_app_key(self):
        app_key = handlers.create_app_key()
        print(app_key)
        self.assertNotEqual(app_key, None)
