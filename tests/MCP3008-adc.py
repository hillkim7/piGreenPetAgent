# read ADC value from MCP3008 ADC chip
import spidev
import time

spi = spidev.SpiDev()
spi.open(0, 0)

def read_channel(channel):
    assert 0 <= channel <= 7, 'ADC channel must be a value of 0-7'
    # make read cmd.
    cmd = 0b11 << 6  # Start bit, single channel read
    cmd |= (channel & 0x07) << 3  # channel number (in 3 bits)
    resp = spi.xfer2([cmd, 0x0, 0x0])
    result = (resp[0] & 0x01) << 9
    result |= (resp[1] & 0xFF) << 1
    result |= (resp[2] & 0x80) >> 7
    return result & 0x3FF

while True:
    values = list(map(lambda x: read_channel(x), range(8)))
    print(values)
    time.sleep(0.5)
