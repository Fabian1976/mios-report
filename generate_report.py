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
			# validate date
			import datetime
			datetime.datetime.strptime(self.report_start_date, '%d-%m-%Y')
		except:
			self.report_start_date = ''
		try:
			self.report_period = self.config.get('report', 'period')
			# Convert period to seconds
			import re, calendar, datetime
			match = re.match(r"([0-9]+)([a-z]+)", self.report_period, re.I)
			if match:
				period_items = match.groups()
			if self.report_start_date == '':
				day, month, year = map(int, datetime.date.strftime(datetime.datetime.today(), '%d-%m-%Y').split('-'))
			else:
				day, month, year = map(int, self.report_start_date.split('-'))
			seconds_in_day = 86400
			if period_items[1] == 'd':
				total_seconds = int(period_items[0]) * seconds_in_day
			elif period_items[1] == 'w':
				total_seconds = int(period_items[0]) * 7 * seconds_in_day
			elif period_items[1] == 'm':
				days_in_month = calendar.monthrange(year, month)[1]
				total_seconds = int(period_items[0]) * days_in_month * seconds_in_day
			elif period_items[1] == 'y':
				if calendar.isleap(year):
					total_seconds = int(period_items[0]) * 366 * seconds_in_day
				else:
					total_seconds = int(period_items[0]) * 365 * seconds_in_day
			self.report_period = total_seconds
		except:
			raise
			# Defaults to 1 week
			self.report_period = 604800
		try:
			self.report_graph_width = self.config.get('report', 'graph_width')
		except:
			self.report_graph_width = '1200'

		if self.report_start_date != '':
			self.report_end_date = datetime.date.strftime(datetime.datetime.strptime(self.report_start_date, "%d-%m-%Y") + datetime.timedelta(seconds=self.report_period), '%d-%m-%Y')
		else:
			self.report_end_date = datetime.date.strftime(datetime.datetime.today(), '%d-%m-%Y')
			self.report_start_date = datetime.date.strftime(datetime.datetime.strptime(self.report_end_date, "%d-%m-%Y") - datetime.timedelta(seconds=self.report_period), '%d-%m-%Y')

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
	# You can also give a starttime (&stime=yyyymmddhh24mm). Example: &stime=201310130000&period=86400, will start from 13-10-2013 and show 1 day (86400 seconds)
	day, month, year = config.report_start_date.split('-')
	stime = year + month + day + '000000'
	curl.setopt(curl.URL, z_url_graph + '?graphid=' + str(graphid) + '&width=' + config.report_graph_width + '&stime=' + stime + '&period=' + str(config.report_period))
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
		pg_connection = pg.connect("host='%s' port='%s' dbname='%s' user='%s' password='%s'" % (config.postgres_host, config.postgres_port, config.postgres_dbname, config.postgres_user, config.postgres_password))
	except Exception:
		print "Cannot connect to database"
		raise

	pg_cursor = pg_connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
	pg_cursor.execute("select * from mios_report where hostgroupid = %s order by hostname, graphname", (hostgroupid,))
	result = pg_cursor.fetchall()
	pg_cursor.close()
	pg_connection.close()
	return result

def generateReport(hostgroupname, data):
	import docx

	if config.report_template == '':
		existing_report = ''
	else:
		existing_report = config.mreport_home + '/templates/' + config.report_template
	if not existing_report:
		document = docx.newdocument()
	else:
		document = docx.opendocx(existing_report)
	relationships = docx.relationshiplist(existing_report)
	body = document.xpath('/w:document/w:body', namespaces=docx.nsprefixes)[0]
	body.append(docx.heading("MIOS rapportage " + hostgroupname, 1))
	hosts = []
	for record in data:
		if record['hostname'] not in hosts:
			hosts.append(record['hostname'])
	# Performance grafieken
	body.append(docx.heading("Performance grafieken", 2))
	for host in hosts:
		body.append(docx.heading(host, 3))
		for record in data:
			if record['hostname'] == host and record['graphtype'] == 'p':
				getGraph(record['graphid'])
				relationships, picpara = docx.picture(relationships, str(record['graphid']) + '.png', record['graphname'], 450)
				body.append(picpara)
				body.append(docx.caption(record['graphname']))
		body.append(docx.pagebreak(type='page', orient='portrait'))
	# Resource grafieken
	body.append(docx.heading("Resource grafieken", 2))
	for host in hosts:
		body.append(docx.heading(host, 3))
		for record in data:
			if record['hostname'] == host and record['graphtype'] == 'r':
				getGraph(record['graphid'])
				relationships, picpara = docx.picture(relationships, str(record['graphid']) + '.png', record['graphname'], 450)
				body.append(picpara)
				body.append(docx.caption(record['graphname']))
		body.append(docx.pagebreak(type='page', orient='portrait'))

	title = 'MIOS rapportage'
	subject = 'Maandelijkse performance en resources rapportage'
	creator = 'Vermont 24/7'
	keywords = ['MIOS', 'Rapportage', 'Vermont']
	coreprops = docx.coreproperties(title=title, subject=subject, creator=creator, keywords=keywords)
	wordrelationships = docx.wordrelationships(relationships)
	if not existing_report:
		appprops = docx.appproperties()
		contenttypes = docx.contenttypes()
		websettings = docx.websettings()
		docx.savedocx(document, coreprops, appprops, contenttypes, websettings, wordrelationships, config.report_name)
	else:
		import shutil, glob
		for file in glob.glob(mreport_home + '/lib/template/word/media/*'):
			shutil.copy2(file, mreport_home + '/tmp/word/media/')
		docx.savedocx(document, coreprops, wordrelationships=wordrelationships, output=config.report_name, template=existing_report)
	import glob # Unix style pathname pattern expansion
	# Remove files which are no longer necessary
	for file in glob.glob(mreport_home + '/*.png'):
		os.remove(file)
	for file in glob.glob(mreport_home + '/lib/template/word/media/*'):
		os.remove(file)
	for root, dirs, files in os.walk(mreport_home + '/tmp/', topdown=False):
		for name in files:
			os.remove(os.path.join(root, name))
		for name in dirs:
			os.rmdir(os.path.join(root, name))

def main():
	# get hostgroup
	hostgroupid, hostgroupname = selectHostgroup()
	os.system('clear')
	# get the hosts and their graphs from selected host group
	result = generateGraphs(hostgroupid)
	generateReport(hostgroupname, result)

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
