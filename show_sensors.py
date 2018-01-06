#!/usr/bin/env python3
# read ADC value from MCP3008 ADC chip
import spidev
import time
import sensor_table

WATER_LEVEL_CHANNEL=0
SOIL_HUMIDIFY_CHANNEL=1
CO2_CHANNEL=2
LIGHT_CHANNEL=3

spi = spidev.SpiDev()
spi.open(0, 0)

spi.mode = 0
old_speed = spi.max_speed_hz
# MCP3008 doesn't work on default Pi SPI speed, 125000000
# It must set the speed as 1 M.
spi.max_speed_hz = 1000000
print('max_speed_hz %d --> %d' % (old_speed, spi.max_speed_hz))

def read_channel(channel):
    assert 0 <= channel <= 7, 'ADC channel must be a value of 0-7'
    # make read cmd.
    cmd = 0b11 << 6  # Start bit, single channel read 
    cmd |= (channel & 0x07) << 3  # channel number (in 3 bits)
    resp = spi.xfer2([cmd, 0, 0])
    #print(channel, resp)
    #resp = spi.xfer2([1, (8+channel) << 4, 0])
    result = (resp[0] & 0x01) << 9
    result |= (resp[1] & 0xFF) << 1
    result |= (resp[2] & 0x80) >> 7
    return result & 0x3FF

delay = 0.2
while True:
    raw_val = read_channel(WATER_LEVEL_CHANNEL)
    cval = sensor_table.convert_water_level(raw_val)
    print('%16s %4d -> %3.2f' % ('WATER_LEVEL', raw_val, cval))
    time.sleep(delay)
    raw_val = read_channel(SOIL_HUMIDIFY_CHANNEL)
    cval = sensor_table.convert_soil_humi(raw_val)
    print('%16s %4d -> %3.2f' % ('SOIL_HUMIDIFY', raw_val, cval))
    time.sleep(delay)
    raw_val = read_channel(CO2_CHANNEL)
    cval = sensor_table.convert_co2(raw_val)
    print('%16s %4d -> %3.2f' % ('CO2', raw_val, cval))
    time.sleep(delay)
    raw_val = read_channel(LIGHT_CHANNEL)
    cval = sensor_table.convert_cds(raw_val)
    print('%16s %4d -> %3.2f' % ('LIGHT', raw_val, cval))
    time.sleep(delay*3)
    print()
 