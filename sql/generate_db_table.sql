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
  itemidid numeric(10,0) not null,
  itemname character varying(100),
  constraint pk_mios_report_uptime primary key (hostgroupid, hostid, itemid)
  using index tablespace mios_index
)
tablespace mios_table;

create index mreportgrph_hostgroupid on mios_report_graphs(hostgroupid);
create index mreportuptm_hostgroupid on mios_report_uptime(hostgroupid);
