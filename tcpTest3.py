# -*- coding: utf-8 -*-
"""
模拟器类
"""
import threading
import socket
import datetime
import time

from collections import namedtuple

try:
    import Queue
except ImportError:
    import queue as Queue

from packet import JsonPacket as Packet

Cell = namedtuple('Cell', 'mcc mnc lacid cellid rxlev')


class Emulate(object):
    def __init__(self, host, port, imei='355372020827303', imsi='460001515535328',
                 iccid='89860113859009347034', version=1, heartbeat=160, vendor=20000, modules="L0P0"):
        self.address = (host, port)
        self.imei = imei
        self.vendor = vendor
        self.imsi = imsi
        self.heartbeat = heartbeat
        self.version = version
        self.vendor = vendor
        self.iccid = iccid
        self._sock = None
        self.modules = modules
        self._queue = Queue.Queue()
        self.loop_started = 0
        self._last_info = (None, None)
        self._status = False
        self.packet = Packet()
        self.connect()
        self.login()

    def connect(self):
        self._sock = socket.socket()
        self._sock.connect(self.address)
        self._status = True
        return self._sock

    def login(self):
        self.send({
            'type': 1,
            'imei': self.imei,
            'imsi': self.imsi,
            'version': self.version,
            'vendor': self.vendor,
            'iccid': self.iccid,
            'modules': self.modules
        })

    def send(self, data):
        if self.loop_started:
            self._queue.put(data)
        else:
            self._sock.send(self.packet.pack(data))

    def _send(self):
        while self._status:
            data = self._queue.get()
            if not data:
                self._status = False
                return None
            self._sock.send(self.packet.pack(data))

    def recv(self):
        self.packet.receive_from_socket(self._sock)
        print(self.packet)

        try:
            itype = self.packet.data['type']
            ident = self.packet.data.get('ident')
        except KeyError:
            return None

        self._last_info = (itype, ident)

        method = getattr(self, 'action_%s' % itype, None)
        if method:
            method()
        else:
            self.react()



    def heartbeat_loop(self):
        while 1:

            time.sleep((self.heartbeat / 2) + 1)
            if not self._status:
                break
            self.send({
                'type': 3,
            })

            # 这里顺便
            global n
            if n % 2 == 0:
                # 广东省广州市天河区科智路靠近科城大厦
                data = self.locate([
                    Cell(mcc=460, mnc=0, lacid=9475, cellid=44901, rxlev=32),
                    Cell(mcc=460, mnc=0, lacid=9475, cellid=17252, rxlev=23),
                ])
                # data = self.locate(gps=(113.4395958, 23.1659372))
                self.send(data)
            else:
                # 广东省广州市黄埔区揽月路靠近最牛的牛杂
                data = self.locate([
                    Cell(mcc=460, mnc=0, lacid=9475, cellid=61009, rxlev=51),
                    Cell(mcc=460, mnc=0, lacid=9475, cellid=21855, rxlev=33),
                    Cell(mcc=460, mnc=0, lacid=9475, cellid=18671, rxlev=26),
                    Cell(mcc=460, mnc=0, lacid=9475, cellid=26963, rxlev=23),
                    Cell(mcc=460, mnc=0, lacid=9475, cellid=50168, rxlev=19),
                    Cell(mcc=460, mnc=0, lacid=10331, cellid=58526, rxlev=13),
                ])
                # data = self.locate(gps=(113.4590952,23.1681934))
                self.send(data)

            n += 1

    def _loop(self):
        send_thread = threading.Thread(target=self._send)
        send_thread.daemon = True
        send_thread.start()
        self.loop_started = 1
        try:
            while 1:
                self.recv()
        except socket.error:
            print('%s socket terminate' % datetime.datetime.now())
        finally:
            self._status = False
            self._queue.put(None)
            # wait the send loop thread exit
            time.sleep(0.1)

    def loop(self, block=True):
        heartbeat_thread = threading.Thread(target=self.heartbeat_loop)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()
        if block:
            self._loop()
        else:
            recv_thread = threading.Thread(target=self._loop)
            recv_thread.daemon = True
            recv_thread.start()

    def locate(self, lbs=None, gps=None, timestamp=None):
        data = {
            'type': 7,
            'feedback': 1,
        }
        if lbs:
            data['cells'] = [{
                'mcc': i.mcc,
                'mnc': i.mnc,
                'lac': i.lacid,
                'ci': i.cellid,
                'rxlev': i.rxlev,
            } for i in lbs]
        if gps:
            data['gps'] = {
                'lon': gps[0],
                'lat': gps[1],
            }
        data['timestamp'] = time.time() if not timestamp else timestamp
        return data

    def react(self):
        itype, ident = self._last_info
        if itype % 2 == 0:
            data = {'type': itype}
            if ident:
                data['ident'] = ident
            self.send(data)

    # def action_7(self):
    #     self.react()
    #
    #     global n
    #     if n % 2 == 0:
    #         # 广东省广州市天河区科智路靠近科城大厦
    #         data = self.locate([
    #             Cell(mcc=460, mnc=0, lacid=9475, cellid=44901, rxlev=32),
    #             Cell(mcc=460, mnc=0, lacid=9475, cellid=17252, rxlev=23),
    #         ])
    #         # data = self.locate(gps=(113.4395958, 23.1659372))
    #         self.send(data)
    #     else:
    #         # 广东省广州市黄埔区揽月路靠近最牛的牛杂
    #         data = self.locate([
    #             Cell(mcc=460, mnc=0, lacid=9475, cellid=61009, rxlev=51),
    #             Cell(mcc=460, mnc=0, lacid=9475, cellid=21855, rxlev=33),
    #             Cell(mcc=460, mnc=0, lacid=9475, cellid=18671, rxlev=26),
    #             Cell(mcc=460, mnc=0, lacid=9475, cellid=26963, rxlev=23),
    #             Cell(mcc=460, mnc=0, lacid=9475, cellid=50168, rxlev=19),
    #             Cell(mcc=460, mnc=0, lacid=10331, cellid=58526, rxlev=13),
    #         ])
    #         # data = self.locate(gps=(113.4590952,23.1681934))
    #         self.send(data)
    #
    #     n += 1


n = 0
# imei = 1000
# imei = 1000+(680*2)*2
imei = 666666666666099

# if __name__ == '__main__':
def task():
    import argparse
    global imei
    imei += 1
    parser = argparse.ArgumentParser(
        description='emulate the device connect to server',
        conflict_handler='resolve',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    # parser.add_argument('-h', '--host', default='httptest.iot08.com', help='server host')
    parser.add_argument('-h', '--host', default='119.23.203.236', help='server host')
    parser.add_argument('-p', '--port', type=int, default=11500, help='server port')
    parser.add_argument('--imei', default='355372020827303', help='emulate imei')
    parser.add_argument('--imsi', default='460001515535328', help='emulate imsi')
    parser.add_argument('--iccid', default='89860113859009347034', help='emulate iccid')
    parser.add_argument('--version', default=1, help='emulate version')
    parser.add_argument('--vendor', default=20000, help='emulate vendor')

    args = parser.parse_args()

    emulate = Emulate(host=args.host, port=args.port, imei=str(imei), imsi=args.imsi, iccid=args.iccid,
                      version=args.version, vendor=args.vendor)

    data = emulate.locate([
       Cell(mcc=460, mnc=0, lacid=9475, cellid=44901, rxlev=32),
       Cell(mcc=460, mnc=0, lacid=9475, cellid=17252, rxlev=23),
    ])
    emulate.send(data)

    # data = emulate.locate(gps=(113.4395958, 23.1659372))
    # emulate.send(data)
    imei += 1

    emulate.loop()  # 保持心跳
    # emulate.loop()  # 循环上传 type 7 指令

threads = []

# times = 12000
times = 680
for i in range(0, times):
    t = threading.Thread(target=task)
    threads.append(t)
for i in range(0, times):
    threads[i].start()
for i in range(0, times):
    threads[i].join()

