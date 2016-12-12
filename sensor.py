#!/usr/bin/env python

#############################################################################
# Sensor Hub - senor monitoring, alerting, and graphing for distributed sensors
# Bob Perciaccante - 2016 Rev 1.0
# 
# About:  Setup as a cron job, runs every ten minutes and polls the
# 	  sensors for temperature information.  This is combined with external
#     conditions and is saved as logs, entered in MySQL, and/or graphed with 
#     RRDTool images sent to a local web server directory 
# Probes:
#	Temp:  DS18B20, 1-Wire Digital
#
# Notes:
#
# Things to fix:
#  1 - Include self checking measures:
#      CPU temp from /sys/class/thermal/thermal_zone0/temp
#
# Module Requirements:
#  - bs4 (via pip) for processing XML data
#  - rrdtool (via pip)for saving data and generating graphs for webpage
#  - You will need an API key from OpenWeatherMaps to be able to pull temp data
############################################################################# 

import smtplib					# used for email alerting
import time			
import requests					# used for getting external info via HTTP
#import rrdtool					# data graphing system
#from rrdtool import update as rrd_update
from bs4 import BeautifulSoup	# used to parse XML for weather information
#import MySQLdb as my            # used for MySQL connection

start = time.time()
#############################################################################
#                            Configuration                                  #
#############################################################################

# Global settings
strSourceDeviceId = "Sensor Hub"
strSourceDeviceType = "local"                   # set this to remote for remote sensors
strSourceDeviceIP = "10.87.96.211"
strSourceDeviceLocation = "Malvern, PA"
strSourceDeviceDescription = "Central Monitoring Hub"
strLogFile="logs/events_new.log"
strRecordFile="logs/record_new.log"
strTimeNow=time.strftime("%Y-%m-%d %H:%M:%S")

# Define Enabled Features
intGenerateLog = 1						# If you want messages sent to log, set to 1
intGenerateRecord = 1				    # If you want messages sent to record log, set to 1
intGenerateDBEntry = 1					# If you want messages written to MySQL, set to 1
intHTTPProxyRequired = 1                # set to 1 to enable outbound HTTP proxy
intEmailNotificationsEnabled = 1        # set to 1 to enable sending of email Notifications
intRRDToolDBEnabled = 0                 # set to 1 to enable saving records to RRDTool  
intRRDToolGraphsEnabled = 0             # set to 1 to enable generation of statistical graphs

# Used for pulling local weather conditions from OpenWeatherMap
strAPIKey = "d3ea3f72bbc523b946cd47c061d88b9f"
strDataFormat = "xml"                   # Options are json, xml, or html
strURL = "http://api.openweathermap.org/data/2.5/weather?us&APPID=" + strAPIKey + "&mode=" + strDataFormat

# Proxy configuration settings used for external weather API pull
strHTTPProxyType = "http"
strHTTPProxyURL = "http://64.102.255.47:80"

# MySQL DB connection information
strMySQLHost="127.0.0.1"
strMySQLUser="pi"
strMySQLPWD="labwatch"
strMySQLDB="labtemp"
strMySQLRecordTable="observations"

# Email Notification settions
strAlertEmail="bperciac@cisco.com"
strAlertEmailName="Temp Sensor Alert"
strAlertEmailSubject="Alert - Temperature Threshold Reached"
strAlarmEmail="bperciac@cisco.com"
strAlarmEmailName="Temp Sensor Alarm"
strAlarmEmailSubject="ALARM - High Temperature Threshold Reached"
strEmailSource="bperciac@cisco.com"
strEmailSourceName="Malvern Lab Sensor"
strSMTPServer="173.36.7.6"         # if you use a hostname, make sure it can be resolved!

# RRDTool attributes go here for charting and graphing
strRRDDatabase="/opt/labwatch/db/labwatch.rrd"
strHTMLHome="/var/www/html"
strGraphDirectory= strHTMLHome + "/graphs/"
strTemp1LineColor="#009933"
strTemp2LineColor="#0000FF"
strOutsideTempLineColor="#ff00ff"
strAlertLineColor="#ff6600"
strAlarmLineColor="#ff0000"
strGraphWidth="1000"
strGraphHeight="400"
strGraphWidthThumb="400"
strGraphHeightThumb="150"

#############################################################################
#                            Sensor settings                                #
#############################################################################
arrSensors = [
    {"id": "28-011612eb4aee",        # Use the 1W sensor HW id here, or ZIP if API call
        "active": 1,                 # If not 1 then sensor will be ignored
        "location_grp": 1,           # Group sensors in reports based on location ID
        "name": "Fishbowl Lab",
        "location": "Malvern",
        "type": "1w",                # use 1W for 1-wire devices, api foe external weather lookup
        "device": "28-011612eb4aee/w1_slave",
        "notifications": 0,          # set this to 1 if you want notifications sent when thresholds hit
        "contact_name": "Bob Perciaccante",
        "contact_email": "bperciac@cisco.com",
        "alert": 75,
        "alarm": 90},
    {"id": "28-011612eb4aef",
        "active": 0,  				# If not 1 then sensor will be ignored
        "location_grp": 1,			# Group sensors in reports based on location ID
        "name": "Service Provider Lab",
        "location": "Anchorage",
        "contact_name": "Bob Perciaccante",
        "contact_email": "bperciac@cisco.com",
        "type": "1w",                # use 1W for 1-wire devices, api foe external weather lookup
        "device": "28-011612eb4aef/w1_slave",
        "notifications": 0,          # set this to 1 if you want notifications sent when thresholds hit
        "alert": 75,
        "alarm": 90},
    {"id": "19355",
        "active": 1,  				          # If not 1 then sensor will be ignored
        "location_grp": 2,			             # Group sensors in reports based on location ID
        "name": "External Temp",
        "location": "Malvern, PA",
        "contact_name": "Bob Perciaccante",
        "contact_email": "bperciac@cisco.com",
        "type": "api",                    # use 1W for 1-wire devices, api foe external weather lookup
        "device": "w1_slave.t1xt",        # ignored if device type=api
        "notifications": 0,               # set this to 1 if you want notifications sent when thresholds hit
        "alert": 75,
        "alarm": 90}
        ]

def writelog(_EventType,_message):
    
    if intGenerateLog == 1:
        try: 
            logentry = strTimeNow + " " + strSourceDeviceId + " - " + str(_EventType) + ": " + _message
            outfile=open(strLogFile,"a")
            outfile.write((logentry))
            outfile.write("\n")
            outfile.close()
        except:
            return None
    
    return

def writedb(arrEvent,_index):
    sql = "INSERT INTO '%s' VALUES(null, null, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')" % \
          (strMySQLRecordTable,
           arrEvent[_index]["timenow"],
           arrEvent[_index]["srcDeviceID"],
           arrEvent[_index]["srcDeviceIP"],
           arrEvent[_index]["srcDeviceDesc"],
           arrEvent[_index]["sensorID"],
           arrEvent[_index]["sensorGroup"],
           arrEvent[_index]["sensorName"],
           arrEvent[_index]["sensorType"],
           arrEvent[_index]["sensorOwner"],
           arrEvent[_index]["sensorOwnerEmail"],
           arrEvent[_index]["sensorTemp"],
           arrEvent[_index]["sensorAlert"],
           arrEvent[_index]["sensorAlarm"]
           )
    #showme(arrEvent)
    #print(sql)
    return

def get_weather(_zipcode):
    # Connect to OpenWeatherMaps and get information for the defined ZIP code

    if intHTTPProxyRequired == 1:
        strCurrentConditions = requests.get(strURL + "&zip=" + _zipcode, proxies={strHTTPProxyType: strHTTPProxyURL})
    else:
        strCurrentConditions = requests.get(strURL + "&zip=" + _zipcode)

    # Download the results in XML format, and use BeautifulSoup to tokenize the results
    CurrentConditions = BeautifulSoup(strCurrentConditions.text, "html.parser")

    # Define the XML fields into arrays
    arrTemperature = CurrentConditions.temperature
    arrHumidity = CurrentConditions.humidity

    #  Error check - see if returned info is "none" then use to not crash script
    if CurrentConditions.temperature == None or CurrentConditions.humidity == None:
        return None
    else:
        # convert kelvin to F
        intCurrentTemp = round((float(arrTemperature['value'])*9/5.0)-459.67,1)
        return intCurrentTemp
		
def get_temp(sensor_device):
    #############################################################################
    # Function: get_temp                                                        # 
    # Function to xtract the temperature from any 1-Wire digital temp sensor    #
    # @param        sensor_device         location on in /sys/bus/w1 where the  #
    #                                     sensor reports temp (in degrees C)    #
    #       @return temp in *F as integer                                       #
    #############################################################################
    try:
            fileobj = open(sensor_device,'r') #read the file for this specific temp probe
            lines = fileobj.readlines()
            fileobj.close()
    except:
            return None

    readraw = lines[1][0:]					# read the second line, beginning to end
    temp_c = readraw.split("t=",1)[1]		# split everything from t= into temp_c
    temp_c = float(int(temp_c))				# temp_c is read as string, convert to int then float
    temp_c=temp_c/1000						# values is in 1,000's -- divide to bring to degree units
    temp_f=(temp_c * 9.0/5.0 + 32)
    temp = float(temp_f)
    temp = round(temp,1)
    return temp

def recordevent(arrEvent,_index):

    if intGenerateRecord == 1:
        record = "%s,'%s','%s','%s','%s','%s','%s','%s','%s','%s','%s',%s,%s,%s" % \
          (arrEvent[_index]["timenow"],
           arrEvent[_index]["srcDeviceID"],
           arrEvent[_index]["srcDeviceIP"],
           arrEvent[_index]["srcDeviceDesc"],
           arrEvent[_index]["sensorID"],
           arrEvent[_index]["sensorGroup"],
           arrEvent[_index]["sensorName"],
           arrEvent[_index]["sensorLocation"],
           arrEvent[_index]["sensorType"],
           arrEvent[_index]["sensorOwner"],
           arrEvent[_index]["sensorOwnerEmail"],
           arrEvent[_index]["sensorTemp"],
           arrEvent[_index]["sensorAlert"],
           arrEvent[_index]["sensorAlarm"]
           )
        outfile=open(strRecordFile,"a")
        outfile.write((record))
        outfile.write("\n")
        outfile.close()

    return

def notify(arrEvent,_index,t_EventType):
    
    if t_EventType == "ALERT":
        t_source = strEmailSourceName + " <" + strEmailSource +">\n"
        t_destination = strAlertEmailName + " <" + strAlertEmail + ">\n"
        t_subject = strAlertEmailSubject
        t_recipients = strAlertEmail
    if t_EventType == "ALARM":
        t_source = strEmailSourceName + " <" + strEmailSource +">\n"
        t_destination = strAlarmEmailName + " <" + strAlarmEmail + ">\n"
        t_recipients = strAlarmEmail
        t_subject = strAlarmEmailSubject 

    message = "From: " + t_source
    message = message + "To: " + t_destination
    message = message + "Subject: " + t_subject + " - " + arrEvent[_index]["sensorName"] + "\n\n"
    message = message + "The following event has triggered a temperature threshold\n\n"
    message = message + "Type of Event:     " + t_EventType + "\n"
    message = message + "Date of Event:     " + arrEvent[_index]["timenow"] + "\n"
    message = message + "Sensor Name:       " + arrEvent[_index]["sensorName"]  + "\n"
    message = message + "Sensor Location:   " + arrEvent[_index]["sensorLocation"] + "\n"
    message = message + "Alert Threshold:   " + str(arrEvent[_index]["sensorAlert"]) + "\n"
    message = message + "Alarm Threshold:   " + str(arrEvent[_index]["sensorAlarm"]) + "\n"
    message = message + "Current Temp:      " + str(arrEvent[_index]["sensorTemp"]) + "\n"
    message = message + "Contact of Record: " + arrEvent[_index]["sensorOwner"] + "(" + arrEvent[_index]["sensorOwnerEmail"] + ")\n\n"
    message = message + "Please reach out to the owner to determine root cause\n"
    #print(message)

    try:
        smtpObj = smtplib.SMTP(strSMTPServer)
        smtpObj.sendmail(strEmailSource, t_recipients, message)
        logmesg = "Email sent to " + t_recipients +" for sensor " + arrEvent[_index]["sensorName"] + ": Temp of " + str(arrEvent[_index]["sensorTemp"]) + " exceeds threshold"
        writelog("INFO",logmesg)
    except SMTPException:
       print ("Error: unable to send email")

    return


def showme(_arrEvent):
    # fundtion to consolidate display of eventt information before slicing it up for differnt functions
    for x in _arrEvent:
        print (x)
        for y in _arrEvent[x]:
            print (y,':',_arrEvent[x][y])

def main():
#############################################################################
#                              Main program                                 #
#############################################################################

    # go through the devices and gather the relevant data
    intSensorCount=0
    for (id) in arrSensors:
        if arrSensors[intSensorCount]["active"] == 1:

            # Check the device type from configured sensors, and get temp from device if a local
            # sensor, or look it up as an API call
            if arrSensors[intSensorCount]["type"] == "1w":
                
                # Pull the temperature from the devices or error if not available
                temp = get_temp(arrSensors[intSensorCount]["device"])
                if temp == None:
                    print("Sensor information for '" + arrSensors[intSensorCount]["name"] +"'(ID: " + arrSensors[intSensorCount]["id"] +") located at " + arrSensors[intSensorCount]["location"] +" is not available and is required for operation.")
                    print("Please check your confguration, or disable this sensor in the sensor configuration section of this script - Exiting")
                    logmesg = "Unable to access sensor information for '" + arrSensors[intSensorCount]["name"] +"'(ID: " + arrSensors[intSensorCount]["id"] +") located at " + arrSensors[intSensorCount]["location"]
                    writelog("FATAL",logmesg)
                    return
            # Get ZIP from device id (should never pull the zip more than once) and pull down the current temp        
            elif arrSensors[intSensorCount]["type"] == "api":
                temp = get_weather(arrSensors[intSensorCount]["id"])
                if temp == None:
                    logmesg = "Weather data not available. Check your URL or API keys - Exiting"
                    print(logmesg)
                    writelog("FATAL",logmesg)
                    return
            else:
                print("Invalid device type for'" + arrSensors[intSensorCount]["name"] +"'(ID: " + arrSensors[intSensorCount]["id"] +") located at " + arrSensors[intSensorCount]["location"] + " is not available and is required for operation.")
            
            # Put all the event information into a dictionary that can be shared with different functions            
            arrEvent = {intSensorCount:
                {"timenow": strTimeNow,
                    "srcDeviceID": strSourceDeviceId,
                    "srcDeviceIP": strSourceDeviceIP,
                    "srcDeviceLoc": strSourceDeviceLocation,
                    "srcDeviceDesc": strSourceDeviceDescription,
                    "sensorID": arrSensors[intSensorCount]["id"],
                    "sensorGroup": arrSensors[intSensorCount]["location_grp"],
                    "sensorName": arrSensors[intSensorCount]["name"],
                    "sensorLocation": arrSensors[intSensorCount]["location"],
                    "sensorType": arrSensors[intSensorCount]["type"],
                    "sensorOwner": arrSensors[intSensorCount]["contact_name"],
                    "sensorOwnerEmail": arrSensors[intSensorCount]["contact_email"],
                    "sensorTemp": temp,
                    "sensorAlert": arrSensors[intSensorCount]["alert"],
                    "sensorAlarm": arrSensors[intSensorCount]["alarm"]
                    }
                 }

            # Check to see if writing to a record file is enabled, as this will document measurements in the event
            # that the DB is down for some reason
            if intGenerateRecord == 1:
                recordevent(arrEvent,intSensorCount)
                if recordevent == None:
                    logmesg = "Unable to write to records file - Exiting"
                    print(logmesg)
                    writelog("FATAL",logmesg)
                    return

            # Check to see if writing to the database is enabled, and if so, pass the event information for submission
            if intGenerateDBEntry == 1:
                writedb(arrEvent,intSensorCount)

            # Check to see if the email notification is enabled, and send the event data
            if intEmailNotificationsEnabled == 1:
                if arrSensors[intSensorCount]["alert"] <= temp < arrSensors[intSensorCount]["alarm"]:
                    strEventType="ALERT"
                    if intEmailNotificationsEnabled ==1:
                        notify(arrEvent,intSensorCount,strEventType)
                elif temp >= arrSensors[intSensorCount]["alarm"]:
                    strEventType="ALARM"
                    if intEmailNotificationsEnabled ==1:
                        notify(arrEvent,intSensorCount,strEventType)
                else:
                    strEventType="EVENT"
                    
                    
                
            # feed event into to showme to display the info for testing purposes
            #showme(arrEvent)
            
        intSensorCount = intSensorCount + 1


    # Data output needs to be in the following format:
    # event time, source_device_id, source_device_ip, source_device_location, source_device_description,
    # id, group, name, location, type, owner, owner email, temp, alert, alarm


if __name__=="__main__":
        main()

# Calculate the time that the script ran and write to logfile
done = time.time()
elapsed = done - start
logmesg = "Script executed at " + strTimeNow + " and completed in " + str(round(elapsed,1)) +" seconds"
writelog("INFO",logmesg)