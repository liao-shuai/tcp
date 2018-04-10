# -*- coding: utf-8 -*-
"""
指令解析处理模块
解析指令参数
将指令参数打包成数据
"""
import binascii
import socket
import struct
import random

try:
    import ujson as json
except ImportError:
    import json

__all__ = ['JsonPacket']


class BasePacket(object):
    
    HEADLEN = 4
    _received = False

    def __init__(self, data=''):
        self.cache_data = data

    @classmethod
    def get_identity(cls):
        return random.randint(0, 9999999)

    @classmethod
    def pack(cls, data):
        """
            将json数据序列化成指令数据
        """
        raise NotImplementedError

    def decode(self):
        """
            流式解码函数，将外部数据发送至生成器
            直到数据解码成功

            decode = self.decode()
            try:
                decode.send(None)
                while not self.received():
                    decode.send(somedata)
            except StopIteration:
                pass
        """
        raise NotImplementedError

    def received(self):
        return self._received

    def receive_from_socket(self, sock):
        decode = self.decode()
        try:
            decode.send(None)
            while not self.received():
                data = sock.recv(4096)
                if data:
                    decode.send(data)
                else:
                    raise socket.error
        except StopIteration as e:
            if len(e.args):
                raise


class JsonPacket(BasePacket):
    @classmethod
    def pack(cls, data):
        # 不需要确认的指令可以不需要 ident 字段
        if not data.get('ident'):
            data['ident'] = cls.get_identity()
        pack_data = json.dumps(data, ensure_ascii=False)
        temp = struct.pack('>HH', data['type'], len(pack_data)) + pack_data.encode("utf-8")
        return temp

    def decode(self):
        self._received = False
        if self.cache_data:
            data = self.cache_data
        else:
            data = ''
        while len(data) < self.HEADLEN:
            complement = yield
            if not complement:
                raise StopIteration('not data can parse')
            data += complement
        # self.type = struct.unpack('>H', data[0:2])[0]
        self.length = struct.unpack('>H', data[2:4])[0]
        TOTALLEN = self.HEADLEN + self.length
        while len(data) < TOTALLEN:
            complement = yield
            if not complement:
                raise StopIteration('not data can parse')
            data += complement
        self.data = json.loads((data[self.HEADLEN:TOTALLEN]).decode('utf-8'))
        self.cache_data = data[TOTALLEN:]
        self._received = True

    def __repr__(self):
        data = getattr(self, 'data', '')
        if data:
            data = json.dumps(data, sort_keys=True)
            string = '<Packet(%s) %s 0x%s>' % (data, 'receive' if self._received else 'suspend', id(self))
        else:
            string = ''
        if self.cache_data:
            string2 = '<Packet(%s) %s 0x%s>' % (self.cache_data, 'cached' if self._received else 'suspend', id(self))
            string = string + '\n' + string2 if string else string2
        return string
