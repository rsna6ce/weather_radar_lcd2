#!/usr/bin/env python3
import os
import sys
import time
import datetime
import threading
import board
from digitalio import DigitalInOut, Direction
from board import D20, D21
from collections import deque

class UltrasoundEchoThread(threading.Thread):
    def __init__(self):
        super(UltrasoundEchoThread, self).__init__()
        self.stop_event = threading.Event()
        self.distance_max = 10.0
        self.latest_distance = self.distance_max
        self.queue = deque([self.distance_max])
        self.queue_max = 5
        self.loop_count=0
        self.timeout=0.1

    def stop(self):
        self.stop_event.set()

    def run(self):
        trig_pin = DigitalInOut(D20)
        echo_pin = DigitalInOut(D21)
        trig_pin.direction = Direction.OUTPUT
        echo_pin.direction = Direction.INPUT
        speed_of_sound = 343.70 #20deg-c
        while True:
            try:
                trig_pin.value = True
                time.sleep(0.000010)
                trig_pin.value = False

                to1 = time.time()
                while not echo_pin.value:
                    self.loop_count += 1
                    to2 = time.time()
                    if to2-to1 > self.timeout:
                        raise
                t1 = time.time() # pulse up time

                while echo_pin.value:
                    self.loop_count += 1
                    pass
                t2 = time.time() # pulse down time

                self.latest_distance = (t2 - t1) * speed_of_sound / 2.0
                self.queue.append(self.latest_distance)
                if len(self.queue) > self.queue_max:
                    self.queue.popleft()

                time.sleep(0.2)
                if self.stop_event.is_set():
                    break
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(e)
                echo_pin.direction = Direction.OUTPUT
                time.sleep(0.2)
                trig_pin.value = True
                time.sleep(0.2)
                trig_pin.value = False
                time.sleep(0.2)
                echo_pin.direction = Direction.INPUT

    def get_latest_distance(self):
        return self.latest_distance

    def get_latest_distance_min(self):
        value = min(self.queue)
        return value, self.loop_count

def main():
    pass
    us_echo_th = UltrasoundEchoThread()
    us_echo_th.daemon = True
    us_echo_th.start()
    while True:
        print(us_echo_th.get_latest_distance_min(),  us_echo_th.get_latest_distance())
        time.sleep(0.5)
    us_echo_th.join()

if __name__ == '__main__':
    sys.exit(main())
