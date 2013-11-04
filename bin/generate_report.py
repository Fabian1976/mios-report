#!/usr/bin/python
__author__    = "Fabian van der Hoeven"
__copyright__ = "Copyright (C) 2013 Vermont 24x7"
__version__   = "2.2"

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
from GChartWrapper import *

import curses, os #curses is the interface for capturing key presses on the menu, os launches the files

postgres = None

class Config:
	def __init__(self, conf_file):
		self.config = None
		self.zabbix_frontend = ''
		self.zabbix_user = ''
		self.zabbix_password = ''
		self.postgres_dbname = ''
		self.postgres_dbs = {}
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
			postgres_host = self.config.get('miosdb', 'host')
		except:
			postgres_host = 'localhost'
		try:
			postgres_port = self.config.get('miosdb', 'port')
		except:
			postgres_port = '5432'
		try:
			postgres_user = self.config.get('miosdb', 'user')
		except:
			postgres_user = 'postgres'
		try:
			postgres_password = self.config.get('miosdb', 'password')
		except:
			postgres_password = 'postgres'
		self.postgres_dbs[self.postgres_dbname] = (postgres_host, postgres_port, postgres_user, postgres_password)
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

		try:
			self.email_sender = self.config.get('email', 'sender')
		except:
			from socket import gethostname
			self.email_sender = 'mios@' + gethostname()
		try:
			self.email_receiver = self.config.get('email','receiver')
		except:
			self.email_receiver = ''
		try:
			self.email_server = self.config.get('email', 'server')
		except:
			self.email_server = 'localhost'

class Postgres(object):

	def __init__(self, instances):

		self.postgres_support = 0
		self.connections      = []
		self.cursor           = []
		self.version          = []
		self.host             = []
		self.port             = []
		self.user             = []
		self.password         = []
		self.dbs              = []
		self.instances        = instances
		self.last_connect     = []
#		self.logger           = logging.getLogger(type(self).__name__)

		try:
			import psycopg2
			import psycopg2.extras
			self.psycopg2 = psycopg2
			self.psycopg2_extras = psycopg2.extras
			self.postgres_support = 1
			print("Successfully loaded psycopg2 module")
		except ImportError:
			print("Module psycopg2 is not installed, please install it!")
			raise
		except:
			print("Error while loading psycopg2 module!")
			raise

		if self.postgres_support == 0:
			return None

		for instance in instances:
			host, port, user, password = instances[instance]
			self.host.append(host)
			self.port.append(port)
			self.user.append(user)
			self.password.append(password)
			self.dbs.append(instance)
			self.connections.append(None)
			self.cursor.append(None)
			self.version.append('')
			indx = self.dbs.index(instance)
			self.last_connect.append(0)
			self.connect(indx)

	def connect(self, indx):

		while self.connections[indx] == None:
			try:
				self.connections[indx] = self.psycopg2.connect("host='%s' port='%s' dbname='%s' user='%s' password='%s'" % (self.host[indx], self.port[indx], self.dbs[indx], self.user[indx], self.password[indx]))
				print("Connection succesful")
				time.sleep(2)
			except Exception, e:
				print("Unable to connect to Postgres")
				print("PG: Additional information: %s" % e)
				print("Trying to reconnect in 10 seconds")
				time.sleep(10)
		self.cursor[indx]      = self.connections[indx].cursor(cursor_factory=self.psycopg2_extras.DictCursor)
		self.cursor[indx].execute('select version()')
		self.version[indx]     = self.cursor[indx].fetchone()
		self.last_connect      = time.time()
		print("Connect to Postgres version %s DB: %s" % (self.version[indx], self.dbs[indx]))

	def execute(self, db, query):

		if self.postgres_support == 0:
			print("Postgres not supported")
			return None

		if not db in self.dbs:
			return -1
		try:
			indx = self.dbs.index(db)
			try:
				self.cursor[indx].execute(query)
			except Exception, e:
				print("PG: Failed to execute query: %s" % query)
				print("PG: Additional info: %s" % e)
				return -1

			try:
				value = self.cursor[indx].fetchall()
			except Exception, e:
				print("PG: Failed to fetch resultset")
				print("PG: Additional info: %s" % e)
				return -1

#			print("indx: %d db: %s action: %s value: %s" % (indx, db, query, str(value)))
			return value
		except:
			print("Error in Postgres connection DB: %s" % db)
			raise
			return -2

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
			print '\t%2d: %s (hostgroupid: %s)' % (hostgroup, hostgroups[hostgroup][0], hostgroups[hostgroup][1])
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

def getHostgroupName(hostgroupid):
        teller = 0
	try:
		hostgroupname = zapi.hostgroup.get({ "output": "extend", "filter": { "groupid": hostgroupid} })[0]['name']
	except:
		hostgroupname = 0
        return hostgroupname

def checkHostgroup(hostgroupid):
	num_graphs_host = postgres.execute(config.postgres_dbname, "select count(*) from mios_report_graphs where hostgroupid = %s" % hostgroupid)
	num_items_host = postgres.execute(config.postgres_dbname, "select count(*) from mios_report_uptime where hostgroupid = %s" % hostgroupid)
	if int(num_graphs_host[0][0]) > 0:
		result = 1
	elif int(num_items_host[0][0]) > 0:
		result = 1
	else:
		result = 0
	return result

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

def getUptimeGraph(itemid):
	day, month, year = map(int, config.report_start_date.split('-'))

	start_epoch = time.mktime((year, month, day, 0, 0, 0, 0, 0, 0))
	end_epoch = start_epoch + config.report_period
	polling_total = postgres.execute(config.postgres_dbname, "select count(*) from zabbix.history_uint where itemid = %s and clock between %s and %s" % (itemid, start_epoch, end_epoch))[0][0]
	rows = postgres.execute(config.postgres_dbname, "select clock from zabbix.history_uint where itemid = %s and clock > %s and clock < %s and value = 0" % (itemid, start_epoch, end_epoch))
	polling_down_rows = []
	for row in rows:
		polling_down_rows.append(row[0])
	item_maintenance_rows = postgres.execute(config.postgres_dbname, "select start_date, (start_date + period) from zabbix.timeperiods\
	 inner join zabbix.maintenances_windows on maintenances_windows.timeperiodid = timeperiods.timeperiodid\
	 inner join zabbix.maintenances on maintenances.maintenanceid = maintenances_windows.maintenanceid\
	 inner join zabbix.maintenances_groups on maintenances_groups.maintenanceid = maintenances.maintenanceid\
	 inner join zabbix.groups on maintenances_groups.groupid = groups.groupid\
	 inner join zabbix.hosts_groups on hosts_groups.groupid = groups.groupid\
	 inner join zabbix.hosts on hosts_groups.hostid = hosts.hostid\
	 inner join zabbix.items on items.hostid = hosts.hostid\
	 where items.itemid = %s and timeperiods.start_date between %s and %s" % (itemid, start_epoch, end_epoch))
	polling_down_maintenance = []
	polling_down = list(polling_down_rows) # Make copy of list so that it can be edited without affecting original list (mutable), same as polling_down_rows[:]
	for clock in polling_down_rows:
		for mclock in item_maintenance_rows:
			if mclock[0] <= clock <= mclock[1]:
				# Is down clock between maintenance period?
				# Then add to down_maintenance and remove from down
				polling_down_maintenance.append(clock)
				polling_down.remove(clock)

	print "Polling items down and in maintenance    : %s" % len(polling_down_maintenance)
	print "Polling items down and NOT in maintenance: %s" % len(polling_down)
	print "Polling items UP                         : %s" % (polling_total - len(polling_down_maintenance) - len(polling_down))
	print "Start epoch      : ", start_epoch
	print "Eind epoch       : ", end_epoch
	print "Period in seconds: ", config.report_period

	percentage_down_maintenance = (float(len(polling_down_maintenance)) / float(polling_total)) * 100
	percentage_down = (float(len(polling_down)) / float(polling_total)) * 100
	percentage_up = 100 - (percentage_down + percentage_down_maintenance)
	print "Percentage down and in maintenanve during period    : ", percentage_down_maintenance
	print "Percentage down and NOT in maintenance during period: ", percentage_down
	print "Percentage up during period                         : ", percentage_up

	uptime_graph = Pie3D([percentage_up, percentage_down, percentage_down_maintenance])
	uptime_graph.size(400,100)
	uptime_graph.label('Up (%.2f%%)' % percentage_up, 'Down (%.2f%%)' % percentage_down, 'Maintenance (%.2f%%)' % percentage_down_maintenance)
	uptime_graph.color('00dd00','dd0000', 'ff8800')
	uptime_graph.save(str(itemid) + '.png')

def getGraphsList(hostgroupid):
	return postgres.execute(config.postgres_dbname, "select * from mios_report_graphs where hostgroupid = %s order by hostname, graphname" % hostgroupid)

def getItemsList(hostgroupid):
	return postgres.execute(config.postgres_dbname, "select * from mios_report_uptime where hostgroupid = %s order by hostname, itemname" % hostgroupid)

def sendReport(filename, hostgroupname):
	import smtplib
	from email.MIMEMultipart import MIMEMultipart
	from email.mime.text import MIMEText
	from email.MIMEBase import MIMEBase
	from email import Encoders

	sender = config.email_sender
	receiver = config.email_receiver

	msg = MIMEMultipart()
	text = 'Bij deze de rapportage van %s van de periode %s t/m %s' % (hostgroupname, config.report_start_date, config.report_end_date)
#	html = """\
#		<html>
#			<head></head>
#				<body>
#					%s
#				</body>
#		</html>
#	""" % text
	body = MIMEMultipart('alternative')
	part1 = MIMEText(text, 'plain')
#	part2 = MIMEText(html, 'html')
	body.attach(part1)
#	body.attach(part2)
	msg.attach(body)

	attachFile = MIMEBase('application', 'msword')
	attachFile.set_payload(file(filename).read())
	Encoders.encode_base64(attachFile)
	attachFile.add_header('Content-Disposition', 'attachment', filename=filename)
	msg.attach(attachFile)
	msg['Subject'] = 'Rapportage %s, %s t/m %s' % (hostgroupname, config.report_start_date, config.report_end_date)
	msg['From'] = sender
	msg['To'] = receiver
	mailer = smtplib.SMTP(config.email_server)
	mailer.sendmail(sender, receiver, msg.as_string())
	mailer.quit()

def generateReport(hostgroupname, graphData, itemData):
	import docx

	if config.report_template == '':
		existing_report = ''
	else:
		existing_report = config.mreport_home + '/templates/' + config.report_template
	if not existing_report:
		document = docx.newdocument()
	else:
		document = docx.opendocx(existing_report, mreport_home + '/tmp')
	relationships = docx.relationshiplist(existing_report, mreport_home + '/tmp')
	body = document.xpath('/w:document/w:body', namespaces=docx.nsprefixes)[0]
	body.append(docx.heading("MIOS rapportage " + hostgroupname, 1))
	hosts = []
	for record in graphData: # Create list of hosts for iteration
		if record['hostname'] not in hosts:
			hosts.append(record['hostname'])
	uptime_items = []
	for record in itemData: # Create list of uptime items for iteration
		if record['itemname'].split('Check - ')[1] not in uptime_items:
			uptime_items.append(record['itemname'].split('Check - ')[1])

	body.append(docx.heading("Beschikbaarheid business services", 2))
	for item in uptime_items:
		body.append(docx.heading(item, 3))
		for record in itemData:
			if record['itemname'].split('Check - ')[1] == item:
				print "Generating uptime graph '%s' from item '%s'" % (record['itemname'].split('Check - ')[1], item)
				getUptimeGraph(record['itemid'])
				relationships, picpara = docx.picture(relationships, str(record['itemid']) + '.png', record['itemname'], 200)
				body.append(picpara)
#				body.append(docx.caption(record['itemname'].split('Check - ')[1]))
	body.append(docx.pagebreak(type='page', orient='portrait'))

	# Performance grafieken
	body.append(docx.heading("Performance grafieken", 2))
	for host in hosts:
		body.append(docx.heading(host, 3))
		for record in graphData:
			if record['hostname'] == host and record['graphtype'] == 'p':
				print "Generating graph '%s' from host '%s'" % (record['graphname'], host)
				getGraph(record['graphid'])
				relationships, picpara = docx.picture(relationships, str(record['graphid']) + '.png', record['graphname'], 450)
				body.append(picpara)
				body.append(docx.caption(record['graphname']))
		body.append(docx.pagebreak(type='page', orient='portrait'))
	# Resource grafieken
	body.append(docx.heading("Resource grafieken", 2))
	for host in hosts:
		body.append(docx.heading(host, 3))
		for record in graphData:
			if record['hostname'] == host and record['graphtype'] == 'r':
				print "Generating graph '%s' from host '%s'" % (record['graphname'], host)
				getGraph(record['graphid'])
				relationships, picpara = docx.picture(relationships, str(record['graphid']) + '.png', record['graphname'], 450)
				body.append(picpara)
				body.append(docx.caption(record['graphname']))
		body.append(docx.pagebreak(type='page', orient='portrait'))
	print "\nDone generating graphs..."

	print "\nStart generating report"
	title = 'MIOS rapportage'
	subject = 'Performance en resources rapportage'
	creator = 'Vermont 24/7'
	keywords = ['MIOS', 'Rapportage', 'Vermont']
	coreprops = docx.coreproperties(title=title, subject=subject, creator=creator, keywords=keywords)
	wordrelationships = docx.wordrelationships(relationships)
	config.report_name = config.report_name.split('.')[0] + '_' + hostgroupname.replace(' ', '_') + '_' + config.report_start_date + '_' + config.report_end_date + '.docx'
	if not existing_report:
		appprops = docx.appproperties()
		contenttypes = docx.contenttypes()
		websettings = docx.websettings()
		docx.savedocx(document, coreprops, appprops, contenttypes, websettings, wordrelationships, config.report_name)
	else:
		import shutil, glob
		for file in glob.glob(mreport_home + '/lib/template/word/media/*'):
			shutil.copy2(file, mreport_home + '/tmp/word/media/')
		docx.savedocx(document, coreprops, wordrelationships=wordrelationships, output=config.report_name, template=existing_report, tmp_folder=mreport_home + '/tmp')
	print "Done generating report..."
	#send it through email
	if config.email_receiver != '':
		sendReport(config.report_name, hostgroupname)
	else:
		print "No email receiver specified. Report will not be sent by email."

	print "\nStart cleanup"
	import glob # Unix style pathname pattern expansion
	# Remove files which are no longer necessary
	for file in glob.glob(mreport_home + '/bin/*.png'):
		os.remove(file)
	for file in glob.glob(mreport_home + '/lib/template/word/media/*'):
		os.remove(file)
	for root, dirs, files in os.walk(mreport_home + '/tmp/', topdown=False):
		for name in files:
			os.remove(os.path.join(root, name))
		for name in dirs:
			os.rmdir(os.path.join(root, name))
	print "Done cleaning up\n"

def main():
	global postgres

	postgres = Postgres(config.postgres_dbs)
	# get hostgroup
	if len(sys.argv) > 2:
		print "To many arguments passed"
		print "Usage: %s (optional hostgroupid. If no id is given, a selection menu will apear)" % sys.argv[0]
	elif len(sys.argv) == 2:
		hostgroupid, hostgroupname = sys.argv[1], getHostgroupName(sys.argv[1])
		if not hostgroupname:
			print "No hostgroup found for id: %s" % hostgroupid
			sys.exit(1)
	else:
		hostgroupid, hostgroupname = selectHostgroup()
	if not checkHostgroup(hostgroupid):
		os.system('clear')
		print "There are no graphs registered in the database for hostgroup '%s'" % hostgroupname
		print "Please run the db_filler script first to select the graphs you want in the report for this hostgroup"
		sys.exit(1)
	else:
		os.system('clear')
		# get the hosts and their graphs from selected host group
		graphsList = getGraphsList(hostgroupid)
		itemsList = getItemsList(hostgroupid)
#		itemsList = {}
		generateReport(hostgroupname, graphsList, itemsList)

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
