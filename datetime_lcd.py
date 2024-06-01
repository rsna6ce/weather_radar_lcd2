#!/usr/bin/env python3
import os
import sys
import time
import datetime
import threading
import board
from board import D5, D6
from busio import I2C
from adafruit_ssd1306 import SSD1306_I2C
from PIL import Image, ImageDraw, ImageFont

from adafruit_extended_bus import ExtendedI2C
#pip3 install adafruit-extended-bus
# /boot/config.txt
#   dtoverlay=i2c-gpio,bus=11,i2c_gpio_sda=5,i2c_gpio_scl=6

class DatetimeLcdThread(threading.Thread):
    def __init__(self):
        super(DatetimeLcdThread, self).__init__()
        self.stop_event = threading.Event()
        i2c = ExtendedI2C(11, frequency=40000)
        self.lcd = SSD1306_I2C(128, 32, i2c, addr=0x3C)
        self.lcd.rotate(False)

    def stop(self):
        self.stop_event.set()

    def run(self):
        weekday_list = ['mon','tue','wed','thu','fri','sat','sun']
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf', 15)
        prev_second = -1
        while True:
            dt_now = datetime.datetime.now()
            curr_second = dt_now.second
            if prev_second != curr_second:
                prev_second = curr_second
                date_str = dt_now.strftime("%Y-%m-%d")
                time_str = dt_now.strftime("%H:%M:%S")
                weekday = dt_now.weekday() #monday:0 ... sunday:6
                weekday_str = weekday_list[weekday]
                weekday_img = Image.open("img/{}.png".format(weekday_str))
                image = Image.new("1", (self.lcd.width, self.lcd.height))
                draw = ImageDraw.Draw(image)
                draw.text((4, 1),date_str, font=font, fill=255)
                draw.text((4, 17),time_str + '  ' + weekday_str, font=font, fill=255)
                image.paste(weekday_img, (106, 1))
                self.lcd.image(image)
                self.lcd.show()
            time.sleep(0.1)
            if self.stop_event.is_set():
                self.lcd.fill(0)
                self.lcd.show()
                break

    def contrast(self, value):
        self.lcd.contrast(value)

def main():
    pass
    datetime_th = DatetimeLcdThread()
    datetime_th.daemon = True
    datetime_th.start()
    datetime_th.join()

if __name__ == '__main__':
    sys.exit(main())