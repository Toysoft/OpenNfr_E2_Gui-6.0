# -*- coding: utf-8 -*-
import base64
from Crypto.Cipher import AES
import hashlib

def derive_key_and_iv(password, salt, key_length, iv_length):
    d = d_i = ''
    while len(d) < key_length + iv_length:
        d_i = hashlib.md5(d_i + password + salt).digest()
        d += d_i
    return d[:key_length], d[key_length:key_length+iv_length]

class AESCipher:
    def __init__(self):
        pass

    def decrypt(self, data, password, key_length=32):
        data = base64.b64decode(data)
        bs = AES.block_size
        salt = data[len("Salted__"): 16]
        data = data[len("Salted__")+len(salt): ]

        key, iv = derive_key_and_iv(password, salt, key_length, bs)
        cipher = AES.new(key, AES.MODE_CBC, iv)

        chunk = cipher.decrypt( data )
        padding_length = ord(chunk[-1])

        return chunk[:-padding_length]

OpenSSL_AES = AESCipher()

def decrypt(data, key="foobar"):
    return OpenSSL_AES.decrypt(data, key)