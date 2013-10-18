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
		print "Aanwezige hostgroups:"
		for hostgroup in hostgroups:
			print '\t%2d: %s' % (hostgroup, hostgroups[hostgroup][0])
		try:
			hostgroupnr = int(raw_input('Selecteer hostgroup: '))
			try:
				hostgroupid = hostgroups[hostgroupnr][1]
				hostgroupnaam = hostgroups[hostgroupnr][0]
			except KeyError:
				print "\nTellen is niet je sterkste punt h%s!" % chr(232)
				hostgroupid = -1
				print "\nDruk op een toets om het nogmaals te proberen..."
				os.system('read -N 1 -s')
		except ValueError:
			print "\nEeuhm... Das geen nummer h%s!" % chr(232)
			hostgroupid = -1
			print "\nDruk op een toets om het nogmaals te proberen..."
			os.system('read -N 1 -s')
		except KeyboardInterrupt: # Catch CTRL-C
			pass
	return (hostgroupid, hostgroupnaam)

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
	# Als de filename van de cookie leeg gelaten wordt, slaat curl de cookie op in het geheugen
	# op deze manier hoeft de cookie achteraf niet verwijderd te worden. Als het script nu stop is de cookie ook weer weg
	z_filename_cookie = ''
	z_image_name = str(graphid) + '.png'
	# Inloggen en cookie ophalen
	curl.setopt(curl.URL, z_url_index)
	curl.setopt(curl.POSTFIELDS, z_login_data)
	curl.setopt(curl.COOKIEJAR, z_filename_cookie)
	curl.setopt(curl.COOKIEFILE, z_filename_cookie)
	curl.perform()
	# De graphs ophalen m.b.v. de cookie
	# Bij alleen het opgeven van de periode gaat de grafiek zolang terug. In dit geval dus 604800 seconden (1 week) vanaf de huidige datum/tijdstip
	# Men kan ook een start tijd opgeven (&stime=yyyymmddhh24mmss) Dus bijvoorbeeld: &stime=201310130000&period=86400 start vanaf 13-10-2013 en duurt 1 dag
	curl.setopt(curl.URL, z_url_graph + '?graphid=' + str(graphid) + '&width=1200&height=200&period=604800')
	curl.setopt(curl.WRITEFUNCTION, buffer.write)
	curl.perform()
	f = open(z_image_name, 'wb')
	f.write(buffer.getvalue())
	f.close()
	
def main():
	# get host groups
	hostgroupid, hostgroupnaam = selectHostgroup()
	os.system('clear')
	print "De hosts en bijbehorende grafieken van groep '%s' worden opgehaald..." % hostgroupnaam
	# get the hosts and their graphs from selected host group
#	hosts = getHosts(hostgroupid)

if  __name__ == "__main__":
	options, args = get_options()

	zapi = ZabbixAPI(server=options.server,log_level=0)

	try:
		zapi.login(options.username, options.password)
#		print "Zabbix API Version: %s" % zapi.api_version()
	except ZabbixAPIException, e:
		sys.stderr.write(str(e) + '\n')

	main()
