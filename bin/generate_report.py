#!/usr/bin/python
__author__    = "Fabian van der Hoeven"
__copyright__ = "Copyright (C) 2013 Vermont 24x7"
__version__   = "2.8"

import ConfigParser
import sys, os
import time, datetime
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
	def __init__(self, conf_file, customer_conf_file):
		self.config              = None
		self.customer_config     = None
		self.zabbix_frontend     = ''
		self.zabbix_user         = ''
		self.zabbix_password     = ''
		self.postgres_dbname     = ''
		self.postgres_dbs        = {}
		self.hostgroupid         = None
		self.report_name         = ''
		self.report_template     = ''
		self.report_start_date   = ''
		self.report_period       = ''
		self.report_trend_start  = ''
		self.report_trend_period = ''
		self.report_graph_width  = ''
		self.report_title        = ''
		self.report_backup_item  = None
		try:
			self.mreport_home = os.environ['MREPORT_HOME']
		except:
			self.mreport_home = '/opt/mios/mios-report'

		self.conf_file = conf_file
		self.customer_conf_file = customer_conf_file
		if not os.path.exists(self.conf_file):
			print "Can't open config file %s" % self.conf_file
			exit(1)
		elif not os.path.exists(self.customer_conf_file):
			print "Can't open config file %s" % self.customer_conf_file
			exit(1)
		# Read common config
		self.config = ConfigParser.ConfigParser()
		self.config.read(self.conf_file)
		# Read customer specific config
		self.customer_config = ConfigParser.ConfigParser()
		self.customer_config.read(self.customer_conf_file)

	def parse(self):
		# Parse common config
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
		# Parse e-mail stuff (also common)
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

		# Parse customer specific config
		try:
			self.hostgroupid = self.customer_config.get('report', 'hostgroupid')
		except:
			self.hostgroupid = None
		try:
			self.report_name = self.customer_config.get('report', 'name')
		except:
			self.report_name = 'Report.docx'
		try:
			self.report_template = self.customer_config.get('report', 'template')
		except:
			self.report_template = ''
		if 'start_date' not in globals(): # so start_date is not passed as an argument to the script
			try:
				self.report_start_date = self.customer_config.get('report', 'start_date')
				# validate date
				datetime.datetime.strptime(self.report_start_date, '%d-%m-%Y')
			except:
				self.report_start_date = ''
		else:
			self.report_start_date = start_date
		try:
			self.report_period = self.customer_config.get('report', 'period')
			# Convert period to seconds
			import re, calendar
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
				total_seconds = 0
				for next_month in range(int(period_items[0])):
					if month+next_month > 12:
						month -= 12
						year += 1
					days_in_month = calendar.monthrange(year, month+next_month)[1]
					total_seconds += days_in_month * seconds_in_day
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
		# Calculate end_date
		if self.report_start_date != '':
			# If start_date is given calculate end_date with period
			self.report_end_date = datetime.date.strftime(datetime.datetime.strptime(self.report_start_date, "%d-%m-%Y") + datetime.timedelta(seconds=self.report_period-1), '%d-%m-%Y')
		else:
			# If no start_date is given, assume today as end_date and calculate the start_date with period
			self.report_end_date = datetime.date.strftime(datetime.datetime.today(), '%d-%m-%Y')
			self.report_start_date = datetime.date.strftime(datetime.datetime.strptime(self.report_end_date, "%d-%m-%Y") - datetime.timedelta(seconds=self.report_period-1), '%d-%m-%Y')

		try:
			self.report_trend_period = self.customer_config.get('report', 'trend_period')
			import re, calendar
			match = re.match(r"([0-9]+)([a-z]+)", self.report_trend_period, re.I)
			if match:
				period_items = match.groups()
			seconds_in_day = 86400
			if period_items[1] == 'm':
				day, month, year = map(int, self.report_start_date.split('-'))
				month -= int(period_items[0])
				month += 1
				if month < 1:
					month += 12
					year -= 1
				total_seconds = 0
				self.report_trend_start = str(day).zfill(2) + '-' + str(month).zfill(2) + '-' + str(year).zfill(2)
				for next_month in range(int(period_items[0])):
					if month+next_month > 12:
						month -= 12
						year += 1
					days_in_month = calendar.monthrange(year, month+next_month)[1]
					total_seconds += days_in_month * seconds_in_day
			self.report_trend_period = total_seconds
		except:
			raise
			self.report_trend_period = self.report_period
		try:
			self.report_graph_width = self.customer_config.get('report', 'graph_width')
		except:
			self.report_graph_width = '1200'
		try:
			self.report_title = self.customer_config.get('report', 'title')
		except:
			self.report_title = "MIOS rapportage"
		try:
			self.report_backup_item = self.customer_config.get('report', 'backup_item')
		except:
			self.report_backup_item = None
		try:
			self.report_infra_picture = self.customer_config.get('report', 'infra_picture')
		except:
			self.report_infra_picture = None

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
			except Exception, e:
				print("Unable to connect to Postgres")
				print("PG: Additional information: %s" % e)
				print("Trying to reconnect in 10 seconds")
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

def getGraph(graphid, graphtype):
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
	z_image_name = str(graphid) + '_' + graphtype + '.png'
	# Log on to Zabbix and get session cookie
	curl.setopt(curl.URL, z_url_index)
	curl.setopt(curl.POSTFIELDS, z_login_data)
	curl.setopt(curl.COOKIEJAR, z_filename_cookie)
	curl.setopt(curl.COOKIEFILE, z_filename_cookie)
	curl.perform()
	# Retrieve graphs using cookie
	# By just giving a period the graph will be generated from today and "period" seconds ago. So a period of 604800 will be 1 week (in seconds)
	# You can also give a starttime (&stime=yyyymmddhh24mm). Example: &stime=201310130000&period=86400, will start from 13-10-2013 and show 1 day (86400 seconds)
	if graphtype == 't': #trending graph
		day, month, year = config.report_trend_start.split('-')
		stime = year + month + day + '000000'
		curl.setopt(curl.URL, z_url_graph + '?graphid=' + str(graphid) + '&width=' + config.report_graph_width + '&stime=' + stime + '&period=' + str(config.report_trend_period))
	else: # normal graph
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
	polling_total = postgres.execute(config.postgres_dbname, "select count(*) from history_uint where itemid = %s and clock between %s and %s" % (itemid, start_epoch, end_epoch))[0][0]
	rows = postgres.execute(config.postgres_dbname, "select clock from history_uint where itemid = %s and clock > %s and clock < %s and value = 0 order by clock" % (itemid, start_epoch, end_epoch))
	polling_down_rows = []
	for row in rows:
		polling_down_rows.append(row[0])
	item_maintenance_rows = postgres.execute(config.postgres_dbname, "select start_date, (start_date + period) from timeperiods\
	 inner join maintenances_windows on maintenances_windows.timeperiodid = timeperiods.timeperiodid\
	 inner join maintenances on maintenances.maintenanceid = maintenances_windows.maintenanceid\
	 inner join maintenances_groups on maintenances_groups.maintenanceid = maintenances.maintenanceid\
	 inner join groups on maintenances_groups.groupid = groups.groupid\
	 inner join hosts_groups on hosts_groups.groupid = groups.groupid\
	 inner join hosts on hosts_groups.hostid = hosts.hostid\
	 inner join items on items.hostid = hosts.hostid\
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

	item_interval = postgres.execute(config.postgres_dbname, "select delay from items where itemid = %s" % itemid)[0][0]
	# Get history values which have no data for longer then the interval and at least 5 minutes (Zabbix internal interval)
	if item_interval < 300:
		interval_threshold = 300
	else:
		interval_threshold = (item_interval * 2) + 10
	rows = postgres.execute(config.postgres_dbname, "select clock, difference from\
	 (\
	  select clock, clock - lag(clock) over (order by clock) as difference from history_uint\
	  where itemid = %s and clock between %s and %s\
	 ) t\
	 where difference > %s" % (itemid, start_epoch, end_epoch, interval_threshold))
	item_nodata_rows = []
	num_pollings_nodata = 0
	for row in rows:
		end_date_nodata = row[0]
		seconds_nodata = row[1]
		num_pollings_nodata += (seconds_nodata / item_interval)
		start_date_nodata = end_date_nodata - seconds_nodata
		item_nodata_rows.append((start_date_nodata, end_date_nodata))
	print "Polling items with nodata                : %s" % num_pollings_nodata
	print "Polling items down and in maintenance    : %s" % len(polling_down_maintenance)
	print "Polling items down and NOT in maintenance: %s" % len(polling_down)
	print "Polling items UP                         : %s" % (polling_total - len(polling_down_maintenance) - len(polling_down))
	print "Start epoch      : ", start_epoch
	print "Eind epoch       : ", end_epoch
	print "Period in seconds: ", config.report_period

	percentage_down_maintenance = (float(len(polling_down_maintenance)) / float(polling_total)) * 100
	percentage_down = (float(len(polling_down)+num_pollings_nodata) / float(polling_total)) * 100
	percentage_up = 100 - (percentage_down + percentage_down_maintenance)
	print "Percentage down and in maintenanve during period    : ", percentage_down_maintenance
	print "Percentage down and NOT in maintenance during period: ", percentage_down
	print "Percentage up during period                         : ", percentage_up

	uptime_graph = Pie3D([percentage_up, percentage_down, percentage_down_maintenance])
	uptime_graph.size(400,100)
	uptime_graph.label('Up (%.2f%%)' % percentage_up, 'Down (%.2f%%)' % percentage_down, 'Maintenance (%.2f%%)' % percentage_down_maintenance)
	uptime_graph.color('00dd00','dd0000', 'ff8800')
	uptime_graph.save(str(itemid) + '.png')

	# Generate table overview of down time (get consecutive down periods)
	item_interval *=2 #Double interval. Interval is never exact. Allways has a deviation of 1 or 2 seconds. So we double the interval just to be safe
	downtime_periods = []
	if len(polling_down_rows) > 0:
		for num in range(len(polling_down_rows)):
			if num == 0:
				start_period = polling_down_rows[num]
				prev_clock = start_period
				end_period = start_period + item_interval
			else:
				if polling_down_rows[num] <= prev_clock + item_interval:
					# Consecutive down time
					end_period = polling_down_rows[num]
					prev_clock = polling_down_rows[num]
				else:
					downtime_periods.append((start_period, end_period))
					start_period = polling_down_rows[num]
					prev_clock = polling_down_rows[num]
		downtime_periods.append((start_period, end_period))
	# Append nodata rows to downtime_periods
	for nodata_rows in item_nodata_rows:
		downtime_periods.append(nodata_rows)
	return downtime_periods
		
def getMaintenancePeriods(hostgroupid):
	day, month, year = map(int, config.report_start_date.split('-'))
	start_epoch = time.mktime((year, month, day, 0, 0, 0, 0, 0, 0))
	end_epoch = start_epoch + config.report_period
	maintenance_rows = postgres.execute(config.postgres_dbname, "select maintenances.name || '. ' || maintenances.description, start_date, (start_date + period) from timeperiods\
	 inner join maintenances_windows on maintenances_windows.timeperiodid = timeperiods.timeperiodid\
	 inner join maintenances on maintenances.maintenanceid = maintenances_windows.maintenanceid\
	 inner join maintenances_groups on maintenances_groups.maintenanceid = maintenances.maintenanceid\
	 inner join groups on maintenances_groups.groupid = groups.groupid\
	 where groups.groupid = %s and timeperiods.start_date between %s and %s" %(hostgroupid, start_epoch, end_epoch))
	return maintenance_rows

def getGraphsList(hostgroupid):
	return postgres.execute(config.postgres_dbname, "select * from mios_report_graphs where hostgroupid = %s order by hostname, graphname" % hostgroupid)

def getItemsList(hostgroupid):
	return postgres.execute(config.postgres_dbname, "select * from mios_report_uptime where hostgroupid = %s order by hostname, itemname" % hostgroupid)

def getBackupList(itemid):
	day, month, year = map(int, config.report_start_date.split('-'))

	start_epoch = time.mktime((year, month, day, 0, 0, 0, 0, 0, 0))
	end_epoch = start_epoch + config.report_period

#	backupList = postgres.execute(config.postgres_dbname, "select value from history_text where itemid = %s and clock between %s and %s" % (itemid, start_epoch, end_epoch))
	backupList = [['15-11-2013 00:59:03;15-11-2013 01:10:15;00:11:12;COMPLETED;DB FULL'] ,['14-11-2013 00:59:03;14-11-2013 01:10:15;00:11:12;COMPLETED;DB FULL']]
	return backupList

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

def generateReport(hostgroupid, hostgroupname, graphData, itemData):
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
	#Samenvatting toevoegen met maintenance overzicht in opmerkingen
	body.append(docx.heading("Samenvatting", 1))
	body.append(docx.heading("Opmerkingen", 2))
	# Maintenance tabel
	maintenance_periods = getMaintenancePeriods(hostgroupid)
	maintenance_tbl_rows = []
	tbl_heading = [ 'OMSCHRIJVING', 'START MAINTENANCE', 'EINDE MAINTENANCE', 'DUUR' ]
	maintenance_tbl_rows.append(tbl_heading)
	for num in range(len(maintenance_periods)):
		tbl_row = []
		(description, start_period, end_period) = maintenance_periods[num]
		tbl_row.append(description)
		tbl_row.append(datetime.datetime.fromtimestamp(start_period).strftime("%d-%m-%Y %H:%M:%S"))
		tbl_row.append(datetime.datetime.fromtimestamp(end_period).strftime("%d-%m-%Y %H:%M:%S"))
		tbl_row.append(hms(end_period - start_period))
		maintenance_tbl_rows.append(tbl_row)
	if len(maintenance_periods) > 0:
		body.append(docx.table(maintenance_tbl_rows))
	else:
		#Aanpassen in lege tabel. Niet de tekst die er nu staat!
#		body.append(docx.paragraph("Er is in de afgelopen periode geen gepland onderhoud geweest."))
		tbl_rows = []
		tbl_heading = [ 'ITEM', 'OPMERKINGEN' ]
		tbl_rows.append(tbl_heading)
		tbl_rows.append(['',''])
		body.append(docx.table(tbl_rows, colw=[1188,7979], firstColFillColor='E3F3B7'))


	body.append(docx.heading("Aktiepunten", 2))

	body.append(docx.heading("MIOS monitoring", 1))
	body.append(docx.heading("Beschikbaarheid business services", 2))
	body.append(docx.paragraph("In deze paragraaf wordt de beschikbaarheid van de business services grafisch weergegeven. Business services worden gezien als de services die toegang verschaffen tot core-functionaliteit."))
	body.append(docx.heading("Web-check", 3))
	for record in graphData:
		if record['graphtype'] == 'w':
			print "Generating web-check graph '%s'" % record['graphname']
			getGraph(record['graphid'], 'w')
			relationships, picpara = docx.picture(relationships, str(record['graphid']) + '_w.png', record['graphname'], 450)
			body.append(picpara)
			body.append(docx.figureCaption(record['graphname']))
	hosts = []
	for record in graphData: # Create list of hosts for iteration
		if record['hostname'] not in hosts:
			hosts.append(record['hostname'])
	uptime_items = []
	for record in itemData: # Create list of uptime items for iteration
		if record['itemname'] not in uptime_items:
			uptime_items.append(record['itemname'])

	body.append(docx.heading("Beschikbaarheid business componenten", 2))
	body.append(docx.paragraph("In deze paragraaf wordt de beschikbaarheid van de business componenten grafisch weergegeven. Business componenten zijn de componenten die samen een business service vormen."))
	body.append(docx.paragraph("Een overzicht van de omgeving met aanwezige business componenten is beschikbaar in hoofdstuk 7."))
	for item in uptime_items:
		body.append(docx.heading(item, 3))
		for record in itemData:
			if record['itemname'] == item:
				print "Generating uptime graph '%s' from item '%s'" % (record['itemname'], item)
				downtime_periods = getUptimeGraph(record['itemid'])
				relationships, picpara = docx.picture(relationships, str(record['itemid']) + '.png', record['itemname'], 200, jc='center')
				body.append(picpara)
#				body.append(docx.figureCaption(record['itemname']))
				tbl_rows = []
				tbl_heading = [ 'START DOWNTIME', 'EINDE DOWNTIME', 'DUUR' ]
				tbl_rows.append(tbl_heading)
				for num in range(len(downtime_periods)):
					tbl_row = []
					(start_period, end_period) = downtime_periods[num]
					tbl_row.append(datetime.datetime.fromtimestamp(start_period).strftime("%d-%m-%Y %H:%M:%S"))
					tbl_row.append(datetime.datetime.fromtimestamp(end_period).strftime("%d-%m-%Y %H:%M:%S"))
					tbl_row.append(hms(end_period - start_period))
					tbl_rows.append(tbl_row)
				if len(downtime_periods) > 0:
					body.append(docx.table(tbl_rows))
	# Maintenance periodes
	body.append(docx.heading("Maintenance-overzicht", 3))
	# De gegevens zijn al gegenereerd bij de samenvatting. Dus er hoeft alleen nog maar gekeken te worden of het nogmaals toegevoegd moet worden
#	maintenance_periods = getMaintenancePeriods(hostgroupid)
#	tbl_rows = []
#	tbl_heading = [ 'OMSCHRIJVING', 'START MAINTENANCE', 'EINDE MAINTENANCE', 'DUUR' ]
#	tbl_rows.append(tbl_heading)
#	for num in range(len(maintenance_periods)):
#		tbl_row = []
#		(description, start_period, end_period) = maintenance_periods[num]
#		tbl_row.append(description)
#		tbl_row.append(datetime.datetime.fromtimestamp(start_period).strftime("%d-%m-%Y %H:%M:%S"))
#		tbl_row.append(datetime.datetime.fromtimestamp(end_period).strftime("%d-%m-%Y %H:%M:%S"))
#		tbl_row.append(hms(end_period - start_period))
#		tbl_rows.append(tbl_row)
	if len(maintenance_periods) > 0:
		body.append(docx.table(maintenance_tbl_rows))
	else:
		body.append(docx.paragraph("Er is in de afgelopen periode geen gepland onderhoud geweest."))

	body.append(docx.heading("Opmerkingen", 3))
	tbl_rows = []
	tbl_heading = [ 'ITEM', 'OPMERKINGEN' ]
	tbl_rows.append(tbl_heading)
	tbl_rows.append(['',''])
	body.append(docx.table(tbl_rows, colw=[1188,7979], firstColFillColor='E3F3B7'))

	# Performance grafieken
	body.append(docx.heading("Basic performance counters", 2))
	body.append(docx.paragraph('De grafieken in dit hoofdstuk zijn grafische weergaves van "basic performance counters". '
	 'Deze counters zeggen niets over de prestaties van een applicatie of platform, maar geven aan of componenten uit de infrastructuur op de top van hun kunnen, of wellicht eroverheen worden geduwd. '
	 'De basic performance counters worden per (relevante) server gerapporteerd over de afgelopen maand. Over het algemeen worden deze counters gemeten op OS-niveau:'))
	points = [	'CPU-load: geeft de zogenaamde "load averages" van een systeem weer. Dit getal is de som van het aantal wachtende processen + actieve processen op de CPU;',
			'CPU utilization: dit getal geeft aan hoeveel procent van de CPU-capaciteit daadwerkelijk wordt gebruikt per tijdseenheid, onderverdeeld naar type CPU-gebruik;',
			'Memory utilization: dit getal geeft aan hoeveel memory er op de server in gebruik is, onderverdeeld naar type memory-gebruik;',
			'Disk stats: geeft latency aan van relevante disken;',
			'Network traffic: geeft network-gebruik aan.']
	for point in points:
		body.append(docx.paragraph(point, style='ListBulleted'))
	body.append(docx.paragraph("De grafieken zijn gegroepeerd naar server, dit geeft het beste inzicht in de specifieke server."))
	body.append(docx.pagebreak(type='page', orient='portrait'))
	for host in hosts:
		host_has_graphs = 0
		for record in graphData:
			if record['hostname'] == host and (record['graphtype'] == 'p' or record['graphtype'] == 'r'):
				host_has_graphs = 1
		if host_has_graphs:
			body.append(docx.heading(host, 3))
			for record in graphData:
				if record['hostname'] == host and (record['graphtype'] == 'p' or record['graphtype'] == 'r'):
					print "Generating performance graph '%s' from host '%s'" % (record['graphname'], host)
					getGraph(record['graphid'], 'p')
					relationships, picpara = docx.picture(relationships, str(record['graphid']) + '_p.png', record['graphname'], 450)
					body.append(picpara)
					body.append(docx.figureCaption(record['graphname']))
#			body.append(docx.pagebreak(type='page', orient='portrait'))

	body.append(docx.heading("Opmerkingen", 3))
	tbl_rows = []
	tbl_heading = [ 'ITEM', 'OPMERKINGEN' ]
	tbl_rows.append(tbl_heading)
	tbl_rows.append(['',''])
	body.append(docx.table(tbl_rows, colw=[1188,7979], firstColFillColor='E3F3B7'))

	# Trending grafieken
	body.append(docx.heading("Trending", 2))
	body.append(docx.paragraph('De volgende paragrafen laten trending-grafieken zien. Deze grafieken zijn gemaakt op basis van een selectie van basic performance counters, en beslaan een periode van minimaal 6 maanden, of sinds de "go-live" van de infrastructuur/business service. Met behulp van de grafieken en strategische planningen moeten voorspellingen kunnen worden gedaan over de toekomstig beschikbare capaciteit van infrastructuur-componenten. Eventuele (kritieke) grenswaarden zijn met een rode lijn aangegeven.'))
#	points = [	'CPU-load (minimaal 6 maanden)',
#			'Counters die tegen limiet aan gaan komen',
#			'Disk-bezetting',
#			'IOPS']
#	for point in points:
#		body.append(docx.paragraph(point, style='ListBulleted'))
	for host in hosts:
		host_has_graphs = 0
		for record in graphData:
			if record['hostname'] == host and (record['graphtype'] == 't' or record['graphtype'] == 'r'):
				host_has_graphs = 1
		if host_has_graphs:
			body.append(docx.heading(host, 3))
			for record in graphData:
				if record['hostname'] == host and (record['graphtype'] == 't' or record['graphtype'] == 'r'):
					print "Generating trending graph '%s' from host '%s'" % (record['graphname'], host)
					getGraph(record['graphid'], 't')
					relationships, picpara = docx.picture(relationships, str(record['graphid']) + '_t.png', record['graphname'], 450)
					body.append(picpara)
					body.append(docx.figureCaption(record['graphname']))
#			body.append(docx.pagebreak(type='page', orient='portrait'))

	body.append(docx.heading("Opmerkingen", 3))
	tbl_rows = []
	tbl_heading = [ 'ITEM', 'OPMERKINGEN' ]
	tbl_rows.append(tbl_heading)
	tbl_rows.append(['',''])
	body.append(docx.table(tbl_rows, colw=[1188,7979], firstColFillColor='E3F3B7'))

	body.append(docx.heading("Advanced performance counters", 2))
	body.append(docx.paragraph('Er zijn geen overzichten van advanced performance counters in het overzicht opgenomen. Advanced performance counters zijn wel zichtbaar in de beschikbaar gestelde dashboards (screens) in de monitoring-portal (https://mios.vermont24-7.com).'))
	print "\nDone generating graphs..."

	# Backup overzicht
	body.append(docx.heading("Backup overzicht", 2))
	body.append(docx.paragraph('Onderstaande tabel geeft een overzicht van de backupstatussen van de Promedico database-backup. Deze backup wordt middels Oracle RMAN uitgevoerd en naar een door AZV beschikbaar gestelde NFS-disk geschreven. De RMAN-backups, evenals de backups van de virtual machines, worden verder door AZV uitgevoerd. Er is voor Vermont geen inzicht in deze backups, deze kunnen vooralsnog dan ook niet worden gerapporteerd.'))
	body.append(docx.heading("Overzicht", 3))
	if not config.report_backup_item:
		body.append(docx.paragraph('Geen backup gemaakt in deze periode.'))
	else:
		backupList = getBackupList(config.report_backup_item)
		tbl_rows = []
		tbl_heading = [ 'START BACKUP', 'EINDE BACKUP', 'DUUR', 'STATUS', 'TYPE' ]
		tbl_rows.append(tbl_heading)
		for item in backupList:
			tbl_row = []
			(backup_start, backup_end, backup_duration, backup_status, backup_type) = item[0].split(';')
			if backup_status == 'COMPLETED':
				backup_status = 'OK'
			tbl_row.append(backup_start)
			tbl_row.append(backup_end)
			tbl_row.append(backup_duration)
			tbl_row.append(backup_status)
			tbl_row.append(backup_type)
			tbl_rows.append(tbl_row)
		body.append(docx.table(tbl_rows))
		body.append(docx.heading("Opmerkingen", 3))
		tbl_rows = []
		tbl_heading = [ 'ITEM', 'OPMERKINGEN' ]
		tbl_rows.append(tbl_heading)
		tbl_rows.append(['',''])
		body.append(docx.table(tbl_rows, colw=[1188,7979], firstColFillColor='E3F3B7'))

	body.append(docx.heading("Ticket-overzicht", 1))
	body.append(docx.paragraph("Er wordt geen gebruik gemaakt van het Vermont ticket-systeem, in overleg is besloten Promedico's centrale ticket-systeem te gebruiken. Rapportages kunnen niet door Vermont worden verstrekt."))

	body.append(docx.heading("Aktiepunten", 1))

	body.append(docx.heading("Definities/afkortingen", 1))
	tbl_rows = []
	tbl_heading = [ 'ITEM', 'OPMERKINGEN' ]
	tbl_rows.append(tbl_heading)
	row1_col1 = docx.paragraph([("Business Services", "b")], size=8)
	row1_col2_par1 = docx.paragraph("Business services worden gezien als de services die toegang verschaffen tot business logica., zoals een (web-)applicatie of website, of componenten die daar rechtstreeks aan gerelateerd zijn, zoals een webservice, een batch-service, een mail-service etc.", size=8)
	row1_col2_par2 = docx.paragraph("Er is bewust sprake van services, en niet van servers, omdat servers ondergeschikt zijn aan services. De beschikbaarheid van deze services wordt functioneel gemeten, wat betekent dat een onbeschikbaarheid van 1 van de onderliggende redundante componenten (zoals servers) niet zichtbaar hoeft te zijn als de service daar niet negatief door wordt beinvloed.", size=8)
	tbl_rows.append([row1_col1,[row1_col2_par1, row1_col2_par2]])

	row2_col1 = docx.paragraph([("CPU-load", "b")], size=8)
	row2_col2_par1 = docx.paragraph('geeft de zogenaamde "load averages" van een systeem weer. Dit getal is de som van het aantal wachtende processen + aktieve processen op de CPU. Wanneer dit getal de hoeveelheid beschikbare CPU.s (cores) regelmatig overschrijdt, kan de server-capaciteit te laag zijn, en draait de machine inefficient. Een server welke dient om een hoge concurrency te kunnen verwerken, dient derhalve voldoende overhead te hebben. Een server die bijvoorbeeld gedurende een X tijd batches verwerkt, moet juist zo veel en efficient mogelijk CPU-resources gebruiken, wat betekent dat load-averages daar hoog mogen zijn, maar liefst niet boven het aantal beschikbare CPU.s. Het getal kan echter naast een indicatie van een te hoge load ook aangeven dat de machine op andere resources tekort komt, bijvoorbeeld wachten op disk-IO;', size=8)
	row2_col2_par2 = docx.paragraph('In de grafiek zijn een drietal gemiddelden opgenomen:', size=8)
	row2_col2_par3 = docx.paragraph('1 min average: gemiddelde gemeten per minuut. Deze waarden komen over het algemeen hoger uit dan de andere twee gemiddelden;', size=8, ind=720)
	row2_col2_par4 = docx.paragraph('5 min average: gemiddelde gemeten over 5 minuten. Wanneer deze waarden bij een lange meting gelijk of in de buurt liggen van voorgaand gemiddelde, is er reden aan te nemen dat op dat tijdstip de load enige tijd heeft aangehouden. Dit kan zijn door langlopende processen, of door een veelvoud aan .piek-procesjes. (hoge concurrency) en gebruikersgedrag welke redelijk constant zijn verlopen over de langere tijd. Bij een korte meting (zoals bij live meekijken in dashboards) gelden iets andere interpretatie-regels, en zullen in de praktijk de waarden tussen de verschillende gemiddelden verder uit elkaar liggen;', size=8, ind=720)
	row2_col2_par5 = docx.paragraph('15 min average: gemiddelde gemeten over 15 minuten. Hiervoor geldt hetzelfde als in voorgaand punt;', size=8, ind=720)
	tbl_rows.append([row2_col1, [row2_col2_par1, row2_col2_par2, row2_col2_par3, row2_col2_par4, row2_col2_par5]])

	row3_col1 = docx.paragraph([("CPU utilization", "b")], size=8)
	row3_col2 = docx.paragraph("dit getal geeft aan hoeveel procent van de CPU-capaciteit daadwerkelijk wordt gebruikt per tijdseenheid, en door welk type CPU-gebruik.", size=8)
	tbl_rows.append([row3_col1, row3_col2])
	body.append(docx.table(tbl_rows, colw=[1648,7529], firstColFillColor='E3F3B7'))

	body.append(docx.heading("Omgevingsoverzicht", 1))
	if config.report_infra_picture:
		relationships, picpara = docx.picture(relationships, '/opt/mios/mios-report/templates/' + config.report_infra_picture, config.report_infra_picture.split('.')[0].replace('_', ' '), 450)
		body.append(picpara)
		body.append(docx.figureCaption(config.report_infra_picture.split('.')[0].replace('_', ' ')))
	print "\nStart generating report"
	title = config.report_title
	subject = 'Performance en trending rapportage'
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

def hms(seconds):
	minutes, seconds = divmod(seconds, 60)
	hours, minutes = divmod(minutes, 60)
	hours %= 24
	if hours != 0:
		result = str(hours) + " uur, " + str(minutes) + " minuten en " + str(seconds) + " seconden"
	elif minutes != 0:
		result = str(minutes) + " minuten en " + str(seconds) + " seconden"
	else:
		result = str(seconds) + " seconden"
	return result

def cleanup():
	print "\nStart cleanup"
	import glob # Unix style pathname pattern expansion
	# Remove files which are no longer necessary
	print "Remove generated graph images"
	for file in glob.glob(mreport_home + '/bin/*.png'):
		os.remove(file)
	for file in glob.glob(mreport_home + '/lib/template/word/media/*'):
		os.remove(file)
	print "Remove files from tmp folders"
	for root, dirs, files in os.walk(mreport_home + '/tmp/', topdown=False):
		for name in files:
			os.remove(os.path.join(root, name))
		for name in dirs:
			os.rmdir(os.path.join(root, name))
	try:
		os.remove('/tmp/docx_seq')
	except:
		pass
	print "Done cleaning up\n"

def main():
	global postgres
	import atexit
	atexit.register(cleanup)

	postgres = Postgres(config.postgres_dbs)

	# get hostgroup
	if not config.hostgroupid:
		hostgroupid, hostgroupname = selectHostgroup()
	else:
		hostgroupid, hostgroupname = config.hostgroupid, getHostgroupName(config.hostgroupid)

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
		generateReport(hostgroupid, hostgroupname, graphsList, itemsList)

if  __name__ == "__main__":
	global config
	global start_date
	try:
		mreport_home = os.environ['MREPORT_HOME']
	except:
		mreport_home = "/opt/mios/mios-report"

	config_file = mreport_home + '/conf/mios-report.conf'
	from optparse import OptionParser

	usage = "usage: %prog [options] <start_date: dd-mm-yyyy>"
	parser = OptionParser(usage=usage, version="%prog " + __version__)
	parser.add_option("-c", "--customer", dest="customer_conf_file", metavar="FILE", help="file which contains report information for customer")
	(options, args) = parser.parse_args()
	if not options.customer_conf_file:
		parser.error("No option given")
	try:
		customer_conf_file = options.customer_conf_file
	except:
		parser.error("Wrong or unknown option")
	if len(args) == 1:
		start_date = args[0]
		try:
			valid_date = time.strptime(start_date, '%d-%m-%Y')
		except ValueError:
			print 'Invalid date! (%s)' % start_date
			sys.exit(1)

	config = Config(config_file, customer_conf_file)
	config.parse()

	zapi = ZabbixAPI(server=config.zabbix_frontend,log_level=0)

	try:
		zapi.login(config.zabbix_user, config.zabbix_password)
#		print "Zabbix API Version: %s" % zapi.api_version()
	except ZabbixAPIException, e:
		sys.stderr.write(str(e) + '\n')

	main()
