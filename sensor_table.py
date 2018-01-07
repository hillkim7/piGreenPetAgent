#!/usr/bin/env python3
# read ADC value from MCP3008 ADC chip
import unittest

class ConvertData:
    
    def __init__(self, src_range, target_range):
        self.src_range = src_range
        self.target_range = target_range
        
    def convert(self, raw_val):
        src_diff = self.src_range[1] - self.src_range[0]
        target_diff = self.target_range[1] - self.target_range[0]
        # src_diff : target_diff = delta(raw_val) : delta_x
        # target_diff * raw_val == src_diff * x
        delta_raw_val =  raw_val - self.src_range[0]
        delta_x = float(delta_raw_val * target_diff) / float(src_diff)
        #print("%s %d --> %d" % (self.__str__(), delta_raw_val, delta_x))
        return self.target_range[0] + delta_x
    
    @staticmethod
    def get_key(convert_data):
        return convert_data.src_range[0]
    
    def __str__(self):
        return str(self.src_range + self.target_range)
    
class ConvertTable:   
    def __init__(self, convert_matrix):
        self.table = []
        for row in convert_matrix:
            src_range = (row[0], row[1])
            target_range = (row[2], row[3])
            self.table.append(ConvertData(src_range, target_range))        
        self.table = sorted(self.table, key=ConvertData.get_key)    

    def convert(self, raw_val):
        test_data = self.table[0]
        for tdata in self.table[1:]:
            #print("%s, %s" % (test_data, tdata))
            if raw_val < tdata.src_range[0]:
                break
            test_data = tdata
        if raw_val < test_data.src_range[0]:
            return test_data.target_range[0]
        if raw_val > test_data.src_range[1]:
            return tdata.target_range[1]
        return test_data.convert(raw_val)

water_level_matrix = [
    [0, 520, 0, 10],
    [520, 570, 10, 20],
    [570, 585, 20, 30],
    [585, 605, 30, 40],
    ]
water_level_table = ConvertTable(water_level_matrix)


def truncate(f, n):
    '''Truncates/pads a float f to n decimal places without rounding'''
    s = '%.12f' % f
    i, p, d = s.partition('.')
    val = '.'.join([i, (d+'0'*n)[:n]])
    return float(val)

def convert_water_level(raw_val):
    val = water_level_table.convert(raw_val)
    return truncate(val, 2)

def convert_co2(raw_val):
    return raw_val * 2

def convert_cds(raw_val):
    val = (1023 - raw_val) / 3
    val = val - 100
    return truncate(val, 2)

soil_humi_matrix = [
    [400, 700, 0, 10],
    [700, 900, 10, 90],
    [900, 1023, 90, 100],
    ]
soil_humi_table = ConvertTable(soil_humi_matrix)
    
def convert_soil_humi(raw_val):
    raw_val = 1023 - raw_val
    val = soil_humi_table.convert(raw_val)
    #print("%d->%d" % (raw_val, cval))
    return truncate(val, 2)

class TestCoverter(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestCoverter, self).__init__(*args, **kwargs)
        matrix = [
            [200, 300, 20, 30],
            [100, 200, 10, 20],
            [300, 400, 30, 40]
            ]
        self.test_table = ConvertTable(matrix)
        
    def test_min_range_err(self):
        self.assertEqual(self.test_table.convert(5), 10)

    def test_max_range_err(self):
        self.assertEqual(self.test_table.convert(500), 40)

    def test_convert(self):
        self.assertEqual(self.test_table.convert(250), 25)
        self.assertEqual(self.test_table.convert(390), 39)
