#!/usr/bin/python
import optparse
import sys, os
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

class zHosts:
	def __init__(self, groupname):
		self.host_list = {}

		
def selectHostgroup():
	teller = 0
	hostgroups = {}
	for hostgroup in zapi.hostgroup.get({ "output": "extend", "filter": { "internal": "0"} }):
		teller+=1
		hostgroups[teller] = (hostgroup['name'], hostgroup['groupid'])
	print "Aanwezige hostgroups:"
	for hostgroup in hostgroups:
		print '\t%2d: %s' % (hostgroup, hostgroups[hostgroup][0])
	try:
		hostgroupnr = int(raw_input('Selecteer hostgroup: '))
		try:
			hostgroupid = hostgroups[hostgroupnr][1]
		except KeyError:
			print "Het opgegeven nummer komt niet overeen met een host group"
			hostgroupid = "Niet gevonden"
	except ValueError:
		print "Geen nummer opgegeven"
	return hostgroupid

def getHosts(hostgroupid):
	hosts = {}
	for host in zapi.host.get({ "output": "extend", "groupids" : hostgroupid }):
		hosts[host['name']] = (host['hostid'], getGraphs(host['hostid']))
	return hosts

def getGraphs(hostid):
	graphs = {}
	selected = False
	for graph in zapi.graph.get({ "output": "extend", "hostids":hostid }):
		graphs[graph['name']] = (graph['graphid'], selected)
	return graphs

def getGraph(graphid):
	import pycurl
	import StringIO
	c = pycurl.Curl()
	buffer = StringIO.StringIO()

	z_server = options.server
	z_user = options.username
	z_password = options.password
	z_url_index = z_server + 'index.php'
	z_url_graph = z_server + 'chart2.php'
	z_login_data = 'name=' + z_user + '&password=' + z_password + '&autologon=1&enter=Sign+in'
	filename_cookie = 'z_tmp_cookies_' + str(graphid) + '.txt'
	image_name = str(graphid) + '.png'
	# login and get cookie
	c.setopt(c.URL, z_url_index)
	c.setopt(c.POSTFIELDS, z_login_data)
	c.setopt(c.COOKIEJAR, filename_cookie)
	c.setopt(c.COOKIEFILE, filename_cookie)
	c.perform()
	# get graph image using cookie
	#Bij alleen het opgeven van de periode gaat de grafiek zolang terug. In dit geval dus 604800 seconden (1 week)
	#Men kan ook een start tijd opgeven (&stime=yyyymmddhh24mmss) Dus bijvoorbeeld: &stime=201310130000&period=86400 start vanaf 13-10-2013 en duurt 1 dag
	c.setopt(c.URL, z_url_graph + '?graphid=' + str(graphid) + '&width=1200&height=200&period=604800')
	c.setopt(c.WRITEFUNCTION, buffer.write)
	c.perform()
	f = open(image_name, 'wb')
	f.write(buffer.getvalue())
	f.close()
	
def runmenu(menu, parent):

	h = curses.color_pair(1) #h is the coloring for a highlighted menu option
	n = curses.A_NORMAL #n is the coloring for a non highlighted menu option

	# work out what text to display as the last menu option
	if parent is None:
		lastoption = "Exit"
	else:
		lastoption = "Return to %s menu" % parent['title']

	optioncount = len(menu['options']) # how many options in this menu

	pos=0 #pos is the zero-based index of the hightlighted menu option.  Every time runmenu is called, position returns to 0, when runmenu ends the position is returned and tells the program what option has been selected
	oldpos=None # used to prevent the screen being redrawn every time
	x = None #control for while loop, let's you scroll through options until return key is pressed then returns pos to program

	# Loop until return key is pressed
	while x !=ord('\n'):
		if pos != oldpos:
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
#				screen.addstr(5+index,4, "%d - %s" % (index+1, menu['options'][index]['title']), textstyle)
				screen.addstr(5+index,4, "%s" % menu['options'][index]['title'], textstyle)
			# Now display Exit/Return at bottom of menu
			textstyle = n
			if pos==optioncount:
				textstyle = h
#			screen.addstr(5+optioncount,4, "%d - %s" % (optioncount+1, lastoption), textstyle)
			screen.addstr(5+optioncount,4, "%s" % lastoption, textstyle)
			screen.refresh()
			# finished updating screen

		x = screen.getch() # Gets user input

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
		elif menu['options'][getin]['type'] == 'GRAPHID':
			getGraph(menu['options'][getin]['graphid'])
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

if  __name__ == "__main__":
	options, args = get_options()

	zapi = ZabbixAPI(server=options.server,log_level=0)

	try:
		zapi.login(options.username, options.password)
#		print "Zabbix API Version: %s" % zapi.api_version()
	except ZabbixAPIException, e:
		sys.stderr.write(str(e) + '\n')

	os.system('clear')
	# get host groups
	hostgroupid = selectHostgroup()
	# get hosts from selected host group
	hosts = getHosts(hostgroupid)

	# Menus bouwen
	menu = {'title': 'Host list', 'type': 'MENU', 'subtitle': 'Please select a host...'}
	menu_options = []
	for host in hosts:
		menu_hosts = {}
		menu_hosts['title'] = host
		menu_hosts['type'] = 'MENU'
		menu_hosts['subtitle'] = 'Select a graph...'
		graphs = hosts[host][1]
		host_options = []
		for graph in graphs:
			menu_graphs = {}
			menu_graphs['title'] = str(graph)
			menu_graphs['type'] = 'GRAPHID'
			menu_graphs['graphid'] = graphs[graph][0]
			host_options.append(menu_graphs)
		menu_hosts['options'] = host_options
		menu_options.append(menu_hosts)
	menu['options'] = menu_options

	doMenu(menu)
