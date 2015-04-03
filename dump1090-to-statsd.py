#!/usr/bin/python
#
# Dan Silvers - github@silvers.net

# Ignore stats files that are older than 60 seconds old
MAX_STATS_AGE = 60

"""
#
# dump1090-stats-to-statsd.py
#
# Requires the statsd python package, there are a bazillion ways to install it. I use:
#    sudo apt-get install python-pip
#    sudo pip install statsd
#
# Reads dump1090's JSON stats file (usually located at /run/dump1090-mutability/stats.json)
# and sends the 1 minute stats numbers to your statsd daemon.
#
# The stats.json file only writes once every minute, so just run this script once a minute from
# cron. Add the following to your crontab:
#
# */1 * * * * python /path/to/dump1090-to-statsd.py myadsb 127.0.0.1 /run/dump1090-mutability/stats.json >/dev/null 2>&1
#
# Once that is done, you should be able to login to your graphite installation to make some nice graphs.
#
"""

import sys
import os
import stat
import time
import json
from statsd import StatsClient
# Use pprint to debug the json you get from dump1090
from pprint import pprint

# Return the number of seconds since a file was last modified
def file_age_in_secs(path):
	return time.time() - os.stat(path)[stat.ST_MTIME]

STATSD_HOST = "127.0.0.1"
RADIO_NAME = "localhost"

# Send data to statsd
def send_radio_stats(n, s):
	client = StatsClient(STATSD_HOST)
	pipe = client.pipeline()

	pipe.gauge("radios.%s.accepted" % n, s["local"]["accepted"][0])
	pipe.gauge("radios.%s.accepted_corrected" % n, s["local"]["accepted"][1])
	# If you use the "aggressive" setting in dump1090-mutability, there may
	# be a third entry in the accepted set. Maybe you want to do something with that data?
	#pipe.gauge("radios.%s.accepted_corrected_2bit" % n, s["local"]["accepted"][2])

	pipe.gauge("radios.%s.bad" % n, s["local"]["bad"])
	pipe.gauge("radios.%s.blocks_dropped" % n, s["local"]["blocks_dropped"])
	pipe.gauge("radios.%s.blocks_processed" % n, s["local"]["blocks_processed"])
	pipe.gauge("radios.%s.modeac" % n, s["local"]["modeac"])
	pipe.gauge("radios.%s.modes" % n, s["local"]["modes"])
	pipe.gauge("radios.%s.strong_signals" % n, s["local"]["strong_signals"])
	pipe.gauge("radios.%s.unknown_icao" % n, s["local"]["unknown_icao"])
	pipe.gauge("radios.%s.cpr.airborne" % n, s["cpr"]["airborne"])
	pipe.gauge("radios.%s.cpr.filtered" % n, s["cpr"]["filtered"])
	pipe.send()
	pipe.gauge("radios.%s.cpr.global_bad" % n, s["cpr"]["global_bad"])
	pipe.gauge("radios.%s.cpr.global_ok" % n, s["cpr"]["global_ok"])
	pipe.gauge("radios.%s.cpr.global_range" % n, s["cpr"]["global_range"])
	pipe.gauge("radios.%s.cpr.global_skipped" % n, s["cpr"]["global_skipped"])
	pipe.gauge("radios.%s.cpr.global_speed" % n, s["cpr"]["global_speed"])
	pipe.gauge("radios.%s.cpr.local_aircraft_relative" % n, s["cpr"]["local_aircraft_relative"])
	pipe.gauge("radios.%s.cpr.local_ok" % n, s["cpr"]["local_ok"])
	pipe.gauge("radios.%s.cpr.local_range" % n, s["cpr"]["local_range"])
	pipe.gauge("radios.%s.cpr.local_receiver_relative" % n, s["cpr"]["local_receiver_relative"])
	pipe.gauge("radios.%s.cpr.local_skipped" % n, s["cpr"]["local_skipped"])
	pipe.send()
	pipe.gauge("radios.%s.cpr.local_speed" % n, s["cpr"]["local_speed"])
	pipe.gauge("radios.%s.cpr.surface" % n, s["cpr"]["surface"])
	pipe.gauge("radios.%s.messages" % n, s["messages"])
	pipe.gauge("radios.%s.tracks_all" % n, s["tracks"]["all"])
	pipe.gauge("radios.%s.tracks_single_message" % n, s["tracks"]["single_message"])
	pipe.timing("radios.%s.cpu.background" % n, s["cpu"]["background"])
	pipe.timing("radios.%s.cpu.demodulation" % n, s["cpu"]["demod"])
	pipe.timing("radios.%s.cpu.usb" % n, s["cpu"]["reader"])
	pipe.send()



if __name__ == "__main__":
	try:
		json_file = sys.argv[3]
	except IndexError:
		print "Usage: dump1090-to-statsd.py <statsd radio name prefix> <statsd host> <path to dump1090 stats.json file>"
		sys.exit(1)
	if not os.path.isfile(json_file):
		print "File does not appear to exist: %s" % json_file
		sys.exit(1)
	if not os.access(json_file, os.R_OK):
		print "Unable to read file, permission denied: %s" % json_file
		sys.exit(1)

	RADIO_NAME = sys.argv[1]
	STATSD_HOST = sys.argv[2]

	print "Parsing dump1090 stats.json file for changes: %s" % json_file
	age = file_age_in_secs(json_file)
	if age >= MAX_STATS_AGE:
		print "File is %d seconds old, not sending data" % age
		sys.exit(0)
	else:
		print "File is %d seconds old, looks like fresh data" % age


	with open(json_file) as data_file:
		data = json.load(data_file)

	d = data["last1min"]
	
	send_radio_stats(RADIO_NAME, d)

	sys.exit(0)
