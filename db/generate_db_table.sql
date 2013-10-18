create table mios_report
(
  hostgroupid numeric(4,0) not null,
  hostid numeric(10,0) not null,
  graphid numeric(10,0) not null,
  constraint pk_mios_report primary key (hostgroupid, hostid, graphid)
  using index tablespace mios_index
)
tablespace mios_table;

create index mreport_hostgroupid on mios_report(hostgroupid);
