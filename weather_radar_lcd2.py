#!/usr/bin/env python3
import os
import sys
import time
import datetime
import threading
import copy
import glob
import socket
import requests

from busio import SPI
from board import SCK, MOSI, MISO, D8, D18, D23, D24, D2, D3, D14
from digitalio import DigitalInOut, Direction, Pull
from adafruit_rgb_display.rgb import color565
from adafruit_rgb_display.ili9488 import ILI9488
from PIL import Image, ImageDraw
import cv2

from bs4 import BeautifulSoup
from urllib import request
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome import service as fs
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

import weather_info_lcd
import datetime_lcd
import ultrasound_echo

#### user configurations ####
URL_HP = 'https://tenki.jp/radar/3/15/'
URL_IMG = 'https://imageflux.tenki.jp/large/static-images/radar/{0:04}/{1:02}/{2:02}/{3:02}/{4:02}/00/pref-15-large.jpg'
IMAGE_CACHE_LENGTH_MINUTE = 60  # from 60 to 120 minute
IMAGE_CACHE_INTERVAL_MINUTE = 5  # 10 or 5 minute
LED_OFF_MINUTE=30
####

CS_PIN    = DigitalInOut(D8)
LED_PIN   = DigitalInOut(D18)
RESET_PIN = DigitalInOut(D23)
DC_PIN    = DigitalInOut(D24)
LED_PIN.direction = Direction.OUTPUT

SWITCH_PIN = DigitalInOut(D3)
SWITCH_PIN.direction = Direction.INPUT
SWITCH_PIN_ON=True

UDP_SHUTDOWN_SH_PORT=50001

spi = SPI(clock=SCK, MOSI=MOSI, MISO=MISO)
display = ILI9488(
    spi,
    cs = CS_PIN,
    dc = DC_PIN,
    rst = RESET_PIN,
    width = 320,
    height = 480,
    rotation = 180,
    baudrate=50000000)

IN_PREPARATION_PNG = 'img/in_preparation.png'
ERROR_PNG = 'img/error.png'
SLEEP_PNG = 'img/sleep.png'
CHROMEDRIVER = "/usr/lib/chromium-browser/chromedriver"
CHROME_SERVICE = fs.Service(executable_path=CHROMEDRIVER)
POWEROFF_SEC=5
CLEANUP_MINUTE=10
DOWNLOAD_ERROR_RETRY_COUNT = 3
DOWNLOAD_HTTP_TIMEOUT_SEC = 300

status_download_error_count = 0
status_sleep = False

filenames = []
lock_filenames = threading.Lock()
lock_lcd = threading.Lock()

class DownloaderThread(threading.Thread):
    def __init__(self):
        super(DownloaderThread, self).__init__()
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self):
        delta_next = datetime.timedelta(seconds=90)
        dt_next = datetime.datetime.now() + delta_next
        while True:
            dt_now = datetime.datetime.now()
            if dt_next < dt_now:
                result = download_radar_images()
                dt_now = datetime.datetime.now()
                dt_next = dt_now + delta_next
            time.sleep(1)
            if self.stop_event.is_set():
                break

def logger_write(msg):
    dt_now = datetime.datetime.now()
    filename = 'log/{0:04}{1:02}{2:02}.log'.format(dt_now.year, dt_now.month, dt_now.day)
    timestamp = '{0:02}:{1:02}:{2:02}'.format(dt_now.hour, dt_now.minute, dt_now.second)
    with open(filename, mode='a') as f:
        writeline = '{} {}\n'.format(timestamp, msg)
        f.write(writeline)
        print(timestamp, msg)

def logger_cleanup(past_days=7):
    dt_now = datetime.datetime.now()
    white_list = []
    for i in range(past_days):
        dt_past = dt_now - datetime.timedelta(days=i)
        filename = 'log/{0:04}{1:02}{2:02}.log'.format(dt_past.year, dt_past.month, dt_past.day)
        white_list.append(filename)

    actual_filenames = sorted(glob.glob('log/*.log'))
    for filename in actual_filenames:
        if filename not in white_list:
            logger_write("Creanup delete " + filename)
            os.remove(filename)

def display_img(filename, error_mark=False):
    if not (os.path.isfile(filename)):
        filename = ERROR_PNG
    img = cv2.imread(filename, cv2.IMREAD_COLOR)
    img = cv2.resize(img, (320, 240),  interpolation = cv2.INTER_AREA)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    if error_mark:
        cv2.rectangle(img, (0, 0), (2, 2), (255, 255, 255), thickness=-1)
    frame = Image.fromarray(img)
    with lock_lcd:
        display.image(frame, x=0, y=240)

# get filenames snapshot
def get_filenames():
    lock_filenames.acquire()
    temp_filenames = copy.deepcopy(filenames)
    lock_filenames.release()
    return temp_filenames

# set filenames update
def set_filenames(arg_filenames):
    global filenames
    lock_filenames.acquire()
    filenames = copy.deepcopy(arg_filenames)
    lock_filenames.release()

def get_latest_filename():
    lock_filenames.acquire()
    latest_filename = ''
    if len(filenames):
        latest_filename = filenames[-1]
    lock_filenames.release()
    return latest_filename


def download_radar_images():
    global status_download_error_count
    global status_sleep

    result = True
    options = Options()
    options.add_argument('--headless')
    browser = webdriver.Chrome(service=CHROME_SERVICE, options=options)
    browser.set_page_load_timeout(DOWNLOAD_HTTP_TIMEOUT_SEC)
    try:
        start = time.perf_counter()
        logger_write("http get started ...")
        if False: #debug
            r = requests.get(URL_HP)
            html_page_source = r.text
        else:
            browser.get(URL_HP)
            html_page_source = str(browser.page_source)
        finished = time.perf_counter()
        elapsed = (finished - start)
        logger_write("http get finished ({}s)".format(int(elapsed)))
        soup = BeautifulSoup(html_page_source,  'html.parser')
        elem_radar_source = soup.find(id='radar-source')
        if elem_radar_source == None:
            logger_write("elem_radar_source is None !!!")
        elem_srcset = elem_radar_source['srcset']
        split_srcset = elem_srcset.split('/')
        elem_year   = int(split_srcset[6])
        elem_month  = int(split_srcset[7])
        elem_day    = int(split_srcset[8])
        elem_hour   = int(split_srcset[9])
        elem_minute = int(split_srcset[10])
        dt_latest = datetime.datetime(elem_year , elem_month , elem_day , elem_hour , elem_minute , 0)
        logger_write('dt_latest: {0:04}{1:02}{2:02}_{3:02}{4:02}'.format(
            dt_latest.year, dt_latest.month, dt_latest.day, dt_latest.hour, dt_latest.minute))

        temp_filenames = []
        for i in range(int(IMAGE_CACHE_LENGTH_MINUTE/IMAGE_CACHE_INTERVAL_MINUTE)):
            offset_min = i * 5
            dt_temp = dt_latest - datetime.timedelta(minutes=offset_min)
            filename = "tmp/{0:04}{1:02}{2:02}_{3:02}{4:02}00.png".format(
                dt_temp.year, dt_temp.month, dt_temp.day, dt_temp.hour, dt_temp.minute)
            temp_filenames.insert(0, filename)
            if not(os.path.isfile(filename)):
                url = URL_IMG.format(dt_temp.year, dt_temp.month, dt_temp.day, dt_temp.hour, dt_temp.minute)
                logger_write('downloading ' + url)
                browser.get(url)
                element = browser.find_element(By.TAG_NAME, "img")
                with open(filename, 'wb') as f:
                    f.write(element.screenshot_as_png)
        set_filenames(temp_filenames)
        status_download_error_count = 0
        logger_write("download_radar_images finished.")
    except Exception as e:
        logger_write("download_radar_images : exception detecred !!!")
        logger_write(str(e))
        result = False
        status_download_error_count += 1
        logger_write("status_download_error_count : {}".format(status_download_error_count))
        if (not status_sleep) and (status_download_error_count>DOWNLOAD_ERROR_RETRY_COUNT):
            display_img(ERROR_PNG)
    finally:
        browser.quit()
        return result

def display_radar_images(latest_only = False):
    temp_filenames = get_filenames()
    file_count = len(temp_filenames)
    if not latest_only:
        for i in range(file_count):
            filename = temp_filenames[i]
            if not(os.path.isfile(filename)):
                filename = ERROR_PNG
            img = cv2.imread(filename, cv2.IMREAD_COLOR)
            img = cv2.resize(img, (320, 240),  interpolation = cv2.INTER_AREA)
            bar_height = 5
            bar_width = 320
            cv2.rectangle(img, (0, 239-bar_height), (bar_width, 239), (0, 0, 0), thickness=-1)
            cv2.rectangle(img, (0, 239-bar_height), (int(bar_width*(i+1)/file_count), 239), (0, 0, 255), thickness=-1)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            frame = Image.fromarray(img)
            with lock_lcd:
                display.image(frame, x=0, y=240)
            time.sleep(0.2)
    if file_count > 0:
        display_img(temp_filenames[file_count-1], error_mark=(status_download_error_count>0))
    else:
        display_img(ERROR_PNG)

def cleanup_unused_images():
    temp_filenames = get_filenames()
    actual_filenames = sorted(glob.glob('tmp/*.png'))

    for filename in actual_filenames:
        if filename not in temp_filenames:
            logger_write("Creanup delete " + filename)
            os.remove(filename)

def weather_rader_lcd2():
    global status_sleep
    logger_write("weather_rader_lcd.py main stared. =========================================")
    display.fill(color565((255,255,255)))
    display_img(IN_PREPARATION_PNG)
    LED_PIN.value = True

    weather_info_th = weather_info_lcd.WeatherInfoThread(display, lock_lcd)
    weather_info_th.daemon = True
    weather_info_th.start()

    datetime_th = datetime_lcd.DatetimeLcdThread()
    datetime_th.daemon = True
    datetime_th.start()
    datetime_th.contrast(255)

    ultrasound_echo_threshold = 0.5
    ultrasound_echo_th = ultrasound_echo.UltrasoundEchoThread()
    ultrasound_echo_th.daemon = True
    ultrasound_echo_th.start()

    download_radar_images()
    display_radar_images(latest_only = True)

    download_th = DownloaderThread()
    download_th.daemon = True
    download_th.start()

    led_off_time = datetime.datetime.now() + datetime.timedelta(minutes=LED_OFF_MINUTE)
    cleanup_time = datetime.datetime.now() + datetime.timedelta(minutes=CLEANUP_MINUTE)
    poweroff_time = datetime.datetime.now() + datetime.timedelta(seconds=POWEROFF_SEC)
    latest_filename_prev = ''
    switch_value_prev = False
    while True:
        # 10sec touch switch to shutdown pc
        if SWITCH_PIN.value==SWITCH_PIN_ON:
            if poweroff_time < datetime.datetime.now():
                logger_write("shutdown ...")
                status_sleep=True
                display_img(SLEEP_PNG)
                udp_shutdown_sh_address = ('127.0.0.1', UDP_SHUTDOWN_SH_PORT)
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                send_len = sock.sendto('shutdown now'.encode('utf-8'), udp_shutdown_sh_address)
                datetime_th.stop()
                time.sleep(30)
                sys.exit(0)
        else:
            poweroff_time = datetime.datetime.now() + datetime.timedelta(seconds=POWEROFF_SEC)
        # 1shot touch switch to display radar
        latest_distance, loop_count= ultrasound_echo_th.get_latest_distance_min()
        usecho_detect = (latest_distance < ultrasound_echo_threshold)
        if usecho_detect:
            logger_write('latest_distance:{} loop_count:{}'.format(latest_distance, loop_count))
        if switch_value_prev != SWITCH_PIN.value or usecho_detect:
            switch_value_prev = SWITCH_PIN.value
            if SWITCH_PIN.value == SWITCH_PIN_ON or usecho_detect:
                LED_PIN.value = True
                datetime_th.contrast(255)
                display_radar_images()
                led_off_time = datetime.datetime.now() + datetime.timedelta(minutes=LED_OFF_MINUTE)
        # auto led off timer
        if led_off_time < datetime.datetime.now():
            LED_PIN.value = False
            datetime_th.contrast(0)
        # auto cleanup image timer
        if cleanup_time < datetime.datetime.now():
            cleanup_unused_images()
            logger_cleanup()
            cleanup_time = datetime.datetime.now() + datetime.timedelta(minutes=CLEANUP_MINUTE)
        latest_filename = get_latest_filename()
        # auto display latest image
        if latest_filename!='' and latest_filename_prev != latest_filename:
            latest_filename_prev = latest_filename
            display_radar_images(latest_only = True)
        time.sleep(0.1)


def main():
    weather_rader_lcd2()

if __name__ == '__main__':
    sys.exit(main())

