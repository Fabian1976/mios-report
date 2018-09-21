#!/usr/bin/python
__author__ = "Fabian van der Hoeven"
__copyright__ = "Copyright (C) 2013 Vermont 24x7"
__version__ = "3.2"

import ConfigParser
import sys
import os
import time
#import traceback
#from getpass import getpass
# Add mios-report LIB to path
try:
        mreport_home = os.environ['MREPORT_HOME']
except:
        mreport_home = "/opt/mios/mios-report"
sys.path.append(mreport_home + '/lib')

from zabbix_api import ZabbixAPI, ZabbixAPIException

#import curses  # curses is the interface for capturing key presses on the menu, os launches the files
import copy  # used for deepcopy. It duplicates object in stead of referencing it

postgres = None
#screen = None
#pad = None


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
            print("Can't open config file %s" % self.conf_file)
            sys.exit(1)

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


class Postgres(object):
    def __init__(self, instances):

        self.postgres_support = 0
        self.connections = []
        self.cursor = []
        self.version = []
        self.host = []
        self.port = []
        self.user = []
        self.password = []
        self.dbs = []
        self.instances = instances
        self.last_connect = []
#        self.logger           = logging.getLogger(type(self).__name__)

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

        while self.connections[indx] is None:
            try:
                self.connections[indx] = self.psycopg2.connect("host='%s' port='%s' dbname='%s' user='%s' password='%s'" % (self.host[indx], self.port[indx], self.dbs[indx], self.user[indx], self.password[indx]))
                print("Connection succesful")
            except Exception as e:
                print("Unable to connect to Postgres")
                print("PG: Additional information: %s" % e)
        self.cursor[indx] = self.connections[indx].cursor(cursor_factory=self.psycopg2_extras.DictCursor)
        self.cursor[indx].execute('select version()')
        self.version[indx] = self.cursor[indx].fetchone()
        self.last_connect = time.time()
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
            except Exception as e:
                print("PG: Failed to execute query: %s" % query)
                print("PG: Additional info: %s" % e)
                return -1
            if query.split()[0].lower() == 'select':
                try:
                    value = self.cursor[indx].fetchall()
                except Exception as e:
                    print("PG: Failed to fetch resultset")
                    print("PG: Additional info: %s" % e)
                    return -1
                return value
        except:
            print("Error in Postgres connection DB: %s" % db)
            raise
            return -2

    def commit(self, db):
        if not db in self.dbs:
            return -1
        try:
            indx = self.dbs.index(db)
            self.connections[indx].commit()
        except Exception as e:
            print("Error in Postgres connection DB: %s" % db)
            print("PG: Additional info: %s" % e)
            return -1

    def rollback(self, db):
        if not db in self.dbs:
            return -1
        try:
            indx = self.dbs.index(db)
            self.connections[indx].rollback()
        except Exception as e:
            print("Error in Postgres connection DB: %s" % db)
            print("PG: Additional info: %s" % e)
            return -1

    def closeConnection(self, db):
        if not db in self.dbs:
            return -1
        try:
            indx = self.dbs.index(db)
            self.cursor[indx].close()
            self.connections[indx].close()
        except Exception as e:
            print("Error in Postgres connection DB: %s" % db)
            print("PG: Additional info: %s" % e)
            return -1


def selectHostgroup():
    teller = 0
    hostgroups = {}
    for hostgroup in zapi.hostgroup.get({"output": "extend", "filter": {"internal": "0"}}):
        teller += 1
        hostgroups[teller] = (hostgroup['name'], hostgroup['groupid'])
    hostgroupid = -1
    while hostgroupid == -1:
        os.system('clear')
        print("Hostgroups:")
        for hostgroup in hostgroups:
            print('\t%2d: %s' % (hostgroup, hostgroups[hostgroup][0]))
        try:
            hostgroupnr = int(input('Select hostgroup: '))
            try:
                hostgroupid = hostgroups[hostgroupnr][1]
                hostgroupname = hostgroups[hostgroupnr][0]
            except KeyError:
                print("\nCounting is not your geatest asset!")
                hostgroupid = -1
                print("\nPress a key to try again...")
                os.system('read -N 1 -s')
        except ValueError:
            print("\nEeuhm... I don't think that's a number!")
            hostgroupid = -1
            print("\nPress a key to try again...")
            os.system('read -N 1 -s')
        except KeyboardInterrupt:  # Catch CTRL-C
            pass
    return (hostgroupid, hostgroupname)


def getHosts(hostgroupid):
    hosts = {}
    graphs = {}
    zapihosts = {}
    zapigraphs = {}
    selected = '0'
    found_graph = False
    selectedHosts = []

    # Fetch all monitored hosts from hostgroup
    zapihosts = zapi.host.get({"output": "name", "sortfield": "name", "groupids": [4, hostgroupid], 'monitored_hosts': 'true'})
    for host in zapihosts:
        selectedHosts.append(host['hostid'])
    # Fetch all graphs for selected hosts
    zapigraphs = zapi.graph.get({"output": "extend", "sortfield": "name", "hostids": selectedHosts, "selectHosts": "true"})
    # Restucture retreived objects
    for host in zapihosts:
        for graph in zapigraphs:
            if host['hostid'] == graph['hosts'][0]['hostid']:
                graphs[graph['name']] = (graph['graphid'], selected)
                found_graph = True
        if found_graph:
            hosts[host['name']] = (host['hostid'], graphs)
            found_graph = False
            graphs = {}
    graphs_in_db = postgres.execute(config.postgres_dbname, "select count(*) from mios_report_graphs where hostgroupid = %s" % hostgroupid)[0][0]
    if graphs_in_db > 0:
        hosts_temp = copy.deepcopy(hosts)
        graphs_in_db = postgres.execute(config.postgres_dbname, "select hostid, graphid, graphtype from mios_report_graphs where hostgroupid = %s" % hostgroupid)
        for host in hosts:
            for hnum in range(len(graphs_in_db)):
                if int(hosts[host][0]) == int(graphs_in_db[hnum][0]):
                    graphs = hosts[host][1]
                    for graph in graphs:
                        if int(graphs[graph][0]) == int(graphs_in_db[hnum][1]):
                            hosts_temp[host][1][graph] = (graphs_in_db[hnum][1], graphs_in_db[hnum][2])
        hosts = hosts_temp
    return hosts


def checkGraphs(hostgroupid, hostgroupname, menu_data, org_menu_data):
    num_hosts = len(menu_data['options'])
    print("Hostgroup '%s':" % hostgroupname)
    for host in range(num_hosts):
        print('\t%s' % menu_data['options'][host]['title'])
        num_graphs = len(menu_data['options'][host]['options'])
        selected_graphs_host = 0
        for graph in range(num_graphs):
            if menu_data['options'][host]['options'][graph]['selected'] != '0':
                selected_graphs_host += 1
        if selected_graphs_host > 0:
            for graph in range(num_graphs):
                if menu_data['options'][host]['options'][graph]['selected'] == 'p':
                    graph_type = "Performance graph"
                elif menu_data['options'][host]['options'][graph]['selected'] == 't':
                    graph_type = "Trend graph"
                elif menu_data['options'][host]['options'][graph]['selected'] == 'r':
                    graph_type = "Both performance and trending"
                elif menu_data['options'][host]['options'][graph]['selected'] == 'w':
                    graph_type = "Web-check graph"
                elif menu_data['options'][host]['options'][graph]['selected'] == 'c':
                    graph_type = "Custom graph"
                if menu_data['options'][host]['options'][graph]['selected'] != '0':
                    print("\t\t%-18s: %s" % (graph_type, menu_data['options'][host]['options'][graph]['title']))
        else:
            print("\t\tNo graphs selected for this host")
    if menu_data != org_menu_data:
        antwoord = ""
        while antwoord not in ["yes", "Yes", "no", "No"]:
            try:
                antwoord = str(raw_input('\nDo you want to store these graphs in the database (BEWARE: the old setting for this hostgroup will be overwritten by these new ones)? (Yes/No): '))
            except KeyboardInterrupt:  # Catch CTRL-C
                pass
        if antwoord in ["yes", "Yes"]:
            print("OK")
            storeGraphs(hostgroupid, hostgroupname, menu_data)
        else:
            print("Then not")
    else:
        print("\nNothing changed. Nothing to do.")


def storeGraphs(hostgroupid, hostgroupname, menu_data):

    num_hosts = len(menu_data['options'])
    postgres.execute(config.postgres_dbname, "delete from mios_report_graphs where hostgroupid = %s" % hostgroupid)
    # do not commit! stay in same transaction so rollback will work if an error occurs
    for host in range(num_hosts):
        num_graphs = len(menu_data['options'][host]['options'])
        for graph in range(num_graphs):
            if menu_data['options'][host]['options'][graph]['selected'] != '0':
                try:
                    postgres.execute(config.postgres_dbname, "insert into mios_report_graphs (hostgroupid, hostgroupname, hostid, hostname, graphid, graphname, graphtype) values (%s, '%s', %s, '%s', %s, '%s', '%s')" % (hostgroupid, hostgroupname, menu_data['options'][host]['hostid'], menu_data['options'][host]['title'], menu_data['options'][host]['options'][graph]['graphid'], menu_data['options'][host]['options'][graph]['title'], menu_data['options'][host]['options'][graph]['selected']))
                except:
                    print("\nNieuwe waardes NIET toegevoegd aan database. Er ging iets mis.\nDe transactie wordt terug gedraaid.\n")
                    postgres.rollback(config.postgres_dbname)
                    postgres.closeConnection(config.postgres_dbname)
                    raise
    postgres.commit(config.postgres_dbname)
    postgres.closeConnection(config.postgres_dbname)


def main():
    import myCursesReportMenu
    global postgres

    postgres = Postgres(config.postgres_dbs)
    # get hostgroups
    hostgroupid, hostgroupname = selectHostgroup()
    os.system('clear')
    print("The hosts and related graphs from group '%s' are being fetched..." % hostgroupname)
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
        menu_hosts['subtitle'] = 'Select the graphs for the report. Use "p" to mark as a performance graph, "t" for a trend graph, "r" for both, "w" for a web-check graph and "c" for custom graph'
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
    #Make copy of original loaded menu (before possible changes)
    org_menu = copy.deepcopy(menu)

    myCursesReportMenu.doMenu(menu)
    os.system('clear')
    checkGraphs(hostgroupid, hostgroupname, menu, org_menu)

if __name__ == "__main__":
    global config
    try:
        mreport_home = os.environ['MREPORT_HOME']
    except:
        mreport_home = "/opt/mios/mios-report"

    config_file = mreport_home + '/conf/mios-report.conf'
    config = Config(config_file)
    config.parse()
    zapi = ZabbixAPI(server=config.zabbix_frontend, log_level=0, validate_certs=False)

    try:
        zapi.login(config.zabbix_user, config.zabbix_password)
#        print "Zabbix API Version: %s" % zapi.api_version()
    except ZabbixAPIException as e:
        sys.stderr.write(str(e) + '\n')
    main()
