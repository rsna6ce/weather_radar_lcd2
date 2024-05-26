# weather_radar_lcd
* weather_radar_lcdは、雨雲レーダー画像を表示する端末です
* 使用は日本国内専用です

## 配線
* ジャンパ線で各デバイスのピンを接続する
  * 配線のピンを間違えた状態で電源を入れると一発でデバイスが故障する場合もある
  * 指差し呼称で接続が合っているか良く確認すること
* ラズパイピン配置（参考）出典: [raspberrypi.org](https://www.raspberrypi.org/documentation/usage/gpio/)
* <img width=640 src=https://github.com/rsna6ce/weather_radar_lcd/assets/86136223/687b129c-a3af-4ca9-8c3a-76dba8b16038>
* 凡例
  * LCD: TFTインチ液晶ディスプレイ タッチパネル 320x480 SPI ILI9341
  * Touch sw: TTP223 静電容量式 タッチ スイッチ
  * HC-SR04: 超音波センサー
  * OLED: 液晶ディスプレイ SSD1306 128x32

| raspi pin no | raspi pin name | device name | device pin |
| ---: | :--- | :--- | :--- |
| 21 | GPIO9(SPI0 MISO) | LCD | SDO(MISO) |
| 12 | GPIO18 | LCD| LED  |
| 23 | GPIO11(SPI0 SCLK) | LCD | SCK |
| 19 | GPIO10(SPI0 MOSI) | LCD | SDI(MOSI) |
| 18 | GPIO24 | LCD | DC |
| 16 | GPIO23 | LCD | RESET |
| 24 | GPIO8(SPI0 CS0) | LCD | CS |
| 14 | Ground | LCD | GND |
| 17 | 3V3 Power | LCD | VCC |
| 1 | 3V3 Power | Touch sw | VCC |
| 5 | GPIO3(SCL) | Touch sw | I/O |
| 9 | Ground | Touch sw | GND |
| 2 | 5V Power | HC-SR04 | Vcc |
| 38 | GPIO20(PCM_DIN) | HC-SR04 | Trig |
| 40 | GPIO21(PCM_DOUT) | HC-SR04 | Echo |
| 34 | Gnd | HC-SR04 | Ground |
| 29 | GPIO5 | OLED | SDA |
| 31 | GPIO6 | OLED | SCK |
| 1 | 3V3 Power | OLED | VCC |
| 6 | Ground | OLED | GND |
