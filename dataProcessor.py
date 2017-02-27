#!/usr/bin/python

import pickle
import sys
from units import * 
sys.path.append("./tools/")
from feature_format import featureFormat, targetFeatureSplit

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

def binMeasurements(bin_dict, measurementStream, timeStream, binPrefix ):
    """
    Iterates a stream of measurements, adding the time spent at each measured
    value to a bin for the measured value. Bins are added as items to the bin_dict
    with the name as binPrefix_measuredValue ie, velocity_3.5

    :param bin_dict: the dictionary to add the bins to. This is the data point.
    :param measurementStream: an array of measurement values. Must have the same length as timeStream.abs
    :param timeStream: an array of time values.
    :param binPrefix: the name of the bin class
    """
    point0 = None
    point1 = None

    for point in zip( measurementStream, timeStream ):
        point0 = point1
        point1 = point
        binValue, duration = medianBinFunction( point0, point1 )

        if binValue is not None:
            binName = '{0}_{1}'.format(binPrefix, round(binValue,1))

            if binName not in bin_dict :
                bin_dict[binName] = duration
            else :
                bin_dict[binName] += duration

### read in data dictionary, convert to numpy array
data_dict = pickle.load( open("20160605153022.pkl", "r") )
#features = ["poi", "salary", "total_payments", 'bonus', 'deferred_income', 'total_stock_value', 'expenses', 'exercised_stock_options', 'other', 'long_term_incentive', 'restricted_stock','to_messages', 'from_poi_to_this_person', 'from_messages', 'from_this_person_to_poi', 'shared_receipt_with_poi']

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
    #data_point['workout_duration'] += workout['total_time']
    
    binMeasurements(data_point, workout['velocity_smooth_stream'], workout['time_stream'], 'velocity')

print data_point

### Tests 
###
timeSum1 = 0
for feature in data_point:
    
    if feature.find('velocity_')==0:
        
        timeSum1 += data_point[feature]
        print '{0},{1}'.format(feature, data_point[feature])

print 'Sum of velocity times:', timeSum1

timeSum2 = 0
for workout in data_dict['workout_set']:
    timeSum2 += workout['time_stream'][len(workout['time_stream'])-1]

print 'Sum of workout times:', timeSum2
