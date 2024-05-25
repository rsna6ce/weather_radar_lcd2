#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import cv2
import time
import numpy as np
import requests
import threading
import datetime
from bs4 import BeautifulSoup
from PIL import ImageFont, ImageDraw, Image
from weather_radar_lcd2 import logger_write

target_url='https://weathernews.jp/onebox/tenki/chiba/12204/'
weather_info_count = 12

def putText_japanese(img, text, point, size, color, anchor):
    font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', size)  #TODO: sudo apt install fonts-noto-cjk
    img_pil = Image.fromarray(img)
    draw = ImageDraw.Draw(img_pil)
    x, y, x2, y2 = draw.textbbox(point, text, font, anchor=anchor)
    draw.text((x,y), text, fill=color, font=font)
    return np.array(img_pil)

class WeatherInfoThread(threading.Thread):
    def __init__(self, display, lock_lcd):
        super(WeatherInfoThread, self).__init__()
        self.stop_event = threading.Event()
        self.display = display
        self.lock_lcd = lock_lcd
        self.cache = ''

    def stop(self):
        self.stop_event.set()

    def run(self):
        delta_next = datetime.timedelta(seconds=90)
        dt_next = datetime.datetime.now()
        while True:
            dt_now = datetime.datetime.now()
            if dt_next < dt_now:
                self.refresh_weather_info()
                dt_next = dt_now + delta_next
            time.sleep(1)
            if self.stop_event.is_set():
                break

    def refresh_weather_info(self):
        time_list=[]
        weather_list=[]
        rain_list=[]
        temp_list=[]
        wind_list=[]
        try:
            r = requests.get(target_url)
            bs = BeautifulSoup(r.text, 'html.parser')
            flick_list_1hours = bs.find_all('div', class_='wx1h_content')
            for flick_list_1hour in flick_list_1hours:

                # parse time
                times = flick_list_1hour.find_all(class_='time')
                for time in times:
                    if len(time_list) >= weather_info_count:
                        break
                    #<p>t</p>
                    time_text = time.find('p').text
                    time_list.append(time_text)

                # parse weather icon name
                weathers = flick_list_1hour.find_all(class_='weather')
                for weather in weathers:
                    if len(weather_list) >= weather_info_count:
                        break
                    #https://weathernews.jp/onebox/img/wxicon/300.png
                    img = weather.find('img')
                    img_src = img['src']
                    left = img_src.rfind('/') + len('/')
                    right = img_src.find('.png')
                    img_src_number = img_src[left:right]
                    weather_list.append(img_src_number)

                # parse rain
                rains = flick_list_1hour.find_all(class_='rain')
                for rain in rains:
                    if len(rain_list) >= weather_info_count:
                        break
                    #<p>r    \n<span>ミリ</span></p>
                    rain_text = rain.find('p').text
                    rain_text = rain_text.replace(' ','').replace('\n','').replace('ミリ','').replace('0.','.')
                    if len(rain_text) > 2:
                        rain_text = '99' #over 100mm rain -> 99mm
                    rain_list.append(rain_text)

                # parse temp
                temps = flick_list_1hour.find_all(class_='temp')
                for temp in temps:
                    if len(temp_list) >= weather_info_count:
                        break
                    #<p>t<span>℃</span></p>
                    temp_str = str(temp.find('p'))
                    left = temp_str.find('<p>') + len('<p>')
                    right = temp_str.find('<span>')
                    temp_text = temp_str[left:right]
                    temp_list.append(temp_text)

                # parse wind
                winds = flick_list_1hour.find_all(class_='wind')
                for wind in winds:
                    if len(wind_list) >= weather_info_count:
                        break
                    #<p>r    \n<span>m</span></p>
                    wind_text = wind.find('p').text
                    wind_text = wind_text.replace(' ','').replace('\n','').replace('m','')
                    wind_list.append(wind_text)

            temp_cache = (
                ''.join(time_list) +
                ''.join(weather_list) +
                ''.join(rain_list) +
                ''.join(temp_list) +
                ''.join(wind_list) )
        except Exception as e:
            logger_write("weather_info : exception detecred !!!")
            logger_write(str(e))
            time_list = ['??'] * weather_info_count
            weather_list = ['??'] * weather_info_count
            rain_list = ['??'] * weather_info_count
            temp_list = ['??'] * weather_info_count
            wind_list = ['??'] * weather_info_count
            dt_now = datetime.datetime.now()
            temp_cache = '???_' + dt_now.strftime('%Y/%m/%d_%H:%M:%S')

        #print(time_list)
        #print(weather_list)
        #print(rain_list)
        #print(temp_list)
        #print(wind_list)

        if temp_cache == self.cache:
            #logger_write('INFO: cache matched. refresh_weather_info display image skipped.')
            return
        else:
            self.cache = temp_cache
            logger_write('INFO: refresh weather_info display...')
            logger_write('INFO: weather_info' + ', '.join(time_list))
            logger_write('INFO: weather_info' + ', '.join(weather_list))
            logger_write('INFO: weather_info' + ', '.join(rain_list))
            logger_write('INFO: weather_info' + ', '.join(temp_list))
            logger_write('INFO: weather_info' + ', '.join(wind_list))

        img = np.full((240, 320, 3), 255, dtype=np.uint8)

        col_width = 48
        row_height = 24
        icon_left=2
        icon = cv2.imread('img/CLOCK2.png')
        h, w = icon.shape[:2]
        img[row_height*0:row_height*0+h, icon_left:icon_left+w] = icon
        img[row_height*1:row_height*1+h, icon_left:icon_left+w] = cv2.imread('img/WEATHER2.png')
        img[row_height*2:row_height*2+h, icon_left:icon_left+w] = cv2.imread('img/WATER2.png')
        img[row_height*3:row_height*3+h, icon_left:icon_left+w] = cv2.imread('img/TEMP2.png')
        img[row_height*4:row_height*4+h, icon_left:icon_left+w] = cv2.imread('img/WIND2.png')
        img[row_height*5:row_height*5+h, icon_left:icon_left+w] = icon
        img[row_height*6:row_height*6+h, icon_left:icon_left+w] = cv2.imread('img/WEATHER2.png')
        img[row_height*7:row_height*7+h, icon_left:icon_left+w] = cv2.imread('img/WATER2.png')
        img[row_height*8:row_height*8+h, icon_left:icon_left+w] = cv2.imread('img/TEMP2.png')
        img[row_height*9:row_height*9+h, icon_left:icon_left+w] = cv2.imread('img/WIND2.png')
        
        grid_color=(242,242,242)
        for i in range(weather_info_count):
            x = i % 6
            y = i // 6
            base_pos_x = (col_width * x) + 32
            base_pos_y = (row_height*5) * y
            offset_x = -9
            offset_y = -14

            cv2.rectangle(img, (base_pos_x, base_pos_y+(row_height*0)), (base_pos_x+col_width-1,  base_pos_y+(row_height*1)-1), grid_color) #time
            img = putText_japanese(img, time_list[i].rjust(2), (base_pos_x+col_width+offset_x, base_pos_y+(row_height*1)+offset_y), 26, (255, 0, 0), 'rb')
            
            if weather_list[i] in ['100','123','124','130','131','500','550','600']:
                # sunny
                icon = cv2.imread('img/SUNNY2.png')
                h, w = icon.shape[:2]
                ofset_x = int((col_width-w)/2)
                img[base_pos_y+(row_height*1):base_pos_y+(row_height*1)+h, base_pos_x+ofset_x:base_pos_x+ofset_x+w] = icon
            elif weather_list[i] in ['200','209','231']:
                # cloudy
                icon = cv2.imread('img/CLOWD2.png')
                h, w = icon.shape[:2]
                ofset_x = int((col_width-w)/2)
                img[base_pos_y+(row_height*1):base_pos_y+(row_height*1)+h, base_pos_x+ofset_x:base_pos_x+ofset_x+w] = icon
            elif weather_list[i] in ['300','304','306','308','328','329','350','650','850']:
                # rainy
                icon = cv2.imread('img/RAIN2.png')
                h, w = icon.shape[:2]
                ofset_x = int((col_width-w)/2)
                img[base_pos_y+(row_height*1):base_pos_y+(row_height*1)+h, base_pos_x+ofset_x:base_pos_x+ofset_x+w] = icon
            elif weather_list[i] == '800':
                # thunder
                icon = cv2.imread('img/THUNDER2.png')
                h, w = icon.shape[:2]
                ofset_x = int((col_width-w)/2)
                img[base_pos_y+(row_height*1):base_pos_y+(row_height*1)+h, base_pos_x+ofset_x:base_pos_x+ofset_x+w] = icon
            elif weather_list[i] in ['340','400','405','406','407','425','426','427','430','450','950']:
                # slow
                icon = cv2.imread('img/SNOW2.png')
                h, w = icon.shape[:2]
                ofset_x = int((col_width-w)/2)
                img[base_pos_y+(row_height*1):base_pos_y+(row_height*1)+h, base_pos_x+ofset_x:base_pos_x+ofset_x+w] = icon
            else:
                img = putText_japanese(img, '??', (base_pos_x+col_width+offset_x, base_pos_y+(row_height*2)+offset_y), 26, (0, 0, 255), 'rb')

            cv2.rectangle(img, (base_pos_x, base_pos_y+(row_height*1)), (base_pos_x+col_width-1,  base_pos_y+(row_height*2)-1), grid_color) #weather

            cv2.rectangle(img, (base_pos_x, base_pos_y+(row_height*2)), (base_pos_x+col_width-1,  base_pos_y+(row_height*3)-1), grid_color) #rain
            img = putText_japanese(img, rain_list[i].rjust(2), (base_pos_x+col_width+offset_x, base_pos_y+(row_height*3)+offset_y), 26, (0, 0, 0), 'rb')

            cv2.rectangle(img, (base_pos_x, base_pos_y+(row_height*3)), (base_pos_x+col_width-1,  base_pos_y+(row_height*4)-1), grid_color) #temp
            img = putText_japanese(img, temp_list[i].rjust(2), (base_pos_x+col_width+offset_x, base_pos_y+(row_height*4)+offset_y), 26, (0, 0, 0), 'rb')

            cv2.rectangle(img, (base_pos_x, base_pos_y+(row_height*4)), (base_pos_x+col_width-1,  base_pos_y+(row_height*5)-1), grid_color) #wind
            img = putText_japanese(img, wind_list[i].rjust(2), (base_pos_x+col_width+offset_x, base_pos_y+(row_height*5)+offset_y), 26, (0, 0, 0), 'rb')

        # convert cv2-BGR -> PIL_RGB
        img2 = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        with self.lock_lcd:
            self.display.image(img2, x=0, y=240)
            logger_write('INFO: refresh weather_info display finished.')

def main():
    pass

if __name__ == '__main__':
    sys.exit(main())
