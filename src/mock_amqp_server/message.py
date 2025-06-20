#!/bin/env python3

class Message(object):
    def __init__(self, headers, body: bytes, base64 = False):
        self.headers = headers
        self.body: bytes = body
        self.base64: bool = base64


    def get_headers(self):
        return self.headers


    def get_body(self):
        return self.body
