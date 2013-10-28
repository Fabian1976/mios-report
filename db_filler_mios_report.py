#!/usr/bin/python
__author__    = "Fabian van der Hoeven"
__copyright__ = "Copyright (C) 2013 Vermont 24x7"
__version__   = "1.0"

import ConfigParser
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

class Config:
	def __init__(self, conf_file):
		self.config = None
		self.zabbix_frontend = ''
		self.zabbix_user = ''
		self.zabbix_password = ''
		self.postgres_dbname = ''
		self.postgres_host = ''
		self.postgres_port = ''
		self.postgres_user = ''
		self.postgres_password = ''
		self.report_name = ''
		self.report_template = ''
		self.report_start_date = ''
		self.report_period = ''
		self.report_graph_width = ''
		try:
			self.mreport_home = os.environ['MREPORT_HOME']
		except:
			self.mreport_home = '/opt/mios/mios-report'

		self.conf_file = conf_file
		if not os.path.exists(self.conf_file):
			print "Can't open config file %s" % self.conf_file
			exit(1)

		self.config = ConfigParser.ConfigParser()
		self.config.read(self.conf_file)

	def parse(self):
		try:
			self.zabbix_frontend = self.config.get('common', 'zabbix_frontend')
		except:
			self.zabbix_frontend = 'localhost'
		try:
			self.zabbix_user = self.config.get('common', 'zabbix_user')
		except:
			self.zabbix_user = 'admin'
		try:
			self.zabbix_password = self.config.get('common', 'zabbix_password')
		except:
			self.zabbix_password = ''
		try:
			self.postgres_dbname = self.config.get('miosdb', 'dbname')
		except:
			self.postgres_dbname = 'postgres'
		try:
			self.postgres_host = self.config.get('miosdb', 'host')
		except:
			self.postgres_host = 'localhost'
		try:
			self.postgres_port = self.config.get('miosdb', 'port')
		except:
			self.portgres_post = '5432'
		try:
			self.postgres_user = self.config.get('miosdb', 'user')
		except:
			self.postgres_user = 'postgres'
		try:
			self.postgres_password = self.config.get('miosdb', 'password')
		except:
			self.postgres_password = 'postgres'
		try:
			self.report_name = self.config.get('report', 'name')
		except:
			self.report_name = 'Report.docx'
		try:
			self.report_template = self.config.get('report', 'template')
		except:
			self.report_template = ''
		try:
			self.report_start_date = self.config.get('report', 'start_date')
		except:
			self.report_start_date = ''
		try:
			self.report_period = self.config.get('report', 'period')
		except:
			self.report_period = '1m'
		try:
			self.report_graph_width = self.config.get('report', 'graph_width')
		except:
			self.report_graph_width = '1200'

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

def getHosts(hostgroupid):
	hosts = {}
	for host in zapi.host.get({ "output": "extend", "groupids" : hostgroupid }):
		hosts[host['name']] = (host['hostid'], getGraphs(host['hostid']))
	return hosts

def getGraphs(hostid):
	graphs = {}
	selected = '0'
	for graph in zapi.graph.get({ "output": "extend", "hostids":hostid }):
		graphs[graph['name']] = (graph['graphid'], selected)
	return graphs

def getGraph(graphid):
	import pycurl
	import StringIO
	curl = pycurl.Curl()
	buffer = StringIO.StringIO()

	z_server = config.zabbix_frontend
	z_user = config.zabbix_user
	z_password = config.zabbix_password
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
	# You can also give a starttime (&stime=yyyymmddhh24mmss). Example: &stime=20131013000000&period=86400, will start from 13-10-2013 and show 1 day (86400 seconds)
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
		lastoption = "Done selecting graphs!"
	else:
		lastoption = "Back to menu '%s'" % parent['title']

	optioncount = len(menu['options']) # how many options in this menu

	pos=0 #pos is the zero-based index of the hightlighted menu option.  Every time runmenu is called, position returns to 0, when runmenu ends the position is returned and tells the program what option has been selected
	oldpos=None # used to prevent the screen being redrawn every time
	x = None #control for while loop, let's you scroll through options until return key is pressed then returns pos to program

	# Loop until return key is pressed
	while x !=ord('\n'):
		if pos != oldpos or x == 112 or x == 114:
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
					if menu['options'][index]['selected'] == '0':
						check = '[ ]'
					elif menu['options'][index]['selected'] == 'p':
						check = '[p]'
					elif menu['options'][index]['selected'] == 'r':
						check = '[r]'
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
		elif x == 112: # p(erformance)
			if 'graphid' in menu['options'][pos]:
				if menu['options'][pos]['selected'] == 'p':
					menu['options'][pos]['selected'] = '0'
				else:
					menu['options'][pos]['selected'] = 'p'
			screen.refresh()
		elif x == 114: # r(esources)
			if 'graphid' in menu['options'][pos]:
				if menu['options'][pos]['selected'] == 'r':
					menu['options'][pos]['selected'] = '0'
				else:
					menu['options'][pos]['selected'] = 'r'
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

def checkGraphs(hostgroupid, hostgroupname, menu_data):
	any_graphs = 0
	num_hosts = len(menu_data['options'])
	print "Hostgroup '%s':" % hostgroupname
	for host in range(num_hosts):
		print '\t%s' % menu_data['options'][host]['title']
		num_graphs = len(menu_data['options'][host]['options'])
		selected_graphs_host = 0
		for graph in range(num_graphs):
			if menu_data['options'][host]['options'][graph]['selected'] != '0':
				selected_graphs_host += 1
		if selected_graphs_host > 0:
			any_graphs = 1
			for graph in range(num_graphs):
				if menu_data['options'][host]['options'][graph]['selected'] == 'p':
					graph_type = "Performance graph"
				elif menu_data['options'][host]['options'][graph]['selected'] == 'r':
					graph_type = "Resource graph"
				if menu_data['options'][host]['options'][graph]['selected'] != '0':
					print "\t\t%-18s: %s" % (graph_type, menu_data['options'][host]['options'][graph]['title'])
		else:
			print "\t\tNo graphs selected for this host"
	if any_graphs:
		antwoord = ""
		while antwoord not in ["yes", "Yes", "no", "No"]:
			try:
				antwoord = str(raw_input('\nDo you want to store these graphs in the database (BEWARE: the old setting for this hostgroup will be overwritten by these new ones)? (Yes/No): '))
			except KeyboardInterrupt: # Catch CTRL-C
				pass
		if antwoord in ["yes", "Yes"]:
			print "OK"
			storeGraphs(hostgroupid, hostgroupname, menu_data)
		else:
			print "Then not"
	else:
		print "\nNo graphs selected. Nothing to do."

def storeGraphs(hostgroupid, hostgroupname, menu_data):
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
		print "Cannot connect to database"
		raise
	pg_cursor = pg_connection.cursor()

	num_hosts = len(menu_data['options'])
	pg_cursor.execute("delete from mios_report where hostgroupid = %s", (hostgroupid,))
	# do not commit! stay in same transaction so rollback will work if an error occurs
	for host in range(num_hosts):
		num_graphs = len(menu_data['options'][host]['options'])
		for graph in range(num_graphs):
			if menu_data['options'][host]['options'][graph]['selected'] != '0':
				try:
					pg_cursor.execute("insert into mios_report (hostgroupid, hostgroupname, hostid, hostname, graphid, graphname, graphtype) values (%s, %s, %s, %s, %s, %s, %s)", (hostgroupid, hostgroupname, menu_data['options'][host]['hostid'], menu_data['options'][host]['title'], menu_data['options'][host]['options'][graph]['graphid'], menu_data['options'][host]['options'][graph]['title'], menu_data['options'][host]['options'][graph]['selected']))
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
	hostgroupid, hostgroupname = selectHostgroup()
	os.system('clear')
	print "The hosts and related graphs from group '%s' are being fetched..." % hostgroupname
	# get the hosts and their graphs from selected host group
	hosts = getHosts(hostgroupid)

	# Build the menus
	menu = {'title': 'Host list', 'type': 'MENU', 'subtitle': 'Select a host...'}
	menu_options = []
	for host in sorted(hosts.iterkeys()):
		menu_hosts = {}
		menu_hosts['title'] = host
		menu_hosts['hostid'] = hosts[host][0]
		menu_hosts['type'] = 'MENU'
		menu_hosts['subtitle'] = 'Select the graphs for the report. Use "p" to mark as a performance graph and "r" for a resource graph'
		graphs = hosts[host][1]
		host_options = []
		for graph in sorted(graphs.iterkeys()):
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
	checkGraphs(hostgroupid, hostgroupname, menu)

if  __name__ == "__main__":
	global config
	try:
		mreport_home = os.environ['MREPORT_HOME']
	except:
		mreport_home = "/opt/mios/mios-report"

	config_file = mreport_home + '/conf/mios-report.conf'
	config = Config(config_file)
	config.parse()
	zapi = ZabbixAPI(server=config.zabbix_frontend,log_level=0)

	try:
		zapi.login(config.zabbix_user, config.zabbix_password)
#		print "Zabbix API Version: %s" % zapi.api_version()
	except ZabbixAPIException, e:
		sys.stderr.write(str(e) + '\n')

	main()
