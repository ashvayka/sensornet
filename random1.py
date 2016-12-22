#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import json
import sys
import time
import requests
import random
from subprocess import PIPE, Popen

#
# Script to scrape information periodically from local sensors and report them to ThingsBoard
#   via HTTP.
#


conn = {
    'server': 'demo.thingsboard.io',              # IP or hostname of manager    
    'port': 1883,                                 # MQTT server port number
    'method': "http",                             # Method used to send data to TB server
    'authkey': '[REDACTED]',           # Auth Key for development laptop
    'attributes': 'v1/devices/me/attributes',     # Topic where device attributes are published
    'telemetry': 'v1/devices/me/telemetry'        # Topic where device telemetry is published
    }

attr = {
    'platform': "Raspberry Pi 3",
    'name': 'Lab Monitor',                       # Name of the sensor, descriptive
    'location': 'Memphis, TN',                   # Common name of location
    'address': '1313 Mockingbird Lane',                 # Street address where device is located
    'lattitude': 40.748441,                      # Used for map overlay
    'longitude': -73.985664,                      # used for map overlay
    'contact': 'Your Name Here',                    # Primary contact responsible for area being monitored
    'contact_email': 'youremail@tld.foo',            # Primary contact email address
    'contact_phone': '800-555-12128',               # primary contact phone
    'alerttemp': 75,
    'alarmTemp': 80
    }

rand = [
    {'id': 1,
     'name': 'Lab Main',
    'temp': random.randrange(65,75,1)},
    {'id': 2,
     'name': 'Lab Freezer',
    'temp': random.randrange(65,75,1)},
    {'id': 3,
     'name': 'Lab - Server Room',
    'temp': random.randrange(65,75,1)},
    {'id': 4,
     'name': 'Network Closet',
    'temp': random.randrange(65,75,1)},
    {'id': 54,
     'name': 'Outside',
    'temp': random.randrange(25,45,1)},
]

http_headers = {'Content-Type': 'application/json'}
url = {
        'attributes': conn['method'] + '://' + conn['server'] +'/api/v1/'+conn['authkey']+'/attributes',
        'telemetry': conn['method'] + '://' + conn['server'] +'/api/v1/'+conn['authkey']+'/telemetry',
        }
def main():

    s_count=0
    message = {
        'sensorcount': len(rand)
        }
    for (id) in rand:
        #print(rand[s_count]['name'])
        x = rand[s_count]['temp']
        message[rand[s_count]['name']] = x
        s_count = s_count + 1

    r_tele = requests.post(url['telemetry'], data=json.dumps(message), headers=http_headers)
    r_attr = requests.post(url['attributes'], data=json.dumps(attr), headers=http_headers)

    #print(json.dumps(message))
    
if __name__ == '__main__':
    main()
