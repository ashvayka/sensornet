#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division
####################################################################
# Script to gather information on the device gathering sensor
#     information to help prevent failures ahead of time
#
####################################################################
#import config as cfg         # Bring in shared configuration file
#import common as com         # Bring in shared functions file
####################################################################
from subprocess import PIPE, Popen
import sys, random
import time
import psutil
import netifaces as ni
import requests
import json

me = {
    'version': 1.2,
    'Platform': "Raspberry Pi Zero",
    'Name': 'Lab Monitor',                       # Name of the sensor, descriptive
    'Location': 'New York, NY'                  # Common name of location
    }

conn = {
    'server': '[YOUR SERVER HERE]',              # IP or hostname of manager    
    'method': "http",                             # Method used to send data to TB server
    'authkey': '[YOUR AUTH KEY HERE]'             # Auth Key for "temp" device
    }

url = {
    'attr': 'http://' + conn['server'] +'/api/v1/'+conn['authkey']+'/attributes',
    'tele': 'http://' + conn['server'] +'/api/v1/'+conn['authkey']+'/telemetry',
    }
http_headers = {'Content-Type': 'application/json'}

def get_cpu_temperature():
    process = Popen(['vcgencmd', 'measure_temp'], stdout=PIPE)
    output, _error = process.communicate()
    temp_c = float(output[output.index('=') + 1:output.rindex("'")])
    temp_f = 9.0/5.0 * temp_c + 32
    return temp_f

def main():
    # give the CPU a second after launch
    time.sleep(2)
    cpu_usage = psutil.cpu_percent()

    cpu_temperature = get_cpu_temperature()
    ram = psutil.phymem_usage()
    ram_total = ram.total / 2**20       # MiB.
    ram_used = ram.used / 2**20
    ram_free = ram.free / 2**20
    ram_percent_used = ram.percent

    disk = psutil.disk_usage('/')
    disk_total = disk.total / 2**30     # GiB.
    disk_used = disk.used / 2**30
    disk_free = disk.free / 2**30
    disk_percent_used = disk.percent
   
    message = {
	'CPUTemp': cpu_temperature,
	'CPUUsage': cpu_usage,
	'RAMUsed': ram_percent_used,
	'DiskUsed': disk_percent_used
        }

    attributes = me
    
    attributes['DiskTotal'] = str(round(disk_total,1)) + 'GB'
    attributes['RAMTotal'] = str(round(ram_total,1)) + 'MB'

    # Get a ilst of network interfaces, and get the IP address for each - add to attributes
    ifaces = ni.interfaces();
    for x in ifaces:
        try:
            ip = ni.ifaddresses(x)[2][0]['addr']
            attributes[x] = ip
        except:
            attributes[x] = "none"

    r_tele = requests.post(url['tele'], data=json.dumps(message), headers=http_headers)
    r_attr = requests.post(url['attr'], data=json.dumps(attributes), headers=http_headers)

    
if __name__ == '__main__':
    main()



