create table mios_report_graphs
(
  hostgroupid numeric(4,0) not null,
  hostgroupname character varying(100),
  hostid numeric(10,0) not null,
  hostname character varying(100),
  graphid numeric(10,0) not null,
  graphname character varying(100),
  graphtype character varying(1),
  constraint pk_mios_report_graphs primary key (hostgroupid, hostid, graphid)
  using index tablespace mios_index
)
tablespace mios_table;

create table mios_report_uptime
(
  hostgroupid numeric(4,0) not null,
  hostgroupname character varying(100),
  hostid numeric(10,0) not null,
  hostname character varying(100),
  itemid numeric(10,0) not null,
  itemname character varying(100),
  constraint pk_mios_report_uptime primary key (hostgroupid, hostid, itemid)
  using index tablespace mios_index
)
tablespace mios_table;

create index mreportgrph_hostgroupid on mios_report_graphs(hostgroupid);
create index mreportuptm_hostgroupid on mios_report_uptime(hostgroupid);

-- Onderstaande onder de user Zabbix uitvoeren
-- Dat is nodig voor het genereren van de uptime pie charts
grant usage on schema zabbix to mios;
grant select on history_uint to mios;
grant select on timeperiods to mios;
grant select on maintenances_windows to mios;
grant select on maintenances to mios;
grant select on maintenances_groups to mios;
grant select on groups to mios;
grant select on hosts_groups to mios;
grant select on hosts to mios;
grant select on items to mios;

create index concurrently hist_uint_itemid_clock on history_uint(itemid, clock);
