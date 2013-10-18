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

def getHosts(hostgroupid):
	hosts = {}
	for host in zapi.host.get({ "output": "extend", "groupids" : hostgroupid }):
		hosts[host['name']] = (host['hostid'], getGraphs(host['hostid']))
	return hosts

def getGraphs(hostid):
	graphs = {}
	selected = 0
	for graph in zapi.graph.get({ "output": "extend", "hostids":hostid }):
		graphs[graph['name']] = (graph['graphid'], selected)
	return graphs

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
	
def runmenu(menu, parent):

	h = curses.color_pair(1) #h is the coloring for a highlighted menu option
	n = curses.A_NORMAL #n is the coloring for a non highlighted menu option

	# work out what text to display as the last menu option
	if parent is None:
		lastoption = "Klaar met grafieken aanvinken!"
	else:
		lastoption = "Terug naar menu %s" % parent['title']

	optioncount = len(menu['options']) # how many options in this menu

	pos=0 #pos is the zero-based index of the hightlighted menu option.  Every time runmenu is called, position returns to 0, when runmenu ends the position is returned and tells the program what option has been selected
	oldpos=None # used to prevent the screen being redrawn every time
	x = None #control for while loop, let's you scroll through options until return key is pressed then returns pos to program

	# Loop until return key is pressed
	while x !=ord('\n'):
		if pos != oldpos or x == 32:
			oldpos = pos
			screen.clear() #clears previous screen on key press and updates display based on pos
			screen.border(0)
			screen.addstr(2,2, menu['title'], curses.A_STANDOUT) # Title for this menu
			screen.addstr(4,2, menu['subtitle'], curses.A_BOLD) #Subtitle for this menu

			# Display all the menu items, showing the 'pos' item highlighted
			for index in range(optioncount):
				textstyle = n
				if pos==index:
					textstyle = h
				if 'graphid' in menu['options'][index]:
					if menu['options'][index]['selected'] == 1:
						check = '[*]'
					else:
						check = '[ ]'
					screen.addstr(5+index,4, "%-50s %s" % (menu['options'][index]['title'], check), textstyle)
				else:
					screen.addstr(5+index,4, "%s" % menu['options'][index]['title'], textstyle)
			# Now display Exit/Return at bottom of menu
			textstyle = n
			if pos==optioncount:
				textstyle = h
#			screen.addstr(5+optioncount,4, "%d - %s" % (optioncount+1, lastoption), textstyle)
			screen.addstr(5+optioncount,4, "%s" % lastoption, textstyle)
			screen.refresh()
			# finished updating screen

		try:
			x = screen.getch() # Gets user input
		except KeyboardInterrupt: # Catch CTRL-C
			x = 0
			pass

		# What is user input?
		if x == 258: # down arrow
			if pos < optioncount:
				pos += 1
			else:
				pos = 0
		elif x == 259: # up arrow
			if pos > 0:
				pos += -1
			else:
				pos = optioncount
		elif x == 32:
			if 'graphid' in menu['options'][pos]:
				if menu['options'][pos]['selected'] == 0:
					menu['options'][pos]['selected'] = 1
				else:
					menu['options'][pos]['selected'] = 0
			screen.refresh()
		elif x != ord('\n'):
			curses.flash()

	# return index of the selected item
	return pos

def processmenu(menu, parent=None):
	optioncount = len(menu['options'])
	exitmenu = False
	while not exitmenu: #Loop until the user exits the menu
		getin = runmenu(menu, parent)
		if getin == optioncount:
			exitmenu = True
#		elif menu['options'][getin]['type'] == 'GRAPHID':
#			getGraph(menu['options'][getin]['graphid'])
		elif menu['options'][getin]['type'] == 'MENU':
			processmenu(menu['options'][getin], menu) # display the submenu

def doMenu(menu_data):
	import curses #curses is the interface for capturing key presses on the menu, os launches the files
	global screen
	screen = curses.initscr() #initializes a new window for capturing key presses
	curses.noecho() # Disables automatic echoing of key presses (prevents program from input each key twice)
	curses.cbreak() # Disables line buffering (runs each key as it is pressed rather than waiting for the return key to pressed)
	curses.start_color() # Lets you use colors when highlighting selected menu option
	screen.keypad(1) # Capture input from keypad

	# Change this to use different colors when highlighting
	curses.init_pair(1,curses.COLOR_BLACK, curses.COLOR_WHITE) # Sets up color pair #1, it does black text with white background

	processmenu(menu_data)
	curses.endwin() #VITAL!  This closes out the menu system and returns you to the bash prompt.

def checkGraphs(hostgroupid, hostgroupnaam, menu_data):
	any_graphs = 0
	num_hosts = len(menu_data['options'])
	print "Groep '%s':" % hostgroupnaam
	for host in range(num_hosts):
		print '\t%s' % menu_data['options'][host]['title']
		num_graphs = len(menu_data['options'][host]['options'])
		selected_graphs_host = 0
		for graph in range(num_graphs):
			if menu_data['options'][host]['options'][graph]['selected'] == 1:
				selected_graphs_host += 1
		if selected_graphs_host > 0:
			any_graphs = 1
			for graph in range(num_graphs):
				if menu_data['options'][host]['options'][graph]['selected'] == 1:
					print "\t\t%s" % menu_data['options'][host]['options'][graph]['title']
		else:
			print "\t\tGeen grafieken geselecteerd voor deze host"
	if any_graphs:
		antwoord = ""
		while antwoord not in ["ja", "Ja", "nee", "Nee"]:
			try:
				antwoord = str(raw_input('\nWil je deze grafieken in de database opslaan (LET OP: de oude instellingen voor deze groep worden overschreven door deze nieuwe)? (Ja/Nee): '))
			except KeyboardInterrupt: # Catch CTRL-C
				pass
		if antwoord in ["ja", "Ja"]:
			print "OK"
			storeGraphs(hostgroupid, hostgroupnaam, menu_data)
		else:
			print "Dan niet"
	else:
		print "\nGeen grafieken geselecteerd. Hoef niets te doen."

def storeGraphs(hostgroupid, hostgroupnaam, menu_data):
	try:
		import psycopg2
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
		print "Kon geen verbinding met de database maken"
		raise
	pg_cursor = pg_connection.cursor()

	num_hosts = len(menu_data['options'])
	pg_cursor.execute("delete from mios_report where hostgroupid = %s", (hostgroupid,))
	# do not commit! stay in same transaction so rollback will work if an error occurs
	for host in range(num_hosts):
		num_graphs = len(menu_data['options'][host]['options'])
		for graph in range(num_graphs):
			if menu_data['options'][host]['options'][graph]['selected'] == 1:
				try:
					pg_cursor.execute("insert into mios_report (hostgroupid, hostgroupname, hostid, hostname, graphid, graphname) values (%s, %s, %s, %s, %s, %s)", (hostgroupid, hostgroupnaam, menu_data['options'][host]['hostid'], menu_data['options'][host]['title'], menu_data['options'][host]['options'][graph]['graphid'], menu_data['options'][host]['options'][graph]['title']))
				except:
					print "\nNieuwe waardes NIET toegevoegd aan database. Er ging iets mis.\nDe transactie wordt terug gedraaid.\n"
					pg_connection.rollback()
					pg_cursor.close()
					pg_connection.close()
					raise
	pg_connection.commit()
	pg_cursor.close()
	pg_connection.close()

def main():
	# get host groups
	hostgroupid, hostgroupnaam = selectHostgroup()
	os.system('clear')
	print "De hosts en bijbehorende grafieken van groep '%s' worden opgehaald..." % hostgroupnaam
	# get the hosts and their graphs from selected host group
	hosts = getHosts(hostgroupid)

	# Menus bouwen
	menu = {'title': 'Host list', 'type': 'MENU', 'subtitle': 'Selecteer een host...'}
	menu_options = []
	for host in hosts:
		menu_hosts = {}
		menu_hosts['title'] = host
		menu_hosts['hostid'] = hosts[host][0]
		menu_hosts['type'] = 'MENU'
		menu_hosts['subtitle'] = 'Vink de grafieken aan die in het rapport meegenomen moeten worden...'
		graphs = hosts[host][1]
		host_options = []
		for graph in graphs:
			menu_graphs = {}
			menu_graphs['title'] = str(graph)
			menu_graphs['type'] = 'GRAPHID'
			menu_graphs['graphid'] = graphs[graph][0]
			menu_graphs['selected'] = graphs[graph][1]
			host_options.append(menu_graphs)
		menu_hosts['options'] = host_options
		menu_options.append(menu_hosts)
	menu['options'] = menu_options

	doMenu(menu)
	os.system('clear')
	checkGraphs(hostgroupid, hostgroupnaam, menu)

if  __name__ == "__main__":
	options, args = get_options()

	zapi = ZabbixAPI(server=options.server,log_level=0)

	try:
		zapi.login(options.username, options.password)
#		print "Zabbix API Version: %s" % zapi.api_version()
	except ZabbixAPIException, e:
		sys.stderr.write(str(e) + '\n')

	main()
