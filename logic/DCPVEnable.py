#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#Copyright (C) 2023 makischu

#DCPVEnable.py  Software implementation for interlock circuitry and 
# temperature controller, generating periodic enable triggers
# for a DC PV controller. Part of DimplexDHW_4PV project.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


#This program is partly based on this source, which is MIT licenced.
    # Very simple HTTP server in python for logging requests
    # Usage::
    #     ./server.py [<port>]
    # https://gist.github.com/mdonkers/63e115cc0c79b4f6b8b3a6b797e485c7

from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import requests 
import sys
import paho.mqtt.client as mqtt
import json
import signal 
import threading
import time


run = True

def handler_stop_signals(signum, frame):
    global run
    run = False

signal.signal(signal.SIGINT, handler_stop_signals)
signal.signal(signal.SIGTERM, handler_stop_signals)



clientStrom = mqtt.Client()         # for receiving DHW's temperature
reqSession = requests.session() 

shellyIP = "192.168.2.75"           # for interlock input. Shelly button action should be configured to call http://192.168.2.xx:8300/dhw/ok/0 when interlock goes low.
mqttIP   = "192.168.2.43"

topicdhw = "dev/dhw/telemetry"
topicsyr = "dev/syr/telemetry"
    
interlockOK    = False
T_water_C = 99
T_water_age = 99
P_water_bar = 0.0
P_water_age = 99
offTriggerCount = 0


#THE logic
def evalEnable():
    global interlockOK
    global T_water_C, P_water_bar
    global T_water_age, P_water_age
    DC_PV_Enable = interlockOK and T_water_C < 60 and T_water_age < 65 and P_water_bar > 2.0 and P_water_age < 65
    T_water_age = T_water_age + 1
    P_water_age = P_water_age + 1
    return DC_PV_Enable


triggerLast = True
triggerAge = 99
#actor
def triggerEnable(on):
    global clientStrom
    global triggerAge
    global triggerLast
    if triggerLast != on or triggerAge > 5:
        if on == True:
            command = "POWEROUT_ON"
        else:
            command = "POWEROUT_OFF"
        clientStrom.publish("dev/pvmeter/command", command)
        triggerLast = on
        triggerAge = 0 
    triggerAge = triggerAge + 1
        


###### Hilfsfunktion(en)
def fire_http_request(urlReq):
    responsetext = None
    error = 0
    try:
        response = reqSession.get(urlReq,timeout=(0.5,0.5))  #connect timeout and read timeout
        responsetext = response.text
    except:
        print("fire_http_request fail:", sys.exc_info()[0])
        error = 1
    #die response interessiert uns hier eigentlich gar nicht
    return error, responsetext


def evalShellyHTTPstatus(response):
    #Shelly1:    {"wifi_sta":{"connected":true,"ssid":"T..S","ip":"192.168.2.xx","rssi":-71},"cloud":{"enabled":false,"connected":false},"mqtt":{"connected":false},"time":"19:43","unixtime":1684777430,"serial":50,   "has_update":false,"mac":"E8DB84ACAFE2","cfg_changed_cnt":4,"actions_stats":{"skipped":0},"relays":[{"ison":false,"has_timer":false,"timer_started":0,"timer_duration":0,"timer_remaining":0,"source":"http"}],                  "meters":[{"power":0.00,"is_valid":true}],                                                                                       "inputs":[{"input":1,"event":"","event_cnt":2}],"ext_sensors":{},"ext_temperature":{},"ext_humidity":{},                                                                                            "update":{"status":"unknown","has_update":false,"new_version":"","old_version":"20221027-091427/v1.12.1-ga9117d3"},"ram_total":51688,"ram_free":41000,"fs_size":233681,"fs_free":150098,"uptime":1115391}
    #ShellyPlug: {"wifi_sta":{"connected":true,"ssid":"T..S","ip":"192.168.2.xx","rssi":-65},"cloud":{"enabled":false,"connected":false},"mqtt":{"connected":false},"time":"19:46","unixtime":1684784790,"serial":16312,"has_update":false,"mac":"F4CFA26CC502","cfg_changed_cnt":0,"actions_stats":{"skipped":0},"relays":[{"ison":false,"has_timer":false,"timer_started":0,"timer_duration":0,"timer_remaining":0,"overpower":false,"source":"http"}],"meters":[{"power":0.00,"overpower":0.00,"is_valid":true,"timestamp":1684784790,"counters":[0.000, 0.000, 0.000],"total":9851}],                                                                                                                                                                                                     "update":{"status":"unknown","has_update":false,"new_version":"","old_version":"20200827-070415/v1.8.3@4a8bc427"},"ram_total":51096,"ram_free":40464,"fs_size":233681,"fs_free":162899,"uptime":977873}
    #Shelly1PM:  {"wifi_sta":{"connected":true,"ssid":"T..S","ip":"192.168.2.xx","rssi":-58},"cloud":{"enabled":false,"connected":false},"mqtt":{"connected":false},"time":"19:49","unixtime":1684784990,"serial":9716, "has_update":false,"mac":"A4CF12F3F149","cfg_changed_cnt":0,"actions_stats":{"skipped":0},"relays":[{"ison":false,"has_timer":false,"timer_started":0,"timer_duration":0,"timer_remaining":0,"overpower":false,"source":"http"}],"meters":[{"power":0.00,"overpower":0.00,"is_valid":true,"timestamp":1684784990,"counters":[0.000, 0.000, 0.000],"total":46111}],"inputs":[{"input":0,"event":"","event_cnt":0}],"ext_sensors":{},"ext_temperature":{},"ext_humidity":{},"temperature":38.80,"overtemperature":false,"tmp":{"tC":38.80,"tF":101.85, "is_valid":true},"update":{"status":"unknown","has_update":false,"new_version":"","old_version":"20200827-070450/v1.8.3@4a8bc427"},"ram_total":50712,"ram_free":39576,"fs_size":233681,"fs_free":149094,"uptime":12366526}
    
    data = json.loads(response)
    relayState = None
    if "relays" in data:
        data_relays = data["relays"];
        if len(data_relays)>0:
            data_relay0 = data_relays[0]
            if "ison" in data_relay0:
                relayState = data_relay0["ison"]
    
    meterPower = None
    meterTotal = None
    if "meters" in data:
        data_meters = data["meters"];
        if len(data_meters)>0:
            data_meter0 = data_meters[0]
            #if "is_valid" in data_meter0:   # is true for shelly1, which does not provide power, so this information is misleading.
            if "is_valid" in data_meter0 and "power" in data_meter0 and "total" in data_meter0:
                if data_meter0["is_valid"] == True:
                    if "power" in data_meter0: 
                        meterPower = data_meter0["power"]
                    if "total" in data_meter0: 
                        meterTotal = data_meter0["total"]

    #https://shelly-api-docs.shelly.cloud/gen1/#shelly1-1pm-status
    # Note: Energy counters (in the counters array and total) will reset to 0 after reboot.
    #Total energy consumed by the attached electrical appliance in Watt-minute
    #wer auch immer sich die einheit ausgedacht hat aber gut dass die api dokumentiert ist.
        
    tempDegC = None
    if "tmp" in data:
        data_tmp = data["tmp"];
        if "tC" in data_tmp and "is_valid" in data_tmp:
            if data_tmp["is_valid"] == True:
                tempDegC = data_tmp["tC"]
                #print(tempDegC)
             
    inputState = None 
    if "inputs" in data:
        data_inputs = data["inputs"]
        if data_inputs:
            data_input = data_inputs[0]
            if "input" in data_input:
                inputState = data_input["input"]
     
    #nach .../pvs_EZ mit P_W, t_C, Ron
    output = {}
    if relayState != None:
        output["relay"] = (0,1)[relayState]
    if inputState != None:
        output["input"] = (0,1)[inputState]
    if meterPower != None:
        output["P_W"] = meterPower
    if tempDegC != None:
        output["t_C"] = tempDegC
    if meterTotal != None:
        output["E_Wm"]= meterTotal
    
    return output

        
def getShellyInput():
    global shellyIP
    global interlockOK 
    interlockOK = False
    urlCmd = "http://{i}/status".format(i=shellyIP)
    error, response = fire_http_request(urlCmd)
    #print(response)
    shellyStati = None
    if error == 0:
        shellyStati = evalShellyHTTPstatus(response)
              
    if shellyStati:
        message = json.dumps(shellyStati)
        #print(message)
        clientStrom.publish("dev/dhwshelly/telemetry", message)
        
        if "input" in shellyStati and shellyStati["input"]==1:
            interlockOK = True
         
        
        

def on_water_temperature(T_water):
    global T_water_C     
    global T_water_age   
    T_water_C = T_water
    T_water_age = 0

def on_water_pressure(P_water):
    global P_water_bar     
    global P_water_age   
    P_water_bar = P_water
    P_water_age = 0
    
#MQTT-Callback.
def on_message(client, userdata, message):
    global topicdhw, topicsyr
    if message.topic == topicdhw:
        messagestr = str(message.payload.decode())
        # ... "T_water_top[C]": "55", "T_water_bot[C]": "48", ...
        data = json.loads(messagestr)
        T_key1 = "T_water_top[C]"
        T_key2 = "T_water_bot[C]"
        Tmax = 99
        if T_key1 in data and T_key2 in data:
            T1 = data[T_key1]
            T2 = data[T_key2]
            try:
                T1=int(T1)
                T2=int(T2)
                Tmax = max([T1,T2])
            except:
                pass
        on_water_temperature(Tmax)
    elif message.topic == topicsyr:
        messagestr = str(message.payload.decode())
        #print(messagestr) { ... , "ValveStatus":"20" ,  ...  "Pressure[bar]":"4.7" }
        data = json.loads(messagestr)
        key_s = "ValveStatus"
        key_p = "Pressure[bar]"
        s_status = "xx"
        pressure = 0.0
        if key_s in data and key_p in data: #value status is not delivered every second, pressure is. 
            s_status   = data[key_s]
            s_pressure = data[key_p]
            try:
                pressure=float(s_pressure)
            except:
                pass
            if s_status != "20": #pressure is measured on value input side, so only valid on output side if value is open.
                pressure = 0.0
            on_water_pressure(pressure)
    
    

# wenn ein kommando per http reinkam... z.B. "/pvs/EZ/da"
def rcvd_http_get(path,ip):
    global interlockOK
    global offTriggerCount
    parts = path.split("/")
    #http://x:y/dhw/ok/1
    #http://x:y/dhw/ok/0
    if len(parts) >3 and parts[1] == "dhw" and parts[2] == "ok":
        stat = 1 if parts[3]=="1" else 0;
        interlockOK = stat == 1
        if not interlockOK:
            triggerEnable(False)
            offTriggerCount = offTriggerCount + 1
        

class S(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        #logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        self._set_response()
        self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))
        rcvd_http_get(str(self.path),self.client_address[0])

    def do_POST(self):
        content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
        post_data = self.rfile.read(content_length) # <--- Gets the data itself
        logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
                str(self.path), str(self.headers), post_data.decode('utf-8'))

        self._set_response()
        self.wfile.write("POST request for {}".format(self.path).encode('utf-8'))



httpdserver = None
httpdthread = None

#https://stackoverflow.com/questions/268629/how-to-stop-basehttpserver-serve-forever-in-a-basehttprequesthandler-subclass
class StoppableHTTPServer(HTTPServer):
    def run(self):
        global run
        try:
            while run:
                self.handle_request()
        except KeyboardInterrupt:
            logging.info('httpd interrupted...') #never called?
            pass
        finally:
            # Clean-up server (close socket, etc.)
            self.server_close()
        logging.info('httpd run exiting...') 
        
def startHttp(server_class=HTTPServer, handler_class=S, port=8300):
    global httpdserver
    global httpdthread
    logging.info('Starting httpd...')
    server_address = ('', port)
    httpdserver = StoppableHTTPServer(server_address, handler_class)
    
    # Start processing requests
    httpdthread = threading.Thread(None, httpdserver.run)
    httpdthread.start()

        
def stopHttp():
    global httpdserver
    global httpdthread
    logging.info('Stopping httpd...')
    dummyrequest = "http://localhost:{p}/shutdown".format(p=httpdserver.server_port)
    fire_http_request(dummyrequest)
    httpdthread.join()
    logging.info('Stopped httpd...')
    
    
    
    
def startMqtt():
    global clientStrom, topicdhw, topicsyr
    logging.info('Starting mqtt...')
    clientStrom.on_message = on_message;
    clientStrom.connect(mqttIP, 1883, 60)
    clientStrom.loop_start()
    clientStrom.subscribe(topicdhw)
    clientStrom.subscribe(topicsyr)
    
def stopMqtt():
    global clientStrom
    logging.info('Stopping mqtt...\n')
    clientStrom.loop_stop()
    
    

if __name__ == '__main__':
    from sys import argv
    
    logging.basicConfig(level=logging.INFO)
    
    startMqtt()
    if len(argv) == 2:
        startHttp(port=int(argv[1]))
    else:
        startHttp()
        
    while run:
        time.sleep(1.0 - (time.time() % 1.0))
        getShellyInput()
        DC_PV_Enable = evalEnable()
        triggerEnable(DC_PV_Enable)
        status = {"interlockOK":interlockOK, "T_water_C":T_water_C, "T_water_age":T_water_age, "offTriggerCount":offTriggerCount, "P_water_bar":P_water_bar, "P_water_age":P_water_age}
        clientStrom.publish("dev/dhwsrv/telemetry", json.dumps(status))

    stopHttp()
    stopMqtt()
