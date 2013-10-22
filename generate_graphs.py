#!/usr/bin/python
import optparse
import sys, os
import time
import traceback
from getpass import getpass
# Add mios-report LIB to path
try:
        mreport_home = os.environ['MREPORT_HOME']
except:
        mreport_home = "/opt/mios/mios-report"
sys.path.append(mreport_home + '/lib')

from zabbix_api import ZabbixAPI, ZabbixAPIException

import curses, os #curses is the interface for capturing key presses on the menu, os launches the files

def get_options():
	""" command-line options """

	usage = "usage: %prog [options]"
	OptionParser = optparse.OptionParser
	parser = OptionParser(usage)

	parser.add_option("-s", "--server", action="store", type="string", dest="server", help="Zabbix Server URL (REQUIRED)")
	parser.add_option("-u", "--username", action="store", type="string", dest="username", help="Username (Will prompt if not given)")
	parser.add_option("-p", "--password", action="store", type="string", dest="password", help="Password (Will prompt if not given)")

	options, args = parser.parse_args()

	if not options.server:
		show_help(parser)

	if not options.username:
		options.username = raw_input('Username: ')

	if not options.password:
		options.password = getpass()

	# apply clue to user...
	if not options.username and not options.password:
		show_help(parser)

	return options, args

def show_help(p):
	p.print_help()
	print "NOTE: Zabbix 1.8.0 doesn't check LDAP when authenticating."
	sys.exit(-1)

def errmsg(msg):
	sys.stderr.write(msg + "\n")
	sys.exit(-1)

def selectHostgroup():
	teller = 0
	hostgroups = {}
	for hostgroup in zapi.hostgroup.get({ "output": "extend", "filter": { "internal": "0"} }):
		teller+=1
		hostgroups[teller] = (hostgroup['name'], hostgroup['groupid'])
	hostgroupid = -1
	while hostgroupid == -1:
		os.system('clear')
		print "Hostgroups:"
		for hostgroup in hostgroups:
			print '\t%2d: %s' % (hostgroup, hostgroups[hostgroup][0])
		try:
			hostgroupnr = int(raw_input('Select hostgroup: '))
			try:
				hostgroupid = hostgroups[hostgroupnr][1]
				hostgroupname = hostgroups[hostgroupnr][0]
			except KeyError:
				print "\nCounting is not your geatest asset!"
				hostgroupid = -1
				print "\nPress a key to try again..."
				os.system('read -N 1 -s')
		except ValueError:
			print "\nEeuhm... I don't think that's a number!"
			hostgroupid = -1
			print "\nPress a key to try again..."
			os.system('read -N 1 -s')
		except KeyboardInterrupt: # Catch CTRL-C
			pass
	return (hostgroupid, hostgroupname)

def getGraph(graphid):
	import pycurl
	import StringIO
	curl = pycurl.Curl()
	buffer = StringIO.StringIO()

	z_server = options.server
	z_user = options.username
	z_password = options.password
	z_url_index = z_server + 'index.php'
	z_url_graph = z_server + 'chart2.php'
	z_login_data = 'name=' + z_user + '&password=' + z_password + '&autologon=1&enter=Sign+in'
	# When we leave the filename of the cookie empty, curl stores the cookie in memory
	# so now the cookie doesn't have to be removed after usage. When the script finishes, the cookie is also gone
	z_filename_cookie = ''
	z_image_name = str(graphid) + '.png'
	# Log on to Zabbix and get session cookie
	curl.setopt(curl.URL, z_url_index)
	curl.setopt(curl.POSTFIELDS, z_login_data)
	curl.setopt(curl.COOKIEJAR, z_filename_cookie)
	curl.setopt(curl.COOKIEFILE, z_filename_cookie)
	curl.perform()
	# Retrieve graphs using cookie
	# By just giving a period the graph will be generated from today and "period" seconds ago. So a period of 604800 will be 1 week (in seconds)
	# You can also give a starttime (&stime=yyyymmddhh24mm). Example: &stime=201310130000&period=86400, will start from 13-10-2013 and show 1 day (86400 seconds)
	curl.setopt(curl.URL, z_url_graph + '?graphid=' + str(graphid) + '&width=1200&height=200&period=604800')
	curl.setopt(curl.WRITEFUNCTION, buffer.write)
	curl.perform()
	f = open(z_image_name, 'wb')
	f.write(buffer.getvalue())
	f.close()

def generateGraphs(hostgroupid):
	try:
		import psycopg2
		import psycopg2.extras # Necessary to generate query results as a dictionary
		pg = psycopg2
	except ImportError:
		print "Module psycopg2 is not installed, please install it!"
		raise
	except:
		print "Error while loading psycopg2 module!"
		raise
	try:
		pg_connection = pg.connect("host='%s' port='%s' dbname='%s' user='%s' password='%s'" % ("10.10.3.8", "9999", "tverdbp01", "mios", "K1HYC0haFBk9jvu71Bpf"))
	except Exception:
		print "Cannot connect to database"
		raise

	pg_cursor = pg_connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
	pg_cursor.execute("select * from mios_report where hostgroupid = %s", (hostgroupid,))
	graphs = pg_cursor.fetchall()
	pg_cursor.close()
	pg_connection.close()
	for graph in graphs:
		os.system('clear')
		print "Generate graph '%s' from host '%s'" % (graph['graphname'], graph['hostname'])
		getGraph(graph['graphid'])

def main():
	# get hostgroup
	hostgroupid, hostgroupname = selectHostgroup()
	os.system('clear')
	# get the hosts and their graphs from selected host group
	generateGraphs(hostgroupid)

if  __name__ == "__main__":
	options, args = get_options()

	zapi = ZabbixAPI(server=options.server,log_level=0)

	try:
		zapi.login(options.username, options.password)
#		print "Zabbix API Version: %s" % zapi.api_version()
	except ZabbixAPIException, e:
		sys.stderr.write(str(e) + '\n')

	main()
