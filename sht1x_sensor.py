## obtaining temperature and humidity using SHT10 sensor.

import RPi.GPIO as GPIO
from pi_sht1x import SHT1x

DATA_PIN = 2
SCK_PIN = 3

class SHT1xSensor:
    def __init__(self):
        pass

    def read_values(self):
      with SHT1x(DATA_PIN, SCK_PIN, gpio_mode=GPIO.BCM, vdd='3.5V', resolution='High',
                 heater=False, otp_no_reload=False, crc_check=True) as sensor:
          temp = sensor.read_temperature()
          humidity = sensor.read_humidity(temp)
          sensor.calculate_dew_point(temp, humidity)
          print(sensor)
          return (round(temp, 2), round(humidity, 2))


if __name__ == "__main__":
    sht = SHT1xSensor()
    measured_values = sht.read_values()
    print("temperature=%f humility=%f" % measured_values)
