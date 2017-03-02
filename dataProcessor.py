#!/usr/bin/python

import pickle
import sys, os
from units import * 
import numpy as np

class DataProcessor:

    _dataDirectory = ''
    _outputFileName = ''

    def __init__( self, dataDirectory, outputFileName ):
        if os.path.isdir( dataDirectory ):
            self._dataDirectory = dataDirectory
        
        if outputFileName is not None:
            self._outputFileName = outputFileName

    def Process(self):
        files = os.listdir( self._dataDirectory )
        data_dict = {}
        
        # For each file in the directory
        for next_file in files:
            fileParts = os.path.splitext(next_file)
            if fileParts[0].find(self._outputFileName) == -1 and fileParts[1] == '.pkl':
                data_point = DataProcessor.ProcessDataPointFile( next_file )
                data_dict[data_point['race_date']] = data_point
            
        with open('{0}.pkl'.format(self._outputFileName), "w") as data_outfile:
            pickle.dump(data_dict, data_outfile)
        
        print
        print '================='
        print data_dict

    @staticmethod
    def medianBinFunction (point0, point1):
        """
        Simple function to find the bin and duration given two consecutive points
        :param point0: a tuple (measuredValue, time)
        :param point1: a tuple (measuredValue, time)
        :return: binValue, duration
        """
        if point0 is None or point1 is None:
            return None, None

        binValue = ( point1[0] - point0[0] ) / 2 + point0[0]
        duration = point1[1] - point0[1]
        return binValue, duration

    @staticmethod
    def binMeasurements( bin_dict, measurementStream, timeStream, binPrefix, rangeMin, rangeMax, binIncrement ):
        """
        Iterates a stream of measurements, adding the time spent at each measured
        value to a bin for the measured value. Bins are added as items to the bin_dict
        with the name as binPrefix_measuredValue ie, velocity_3.5

        :param bin_dict: the dictionary to add the bins to. This is the data point.
        
        :param measurementStream: an array of measurement values. Must have the same length as timeStream.abs
        
        :param timeStream: an array of time values.
        
        :param binPrefix: the name of the bin class

        :param rangeMin: the lower end of the measurement range. 
                            Values below the min will be tossed.
        
        :param rangeMax: the upper end of the measurement range. 
                            Values equal to or above the max will be tossed.
        
        :param binIncrement: the increment in measurement values between bins
        """
        point0 = None
        point1 = None

        # create an array of bin edges
        bin_edges = np.linspace( rangeMin, rangeMax, ((rangeMax - rangeMin)/binIncrement) + 1 )

        # Add the range of bins to the dictionary. 
        #   the name of each bin uses the bin index, not its measurement value
        for binIndex in range(bin_edges.size - 1):
            binName = '{0}_{1}-{2}'.format(binPrefix, bin_edges[binIndex], bin_edges[binIndex+1])
            bin_dict[binName] = 0

        # Go through the stream and get the bin value and duration for each increment
        for point in zip( measurementStream, timeStream ):
            point0 = point1
            point1 = point
            measurementValue, duration = DataProcessor.medianBinFunction( point0, point1 )

            # If we got a valid result, add it to the appropriate bin in the dictionary
            if measurementValue is not None:
                try:
                    binIndex = np.digitize( measurementValue, bin_edges )
                    if binIndex > 0 and binIndex < bin_edges.size :
                        binName = '{0}_{1}-{2}'.format(binPrefix, bin_edges[binIndex-1], bin_edges[binIndex])
                        bin_dict[binName] += duration
                        #print measurementValue, duration, binIndex, binName
                    else:
                        print "Value {0} falls outside of bins for {1}".format(measurementValue, binPrefix)
                except IndexError:
                    print "Value {0} falls outside of bins for {1}".format(measurementValue, binPrefix)

    @staticmethod
    def ProcessDataPointFile(file):
        print
        print 'Processing file:', file
        ### read in data dictionary, convert to numpy array
        data_dict = pickle.load( open(file, "r") )

        # Normalize / flatten this data point
        data_point = {}
        data_point['race_date'] = data_dict['race_date'].isoformat()
        data_point['race_distance'] = float( data_dict['race_distance'] )
        data_point['race_speed'] = float( data_dict['race_speed'] )
        data_point['workout_count'] = 0
        data_point['workout_distance'] = 0.0
        data_point['workout_duration'] = 0

        # for each workout in the data dictionary
        #   add time spent to each measurement bin

        for workout in data_dict['workout_set']:
            # Add to the overall summaries
            data_point['workout_count'] += 1
            data_point['workout_distance'] += float( workout['distance'] )
            data_point['workout_duration'] += workout['total_time'].total_seconds()
            
            if 'velocity_smooth_stream' in workout:
                DataProcessor.binMeasurements(data_point, workout['velocity_smooth_stream'], workout['time_stream'], 'velocity', rangeMin=1.0, rangeMax=10.0, binIncrement=0.1 )
            if 'cadence_stream' in workout:
                DataProcessor.binMeasurements(data_point, workout['cadence_stream'], workout['time_stream'], 'cadence', rangeMin=50, rangeMax=300, binIncrement=2)
            
        print data_point
        DataProcessor._sanityCheck( data_point, data_dict )

        return data_point

    @staticmethod
    def _sanityCheck(processed_data_point, data_point_dict):
        ### Tests 
        ###
        timeSum1 = 0
        for feature in processed_data_point:
            
            if feature.find('velocity_')==0:
                
                timeSum1 += processed_data_point[feature]

        print 'Sum of velocity times:', timeSum1

        timeSum2 = 0
        for workout in data_point_dict['workout_set']:
            timeSum2 += workout['time_stream'][len(workout['time_stream'])-1]

        print 'Sum of workout times:', timeSum2
