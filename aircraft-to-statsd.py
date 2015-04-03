#!/usr/bin/python
#
# Dan Silvers - github@silvers.net


# Seconds between stats submissions. 10 seconds seems to work nicely.
INTERVAL = 10

# Your statsd hostname.
STATSD_HOST = "127.0.0.1"

"""
# aircraft-to-statsd.py
#
# Send dump1090's aircraft.json data to statsd. This file contains the number of decoded messages
# along with information about each and every airplane that dump1090 is able to hear.
#
# This script creates a new thread every 10 seconds (or whatever you set in INTERVAL above), then reads
# from the aircraft.json file, sending the data to statsd.
#
#
#
{ "now" : 1428032255.8,
  "messages" : 36354113,
  "aircraft" : [
    {"hex":"c07bbe","flight":"WJA584  ","lat":46.006692,"lon":-92.464371,"nucp":6,"seen_pos":0.2,"altitude":37000,"vert_rate":0,"track":108,"speed":494,"messages":22,"seen":0.2,"rssi":-29.6},
    {"hex":"a66c99","squawk":"5361","altitude":5875,"messages":425,"seen":0.1,"rssi":-16.4},
    {"hex":"a51d90","squawk":"6261","flight":"FDX1683 ","lat":42.988495,"lon":-87.817298,"nucp":0,"seen_pos":1.3,"altitude":4125,"vert_rate":1856,"messages":515,"seen":0.0,"rssi":-12.4},
   ....
  ]
}
"""

import os
import sys
import time
import threading
import json
from statsd import StatsClient


def send_stats(last_timestamp, last_message_count, json_filename):
	with open(json_filename) as data_file:
		data = json.load(data_file)

	current_timestamp = data["now"]
	current_message_count = data["messages"]

	secs = False
	msgs = False

	if last_timestamp is False:
		print "Starting up, first pass...."
	elif current_message_count < last_message_count:
		print "Looks like dump1090 restarted, message count reset (%d)" % current_message_count
	else:
		secs = current_timestamp - last_timestamp
		msgs = current_message_count - last_message_count
		
		print "{0} sec\t{1} messages\t{2} messages per sec avg".format(secs, msgs, (msgs / secs))

	last_timestamp = current_timestamp
	last_message_count = current_message_count
	threading.Timer(INTERVAL, send_stats, [last_timestamp, last_message_count, json_filename]).start()

	aircrafts_5s = []
	aircrafts_10s = []
	aircrafts_30s = []
	aircrafts_60s = []

	for aircraft in data["aircraft"]:
		if aircraft["seen"] < 5:
			aircrafts_5s.append(aircraft["hex"])
		if aircraft["seen"] < 10:
			aircrafts_10s.append(aircraft["hex"])
		if aircraft["seen"] < 30:
			aircrafts_30s.append(aircraft["hex"])
		if aircraft["seen"] < 60:
			aircrafts_60s.append(aircraft["hex"])

	print "\t5s:{0}\t10s:{1}\t30s:{2}\t60s:{3}".format(len(aircrafts_5s), len(aircrafts_10s), len(aircrafts_30s), len(aircrafts_60s))

	radio_name = sys.argv[1]

	if secs:
		client = StatsClient(STATSD_HOST)
		client.incr("radios.%s.message_rate" % radio_name, msgs)

		pipe = client.pipeline()
		c = 0
		max_msg_size = 20
		for hex in aircrafts_10s:
			pipe.set("radios.%s.aircraft" % radio_name, hex)
			c = c + 1
			if c == max_msg_size:
				pipe.send()
				c = 0
		if c != max_msg_size:
			pipe.send()



if __name__ == "__main__":
        try:
                json_filename = sys.argv[2]
        except IndexError:
                print "Usage: aircraft-statsd.py <radio description for statsd> <path to aircraft.json>"
                sys.exit(1)
        if not os.path.isfile(json_filename):
                print "File does not appear to exist: %s" % json_filename
                sys.exit(1)
        if not os.access(json_filename, os.R_OK):
                print "Unable to read file, permission denied: %s" % json_filename
                sys.exit(1)

	send_stats(False, False, json_filename)
