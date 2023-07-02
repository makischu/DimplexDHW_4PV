#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#Copyright (C) 2023 makischu

#CircEnable.py  Enable logic for the circulation pump.
# Part of DimplexDHW_4PV project.

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

import logging
import requests 
import sys
import paho.mqtt.client as mqtt
import json
import signal 
import time


run = True

def handler_stop_signals(signum, frame):
    global run
    run = False

signal.signal(signal.SIGINT, handler_stop_signals)
signal.signal(signal.SIGTERM, handler_stop_signals)



clientStrom = mqtt.Client()         # for receiving DHW's temperature
reqSession = requests.session() 

shellyIP = "192.168.2.76"           # for pump enable output
mqttIP   = "192.168.2.43"

topicdhw  = "dev/dhw/telemetry"
topicpvme = "dev/pvmeter/energy"
    
T_water_C = 99
hwhp_idle = False
T_water_age = 99
P_dc_W = 0.0
P_dc_age = 99
offTriggerCount = 0


#THE logic
def evalEnable():
    global pumpOn
    global T_water_C, P_dc_W, hwhp_idle
    global T_water_age, P_dc_age
    Pump_Enable = T_water_C > 55 and T_water_age < 65 and P_dc_W > 150.0 and P_dc_age < 65 and hwhp_idle == True
    T_water_age = T_water_age + 1
    P_dc_age = P_dc_age + 1
    return Pump_Enable




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


triggerLastIn  = True
triggerLastOut = False
triggerOutAge = 99
triggerInStableSince = 0
#actor
def triggerEnable(on):
    global clientStrom
    global triggerLastIn, triggerLastOut, triggerOutAge, triggerInStableSince
    if triggerLastIn == on:
        triggerInStableSince += 1
    else:
        triggerLastIn = on 
        triggerInStableSince = 0
    if triggerInStableSince > 10:
        if (triggerLastOut != on and triggerOutAge > 30) or triggerOutAge > 900:
            urlCmd = "http://{i}/relay/0?turn={s}".format(i=shellyIP,s=("off","on")[on])
            fire_http_request(urlCmd)
            triggerLastOut = on
            triggerOutAge = 0 
    triggerOutAge += 1
        

        

def on_water_temperature(T_water, isIdle):
    global T_water_C , T_water_age ,hwhp_idle
    T_water_C = T_water
    hwhp_idle = isIdle
    T_water_age = 0

def on_pvdc_power(P_dc):
    global P_dc_W , P_dc_age 
    P_dc_W = P_dc
    P_dc_age = 0
    
#MQTT-Callback.
def on_message(client, userdata, message):
    global topicdhw, topicsyr
    if message.topic == topicdhw:
        messagestr = str(message.payload.decode())
        #print(messagestr) 
        # ... "T_water_top[C]": "55", "T_water_bot[C]": "48", ... "StatusCode": "8"
        data = json.loads(messagestr)
        T_key1 = "T_water_top[C]"
        T_key2 = "T_water_bot[C]"
        T_key3 = "StatusCode"
        T1 = T2 = T3 = isIdle = None
        if T_key1 in data and T_key2 in data and T_key3 in data:
            T1 = data[T_key1]
            T2 = data[T_key2]
            T3 = data[T_key3]
            try:
                T1=int(T1)
                T2=int(T2)
                isIdle = T3 == "8"
            except:
                pass
        on_water_temperature(T1, isIdle)
    elif message.topic == topicpvme:
        messagestr = str(message.payload.decode())
        #print(messagestr) 
        #{"P_DC[W]": "888.8", ... "outputon": "1", ...}
        data = json.loads(messagestr)
        key_p = "P_DC[W]"
        if  key_p in data:
            s_p_dc = data[key_p]
            p_dc = 0
            try:
                p_dc=float(s_p_dc)
            except:
                pass
            on_pvdc_power(p_dc)
    
    

    
    
def startMqtt():
    global clientStrom, topicdhw, topicpvme
    logging.info('Starting mqtt...')
    clientStrom.on_message = on_message;
    clientStrom.connect(mqttIP, 1883, 60)
    clientStrom.loop_start()
    clientStrom.subscribe(topicdhw)
    clientStrom.subscribe(topicpvme)
    
def stopMqtt():
    global clientStrom
    logging.info('Stopping mqtt...\n')
    clientStrom.loop_stop()
    
    

if __name__ == '__main__':
    
    logging.basicConfig(level=logging.INFO)
    
    startMqtt()
        
    while run:
        time.sleep(1.0 - (time.time() % 1.0))
        Pump_Enable = evalEnable()
        triggerEnable(Pump_Enable)
        status = {"pumpOnSoll":Pump_Enable, "T_water_C":T_water_C, "T_water_age":T_water_age, "P_dc_W":P_dc_W, "P_dc_age":P_dc_age, "triggerLastOut":triggerLastOut,"triggerOutAge":triggerOutAge , "hwhp_idle":hwhp_idle}
        clientStrom.publish("dev/dhwcrc/telemetry", json.dumps(status))

    stopMqtt()
