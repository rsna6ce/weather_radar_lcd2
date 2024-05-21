#!/usr/bin/env python3
import os
import sys
import time
import datetime
import threading
import board
from busio import I2C
from adafruit_ssd1306 import SSD1306_I2C
from PIL import Image, ImageDraw, ImageFont


class DatetimeLcdThread(threading.Thread):
    def __init__(self):
        super(DatetimeLcdThread, self).__init__()
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self):
        weekday_list = ['mon','tue','wed','thu','fri','sat','sun']
        i2c = I2C(scl=board.SCL, sda=board.SDA)
        lcd = SSD1306_I2C(128, 32, i2c, addr=0x3C)
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
                image = Image.new("1", (lcd.width, lcd.height))
                draw = ImageDraw.Draw(image)
                draw.text((4, 1),date_str, font=font, fill=255)
                draw.text((4, 17),time_str + '  ' + weekday_str, font=font, fill=255)
                image.paste(weekday_img, (106, 1))
                lcd.image(image)
                lcd.show()
            time.sleep(0.1)
            if self.stop_event.is_set():
                break



def main():
    pass
    datetime_th = DatetimeLcdThread()
    datetime_th.daemon = True
    datetime_th.start()
    datetime_th.join()

if __name__ == '__main__':
    sys.exit(main())