create table mios_report
(
  hostgroupid numeric(4,0) not null,
  hostgroupname character varying(100),
  hostid numeric(10,0) not null,
  hostname character varying(100),
  graphid numeric(10,0) not null,
  graphname character varying(100),
  constraint pk_mios_report primary key (hostgroupid, hostid, graphid)
  using index tablespace mios_index
)
tablespace mios_table;

create index mreport_hostgroupid on mios_report(hostgroupid);
