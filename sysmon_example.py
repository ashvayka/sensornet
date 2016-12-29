#!/usr/bin/env python
# -*- coding: utf-8 -*-

####################################################################
# Script to gather system usage information to monitor for resource
#    limitations and to allow for the alerting within the Thingsboard
#    Rules engine, if configured to do so.
#
# Publishes the following client attributes:
#    DiskTotal:    Total amount of disk installed
#    RAMTotal:     Total amount of RAM installed
#    Name:         Common name of device
#    Location:     Location information as definec in Me attributes
#    PlatformL     Hardware platform information from Me attributes
#    Interface(s)  Interface name and IP addresses of interfaces installed
#
# Publishes the following telemetry values:
#    CPUTemp:      Temp of the CPU as reported by the systems
#    CPUUsage:     Percentage of CPU used
#    RAMUsed:      Percentage of RAM used
#    DiskUsed:     Percentage of Disk used
####################################################################

from subprocess import PIPE, Popen     # Used for system metric gathering
import time                            # used in calculating sleep timer
import psutil                          # Used for system metric gathering
import netifaces as ni                 # Used to gether interface informatioin
import requests                        # Used for creating HTTP sessions to ThingsBoard server
import json                            # Used for data formatting

me = {
    'Platform': "Raspberry Pi Zero",            # Describe the hardware platform information is gathered from
    'Name': 'Lab Monitor',                      # Name of the sensor, descriptive
    'Location': 'New York, NY'                  # Common name of location
    }

conn = {
    'server': '[YOUR SERVER HERE]',              # IP or hostname of manager    
    'method': "http",                            # Method used to send data to TB server
    'authkey': '[YOUR AUTH KEY HERE]'            # Auth Key for your device
    }

# Combine some of the above variables for use in later processing
url = {
    'attr': conn['method'] + '://' + conn['server'] +'/api/v1/'+conn['authkey']+'/attributes',
    'tele': conn['method'] + '://' + conn['server'] +'/api/v1/'+conn['authkey']+'/telemetry',
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
	'CPU Temp': cpu_temperature,
	'CPU Usage': cpu_usage,
	'RAM Used': ram_percent_used,
	'Disk Used': disk_percent_used
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
