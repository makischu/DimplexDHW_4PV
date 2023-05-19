#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#Copyright (C) 2023 makischu

#dhwmodbus2mqtt: Periodically poll Dimplex DHW and Phoenix EM357 
#via ModbusTCP-Converter and send formatted results per MQTT

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


# first tried pymodbustcp, but I failed to talk to multiple devices.
# conda install -c conda-forge pymodbustcp
#from pyModbusTCP.client import ModbusClient

#https://github.com/AdvancedClimateSystems/uModbus/
#https://anaconda.org/esrf-bcu/umodbus
#conda install -c esrf-bcu umodbus
#from umodbus import conf
from umodbus.client import tcp

#uses paho-mqtt. for anaconda/sypder:
#conda install -c conda-forge paho-mqtt 
import paho.mqtt.client as mqtt

import time
import datetime
import signal 
import socket
import json
import logging


modbus_host="192.168.2.53"
modbus_port=8234
modbussocket = socket.create_connection((modbus_host, modbus_port), timeout=1)
slave_id_phx = 5 
slave_id_dim = 2

mqtt_host = "192.168.2.43"
mqtt_port = 1883
clientStrom = mqtt.Client()
logging.info('Starting mqtt...')
clientStrom.connect(mqtt_host, mqtt_port, 60)
clientStrom.loop_start()

run = True

def handler_stop_signals(signum, frame):
    global run
    run = False

signal.signal(signal.SIGINT, handler_stop_signals)
signal.signal(signal.SIGTERM, handler_stop_signals)


#modbus knows 16bit values; registers are combined for higher resolution.
#u64 und s64 don't exist at python, but big (signed) integers
#phoenix's register descriptions are not intuitive, but this is how it works:
    
def reg_to_u64(reg_vals):
    res=None
    if len(reg_vals)==4:
        res = (reg_vals[0]<<48) + (reg_vals[1]<<32) + (reg_vals[2]<<16) + (reg_vals[3])
    return res

def reg_to_s64(reg_vals):
    res=reg_to_u64(reg_vals)
    if res:
        if(res & 0x8000000000000000):
            res=-0x10000000000000000 + res
    return res
    
def reg_to_u32(reg_vals):
    res=None
    if len(reg_vals)==2:
        res = (reg_vals[0]<<16) + (reg_vals[1])
    return res

#dimplex uses signed and unsigned values, but only 16 bit each
def reg_to_s16(reg_val):
    res=reg_val
    if(res & 0x8000):
        res=-0x10000 + res
    return res



def collectMeter_P():
    global modbussocket, slave_id_phx
    values={}
    try:
        message = tcp.read_holding_registers(slave_id=slave_id_phx, starting_address=0x0020, quantity=12)
        val = tcp.send_message(message, modbussocket)
        #val = c.read_holding_registers(0x0020, 12)
        #val = [0, 0, 1, 97, 0, 0, 0, 0, 0, 0, 0, 14977]
        P_L1_mW = reg_to_s64(val[0:4])
        P_L2_mW = reg_to_s64(val[4:8])
        P_L3_mW = reg_to_s64(val[8:12])
        
        values["P_L1[W]"] = "{x:.3f}".format(x=P_L1_mW/1000.0)
        values["P_L2[W]"] = "{x:.3f}".format(x=P_L2_mW/1000.0)
        values["P_L3[W]"] = "{x:.3f}".format(x=P_L3_mW/1000.0)
    except:
        values["P_L1[W]"] = "-"
        values["P_L2[W]"] = "-"
        values["P_L3[W]"] = "-"
        values["error"] = 1
    return values

def collectMeter_E():
    global modbussocket, slave_id_phx
    values={}
    try:
        message = tcp.read_holding_registers(slave_id=slave_id_phx, starting_address=0x0100, quantity=12)
        valE = tcp.send_message(message, modbussocket)
        #valE = c.read_holding_registers(0x0100, 12)
        #bei 34285 steht 3,43 im display als kwh
        #bei 110234 steht 11,03 im display. d.h. der teiler ist eher 10000 statt 1000 wie in der anleitung.
        E_L1_zWh = reg_to_u64(valE[0:4])
        E_L2_zWh = reg_to_u64(valE[4:8])
        E_L3_zWh = reg_to_u64(valE[8:12])
        
        values["E_L1[kWh]"] = "{x:.3f}".format(x=E_L1_zWh/10000.0)
        values["E_L2[kWh]"] = "{x:.3f}".format(x=E_L2_zWh/10000.0)
        values["E_L3[kWh]"] = "{x:.3f}".format(x=E_L3_zWh/10000.0)
    except:
        values["E_L1[kWh]"] = "-"
        values["E_L2[kWh]"] = "-"
        values["E_L3[kWh]"] = "-"
        values["error"] = 1
    return values
        
def collectMeter_U():
    global modbussocket, slave_id_phx
    values={}
    try:
        message = tcp.read_holding_registers(slave_id=slave_id_phx, starting_address=0xC558, quantity=6)
        valV = tcp.send_message(message, modbussocket)
        U_L1_hV = reg_to_u32(valV[0:2])
        U_L2_hV = reg_to_u32(valV[2:4])
        U_L3_hV = reg_to_u32(valV[4:6])
        
        values["U_L1[V]"] = "{x:.2f}".format(x=U_L1_hV/100.0)
        values["U_L2[V]"] = "{x:.2f}".format(x=U_L2_hV/100.0)
        values["U_L3[V]"] = "{x:.2f}".format(x=U_L3_hV/100.0)
    except:
        values["U_L1[V]"] = "-"
        values["U_L2[V]"] = "-"
        values["U_L3[V]"] = "-"
        values["error"] = 1
    return values

def collectMeter_f():
    global modbussocket, slave_id_phx
    values={}
    try:
        message = tcp.read_holding_registers(slave_id=slave_id_phx, starting_address=0x0050, quantity=2)
        valF = tcp.send_message(message, modbussocket)
        #valF = c.read_holding_registers(0x0050, 2)
        F_mHz = reg_to_u32(valF[0:2])
        
        values["f[Hz]"] = "{x:.3f}".format(x=F_mHz/1000.0)
    except:
        values["f[Hz]"] = "-"
        values["error"] = 1
    return values


def collectDimplexM():
    global modbussocket, slave_id_dim
    values={}
    try: 
        #adresses 0 to 7 and 25 also deliver some values, though not documented.
        message = tcp.read_input_registers(slave_id=slave_id_dim, starting_address=0, quantity=26)
        val = tcp.send_message(message, modbussocket)
        #[5, 0, 0, 161, 20, 27xx, 1, 0, 58, 58, 18, 20, 35, 25, 0, 0, 0, 0, 0, 8, 8, 503, 78, 75, 3, 357]
        #print(val)
        #val = modbusClientDimplex.read_input_registers(8, 2)
        
        values["T_water_top[C]"]    =  str(reg_to_s16(val[8]))
        values["T_water_bot[C]"]    =  str(reg_to_s16(val[9]))
        values["T_air_inlet[C]"]    =  str(reg_to_s16(val[10]))
        #values["Text_collector[C]"] =  str(reg_to_s16(val[11])) collector temperature (R13 only on models with additional heat exchanger and Sol selected as 2nd heat generator)
        #values["Twater_set[C]"]    =  str(reg_to_s16(val[12])) the current domestic hot water setpoint
        #values["T_defrost[C]"]      =  str(reg_to_s16(val[13])) defrost sensor (only on models with defrost)
        values["IO_P_VCHP"]         = str(val[1])+'_'+str(val[14])+str(val[15])+str(val[16])+str(val[17])
        values["P_line_est[W]"]     = str(val[18])  #calculated(!) power consumption of the device
        values["StatusCode"]        = str(val[19])
        values["ErrorCode"]         = str(val[20])
        
        # values["TBD0"] = str(val[0])
        # # values["TBD1"] = str(val[1]) solved: pv input.
        # values["TBD2"] = str(val[2])
        # # values["TBD3"] = str(val[3]) solved: software version
        # # values["TBD4"] = str(val[4]) solved: hardware version
        # # values["TBD5"] = str(val[5]) solved: serial number
        # values["TBD6"] = str(val[6])
        # values["TBD7"] = str(val[7])
        # values["TBD25"] = str(val[25])
    except:
        values["error"] = 1
    return values


#intermediate experiments
# t = time.time()            
# print(collectDimplex1())
# # print(collectMeter_P())
# # time.sleep(0.5)
# # print(collectDimplex1())
# # print(collectMeter_E())
# # print(collectMeter_U())
# # print(collectMeter_f())
# elapsed = time.time() -t
# print(elapsed) 


def publish2mqtt(devicename, d,t,tcollect,values):
    topic = "dev/{n}/telemetry".format(n=devicename)
            
    error=0
    if "error" in values:
        error = values["error"]
    tcollect_ms = int(tcollect * 1000.0)
    
    heads = { "src" : "dhwmodbus2mqtt", 
              "error" : str(error), 
              "d" : d , "t" : t ,
              "t_collect" : str(tcollect_ms) }
    
    row = {}
    row.update(heads)
    row.update(values)
    
    messageJson = json.dumps(row)

    #message = bytes(messageJson, "ascii", "backslashreplace")
    #if len(message) > 1500:
    #    print("too long")
    #sock.sendto(message, (UDP_IP, UDP_PORT))
   
    clientStrom.publish(topic, messageJson)
    
    #print(topic, messageJson)
    return



def collect_every_second(d,t):
    values = {}
    tstart = time.time()
    values = collectMeter_P()
    elapsed = time.time() -tstart
    publish2mqtt("phx",d,t,elapsed,values)
    return
    
def collect_every_minute(d,t):
    values = {}
    tstart = time.time()
    values.update(collectDimplexM())
    elapsed = time.time() -tstart
    publish2mqtt("dhw",d,t,elapsed,values)
    
    values = {}
    tstart = time.time()
    values.update(collectMeter_P())
    values.update(collectMeter_E())
    values.update(collectMeter_U())
    values.update(collectMeter_f())
    elapsed = time.time() -tstart
    publish2mqtt("phx",d,t,elapsed,values)
    return

def collect_every_day(d,t):
    return collect_every_minute(d,t)


dateLast = datetime.date(2000,1,1)

while run:
    #print ("run")
    mynow   = datetime.datetime.now()
    d = mynow.strftime("%Y-%m-%d")      #YYYY-MM-DD
    t = mynow.strftime("%H:%M:%S")      #HH:MM:SS
    mytoday = datetime.date.today()
    doflush = False
    if dateLast != mytoday:             #every day
        dateLast = mytoday
        collect_every_day(d,t)
    elif mynow.second % 60 == 0:        #every minute
        collect_every_minute(d,t)
        doflush = True
    else:                               #every second
        collect_every_second(d,t)

    #wait for next full second
    #print('.', end='')
    print('.', end='', flush=doflush)
    time.sleep(1.0 - (time.time() % 1.0))



clientStrom.loop_stop()
logging.info('Stopping mqtt...\n')

modbussocket.close()
