#!/usr/bin/python
__author__    = "Fabian van der Hoeven"
__copyright__ = "Copyright (C) 2013 Vermont 24x7"
__version__   = "2.3"

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
		hosts[host['name']] = (host['hostid'], getCheckItems(host['hostid']))
	return hosts

def getCheckItems(hostid):
	items = {}
	selected = '0'
#	for item in zapi.item.get({ "output": "extend",  "hostids":hostid, "search": { "name": "Check -*"}, "searchWildcardsEnabled":1 }):
	for item in zapi.item.get({ "output": "extend",  "hostids":hostid, "filter": { "valuemapid": "1"} }): # Valuemapid 1 = "Service state" (0 = down, 1 = up)
		items[item['name']] = (item['itemid'], selected)
	return items

def runmenu(menu, parent):

	h = curses.color_pair(1) #h is the coloring for a highlighted menu option
	n = curses.A_NORMAL #n is the coloring for a non highlighted menu option

	# work out what text to display as the last menu option
	if parent is None:
		lastoption = "Done selecting items!"
	else:
		lastoption = "Back to menu '%s'" % parent['title']

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
				if 'itemid' in menu['options'][index]:
					if menu['options'][index]['selected'] == '0':
						check = '[ ]'
					elif menu['options'][index]['selected'] == '1':
						check = '[*]'
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
		elif x == 32: # space
			if 'itemid' in menu['options'][pos]:
				if menu['options'][pos]['selected'] == '0':
					menu['options'][pos]['selected'] = '1'
				else:
					menu['options'][pos]['selected'] = '0'
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

def checkItems(hostgroupid, hostgroupname, menu_data):
	any_items = 0
	num_hosts = len(menu_data['options'])
	print "Hostgroup '%s':" % hostgroupname
	for host in range(num_hosts):
		print '\t%s' % menu_data['options'][host]['title']
		num_items = len(menu_data['options'][host]['options'])
		selected_items_host = 0
		for item in range(num_items):
			if menu_data['options'][host]['options'][item]['selected'] != '0':
				selected_items_host += 1
		if selected_items_host > 0:
			any_items = 1
			for item in range(num_items):
				if menu_data['options'][host]['options'][item]['selected'] != '0':
					print "\t\t%s" % (menu_data['options'][host]['options'][item]['title'])
		else:
			print "\t\tNo items selected for this host"
	if any_items:
		antwoord = ""
		while antwoord not in ["yes", "Yes", "no", "No"]:
			try:
				antwoord = str(raw_input('\nDo you want to store these items in the database (BEWARE: the old setting for this hostgroup will be overwritten by these new ones)? (Yes/No): '))
			except KeyboardInterrupt: # Catch CTRL-C
				pass
		if antwoord in ["yes", "Yes"]:
			print "OK"
			storeItems(hostgroupid, hostgroupname, menu_data)
		else:
			print "Then not"
	else:
		print "\nNo items selected. Nothing to do."

def storeItems(hostgroupid, hostgroupname, menu_data):
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
		pg_connection = pg.connect("host='%s' port='%s' dbname='%s' user='%s' password='%s'" % (config.postgres_host, config.postgres_port, config.postgres_dbname, config.postgres_user, config.postgres_password))
	except Exception:
		print "Cannot connect to database"
		raise
	pg_cursor = pg_connection.cursor()

	num_hosts = len(menu_data['options'])
	pg_cursor.execute("delete from mios_report_uptime where hostgroupid = %s", (hostgroupid,))
	# do not commit! stay in same transaction so rollback will work if an error occurs
	for host in range(num_hosts):
		num_items = len(menu_data['options'][host]['options'])
		for item in range(num_items):
			if menu_data['options'][host]['options'][item]['selected'] != '0':
				try:
					pg_cursor.execute("insert into mios_report_uptime (hostgroupid, hostgroupname, hostid, hostname, itemid, itemname) values (%s, %s, %s, %s, %s, %s)", (hostgroupid, hostgroupname, menu_data['options'][host]['hostid'], menu_data['options'][host]['title'], menu_data['options'][host]['options'][item]['itemid'], menu_data['options'][host]['options'][item]['title']))
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
	print "The hosts and related items from group '%s' are being fetched..." % hostgroupname
	# get the hosts and their items from selected host group
	hosts = getHosts(hostgroupid)

	# Build the menus
	menu = {'title': 'Host list', 'type': 'MENU', 'subtitle': 'Select a host...'}
	menu_options = []
	for host in sorted(hosts.iterkeys()):
		menu_hosts = {}
		menu_hosts['title'] = host
		menu_hosts['hostid'] = hosts[host][0]
		menu_hosts['type'] = 'MENU'
		menu_hosts['subtitle'] = 'Select the items for the uptime graphs. Use <SPACE> to mark an item'
		items = hosts[host][1]
		host_options = []
		for item in sorted(items.iterkeys()):
			menu_items = {}
			menu_items['title'] = str(item)
			menu_items['type'] = 'ITEMID'
			menu_items['itemid'] = items[item][0]
			menu_items['selected'] = items[item][1]
			host_options.append(menu_items)
		menu_hosts['options'] = host_options
		menu_options.append(menu_hosts)
	menu['options'] = menu_options

	doMenu(menu)
	os.system('clear')
	checkItems(hostgroupid, hostgroupname, menu)

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
