#!/bin/env python3

class Message(object):
    def __init__(self, headers, body, base64 = False):
        self.headers = headers
        self.body = body
        self.base64: bool = base64
