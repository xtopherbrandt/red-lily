#!/usr/bin/python

import unittest
from dataProcessor import DataProcessor

class TestDataProcessor( unittest.TestCase ):
    def test_duration_of_points_with_increasing_values(self):
        measurements=[1.0,2.0,3.0]
        times=[0,1,2]
        bins={}
        DataProcessor.binMeasurements( bins, measurements, times, 'test' )
        
        self.assertEqual({'test_1.5':1, 'test_2.5':1}, bins )
   
    def test_duration_of_points_with_same_values(self):
        measurements=[2.0,2.0,2.0]
        times=[0,1,2]
        bins={}
        DataProcessor.binMeasurements( bins, measurements, times, 'test' )
        
        self.assertEqual({'test_2.0':2}, bins )

    def test_duration_of_points_with_decreasing_values(self):
        measurements=[3.0,2.0,1.0]
        times=[0,1,2]
        bins={}
        DataProcessor.binMeasurements( bins, measurements, times, 'test' )
        
        self.assertEqual({'test_1.5':1, 'test_2.5':1}, bins )


if __name__ == '__main__':
    unittest.main()