from flask import Flask, redirect, url_for, request, session, render_template
from stravalib import Client
from stravalib.exc import ActivityUploadFailed
import os, sys
from requests.exceptions import HTTPError
from datetime import datetime, date, timedelta
import pickle
from units import *
import xml.etree.ElementTree as ET
import shutil

# Next we create an instance of this class. 

app = Flask(__name__)
app.secret_key = os.urandom(24)
access_token = ''
client = Client()


def saveDataPoint(raceActivity):
    firstDate = raceActivity.start_date - timedelta(weeks=3)
    app.logger.debug("  Data point from: {0} to {1}".format(firstDate, raceActivity.start_date))
    dataPointActivities = client.get_activities( after=firstDate, before=raceActivity.start_date )
    dataPointFeatures = {}
    dataPointFeatures['first_date'] = firstDate
    dataPointFeatures['race_date'] = raceActivity.start_date
    dataPointFeatures['race_distance'] = raceActivity.distance
    dataPointFeatures['race_speed'] = raceActivity.average_speed
    dataPointFeatures['workout_set'] = []

    for activity in dataPointActivities:
        if activity.type == 'Run':
            workout = {}
            workout['date'] = activity.start_date
            workout['distance'] = activity.distance
            workout['average_speed'] = activity.average_speed
            workout['total_time'] = activity.elapsed_time

            try:
                workout_stream = client.get_activity_streams(activity_id = activity.id, types=['time','distance','altitude', 'velocity_smooth','heartrate','cadence','grade_smooth'], resolution='high')
                for stream_type in workout_stream.keys():
                    workout['{0}_stream'.format(stream_type)] = workout_stream[stream_type].data

                dataPointFeatures['workout_set'].append(workout)
            except HTTPError as e:
                app.logger.debug('Http Error while trying to get streams for activity {0}\n{1}'.format(activity.id, e))
    
    app.logger.debug('  ...{0} workouts in this data point'.format(len(dataPointFeatures['workout_set'])))
    
    filename = raceActivity.start_date.strftime('%Y%m%d%H%M%S')
    with open('{0}.pkl'.format(filename), "w") as dataPoint_outfile:
        pickle.dump(dataPointFeatures, dataPoint_outfile)

@app.route('/')
def hello_world():
    return render_template('helloworld.htm')

@app.route('/authorize')
def authorize():
    url = client.authorization_url(client_id=16323, redirect_uri='http://127.0.0.1:8887/exchange', scope='view_private,write')
    return redirect(url)

@app.route('/exchange', methods=['GET'])
def exchange():
    code = request.args.get('code')
    access_token = client.exchange_code_for_token(client_id=16323, client_secret='acc979731b8be9933f46ab89f9d8094c705a3503', code=code)
    client.access_token = access_token
    session['logged_in'] = True
    app.logger.debug('Access Token: %s', access_token)
    return render_template('commands.htm')

@app.route('/activities', methods=['GET'])
def activities():
    # if we don't have an access token, reauthorize first
    if client.access_token == None:
        app.logger.debug("Reauthorizing...")
        return redirect(url_for('authorize'))

    try:
        activity_set = client.get_activities( before='2014-12-01', after='2008-01-01' )
        activities = []
        for activity in activity_set:
            activities.append({'id':activity.id, 'external_id':activity.external_id, 'distance':activity.distance, 'name':activity.name, 'desc':activity.description})

        app.logger.debug(activities[0])
        return render_template('show_activities.html', activites=activities)
    except HTTPError:
        app.logger.debug("Reauthorizing...")
        return redirect(url_for('authorize'))
    except Exception as e:
        app.logger.debug(e)
        return str(e)

@app.route('/generateDataPoints', methods=['GET'])
def generateDataPoints():
    # if we don't have an access token, reauthorize first
    if client.access_token == None:
        app.logger.debug("Reauthorizing...")
        return redirect(url_for('authorize'))

    try:
        app.logger.debug('Searching...')
        activity_set = client.get_activities( )
        
        for activity in activity_set:
            if activity.workout_type == '1' :
                app.logger.debug('Found Race : {0} - {1}'.format( activity.name, activity.start_date))
                saveDataPoint(activity)
        return "OK"
    except Exception as e:
        app.logger.debug(e)
        return str(e)

@app.route('/activities/stream', methods=['GET'])
def activitiesStream():
    # if we don't have an access token, reauthorize first
    if client.access_token == None:
        app.logger.debug("Reauthorizing...")
        return redirect(url_for('authorize'))

    try:
        stream = client.get_activity_streams(activity_id = 856784749, types=['time','distance','altitude', 'velocity_smooth','heartrate','cadence','grade_smooth'], resolution='high')
                
        return "OK"
    except HTTPError:
        app.logger.debug("Reauthorizing...")
        return redirect(url_for('authorize'))
    except Exception as e:
        app.logger.debug(e)
        return str(e)


@app.route('/activities/files/batch')
def activitiesFilesBatch():
    '''
    Helper function to process a batch of local files

    DO NOT DEPLOY THIS METHOD TO PRODUCTION

    BIG SECURITY RISK
    '''
    # if we don't have an access token, reauthorize first
    if client.access_token == None:
        app.logger.debug("Reauthorizing...")
        return redirect(url_for('authorize'))

    # Create a mapping between the garmin ID and the strava ID for all activities
    # this was added to allow re-uploading of activity files
    activity_map = {}
    activity_set = client.get_activities( )
    for activity in activity_set:
        activity_map[activity.external_id] = activity.id

    # Get the file name from the query string
    file_directory = request.args.get('dir')
    completed_files = []

    files = os.listdir(file_directory)

    # For each file in the directory
    for gpx_file in files:
        # If this is a file
        if ( os.path.isfile( os.path.join(file_directory, gpx_file) ) ):
            
            # If this file has already been uploaded, delete it and re-upload
            if gpx_file in activity_map:
                app.logger.debug( 'Deleting activity {0}:{1}'.format(gpx_file, activity_map[gpx_file] ))
                client.delete_activity( activity_map[gpx_file] )

            try:
                # Process it
                time, name, desc, garmin_type, strava_type, external_id, data_type = processGpxFile(os.path.join(file_directory, gpx_file))
                
                # Move it to Done
                shutil.move(os.path.join(file_directory, gpx_file), os.path.join(file_directory, 'Done'))
            
                # Record it
                f = {'fileName':gpx_file, 'name': name, 'desc': desc, 'garmin_type': garmin_type, 'strava_type': strava_type, 'external_id': external_id }
                completed_files.append(f)
            except ActivityUploadFailed:
                # skip failures, these are usually duplicates
                 
                # Move it to Unprocessed
                shutil.move(os.path.join(file_directory, gpx_file), os.path.join(file_directory, 'Unprocessed'))
                pass
            except Exception as e:
                import traceback
                app.logger.debug('Exception while processing file:{0} : {1}'.format(gpx_file, e))
                exc_type, exc_value, exc_traceback = sys.exc_info()
                app.logger.debug(traceback.format_exception(exc_type, exc_value, exc_traceback ))
                return str(e)

    return render_template('show_uploaded_files.html', files=completed_files)

@app.route('/activities/files/upload')
def activitiesFilesUpload():
    name = 'Not Found'
    files = []

    # if we don't have an access token, reauthorize first
    if client.access_token == None:
        app.logger.debug("Reauthorizing...")
        return redirect(url_for('authorize'))

    try:
        # Get the file name from the query string
        gpx_file = request.args.get('file')

        # process and upload the file
        time, name, desc, garmin_type, strava_type, external_id, data_type = processGpxFile( gpx_file )
        f = {'fileName':gpx_file, 'name': name, 'desc': desc, 'garmin_type': garmin_type, 'strava_type': strava_type, 'external_id': external_id }
        files.append(f)
        return render_template('show_uploaded_files.html', files=files)
    except HTTPError:
        app.logger.debug("Reauthorizing...")
        return redirect(url_for('authorize'))
    except Exception as e:
        app.logger.debug(e)
        return str(e)

def processGpxFile(gpx_file_name):
    # Open the file for read processing
    with open( gpx_file_name, 'r') as activity_file:
        # Use XPath to find some of the details like name, description and type
        ET.register_namespace('', "http://www.topografix.com/GPX/1/1")
        root = ET.parse(activity_file).getroot()
        ns = {'gpxns':'http://www.topografix.com/GPX/1/1'}
        time_elem = root.find('gpxns:metadata/gpxns:time', ns)
        if time_elem is not None :
            time = time_elem.text
        else :
            time = ''
        name_elem = root.find('gpxns:trk/gpxns:name', ns)
        if name_elem is not None :
            name = name_elem.text
        else:
            name = ''
        desc_elem = root.find('gpxns:trk/gpxns:desc', ns)
        if desc_elem is not None :
            desc = desc_elem.text
        else:
            desc = ''
        garmin_type_elem = root.find('gpxns:trk/gpxns:type', ns)
        if garmin_type_elem is not None :
            garmin_type = garmin_type_elem.text
        else :
            garmin_type = ''
        external_id = gpx_file_name.split('_')[1].split('.')[0]
        data_type = gpx_file_name.split('_')[1].split('.')[1]

        # Convert the garmin type to a strava type
        strava_type = garminTypeToStravaType( garmin_type )

        # Replace all of the <ns3:TrackPointExtension> elements with <heartrate> element
        ns3 = {'extns':'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'}
        extenstions_elem = root.findall('.//gpxns:trkpt/gpxns:extensions', ns)
        for elem in extenstions_elem:
            trackpointExts_elem = elem.find('./extns:TrackPointExtension', ns3)
            hr = trackpointExts_elem.find('./extns:hr', ns3).text
            elem.remove(trackpointExts_elem)
            ET.SubElement(elem, 'heartrate').text = hr

        # Log what we know
        app.logger.debug('{0}: {1} {2} {3} {4}-->{5} {6} {7}'.format(gpx_file_name, time, name, desc, garmin_type, strava_type, external_id, data_type))

    # Now re-open it to save the modified GPX tree
    with open( gpx_file_name, 'w+') as activity_file:

        # Save the tree to the file
        tree = ET.ElementTree(root)
        tree.write(activity_file, xml_declaration=True, encoding='UTF-8')

        # Move the file pointer back to the start
        activity_file.seek(0)
        
        # Upload the file and wait for up to 1 min for the response to come back
        client.upload_activity( activity_file=activity_file, data_type=data_type, name=name, description=desc, activity_type=strava_type ).wait(timeout=60)

    return time, name, desc, garmin_type, strava_type, external_id, data_type

def garminTypeToStravaType( garminType ):
    if type(garminType) != str:
        app.logger.debug("invalid type {0}".format( type(garminType)))
        return None
    elif garminType.find('running') != -1:
        return 'run'
    elif garminType.find('cycling') != -1:
        return 'ride'
    elif garminType.find('biking') != -1:
        return 'ride'
    elif garminType == 'BMX':
        return 'ride'
    elif garminType.find('swimming') != -1:
        return 'swim'
    elif garminType == 'hiking':
        return 'hike'
    elif garminType.find('walking') != -1:
        return 'walk'
    elif garminType == 'cross_country_skiing':
        return 'nordicski'
    elif garminType == 'skate_skiing':
        return 'nordicski'
    elif garminType == 'resort_skiing_snowboarding':
        return 'alpineski'
    elif garminType == 'skating':
        return 'iceskate'
    elif garminType == 'inline_skate':
        return 'inlineskate'
    elif garminType == 'backcountry_skiing_snowboarding':
        return 'backcountryski'
    else:
        return None