--As user mios uitvoeren
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

create table mios_customers
(
  customer_id numeric(4,0) not null,
  name character varying(100),
  constraint pk_mios_customers primary key(customer_id)
  using index tablespace mios_index
)
tablespace mios_table;

create table mios_customer_groups
(
  customer_id numeric(4,0) not null,
  hostgroupid numeric(4,0) not null,
  constraint pk_mios_customer_groups primary key (customer_id, hostgroupid)
  using index tablespace mios_index
)
tablespace mios_table;

create sequence mios_customers_seq start 1;

create index mreportgrph_hostgroupid on mios_report_graphs(hostgroupid);
create index mreportuptm_hostgroupid on mios_report_uptime(hostgroupid);

create table mios_report_text
(
  hostgroupid numeric(4,0) not null,
  paragraph_name character varying(100),
  paragraph_text text,
  constraint pk_mios_report_text primary key (hostgroupid, paragraph_name)
  using index tablespace mios_index
)
tablespace mios_table;

insert into mios_report_text (hostgroupid, paragraph_name, paragraph_text) values (0, 'Advanced_performance_counters', 'Er zijn geen overzichten van advanced performance counters in het overzicht opgenomen. Advanced performance counters zijn wel zichtbaar in de beschikbaar gestelde dashboards (screens) in de monitoring-portal (https://zabbix.vermont24-7.com).');
insert into mios_report_text (hostgroupid, paragraph_name, paragraph_text) values (0, 'Backup_overzicht', 'Onderstaande tabel geeft een overzicht van de backupstatussen van de <platform-naam> database-backup.');
insert into mios_report_text (hostgroupid, paragraph_name, paragraph_text) values (0, 'Basic_performance_counters', E'De grafieken in dit hoofdstuk zijn grafische weergaves van "basic performance counters".\nDeze counters zeggen niets over de prestaties van een applicatie of platform, maar geven aan of componenten uit de infrastructuur op de top van hun kunnen, of wellicht eroverheen worden geduwd.\nDe basic performance counters worden per (relevante) server gerapporteerd over de afgelopen maand. Over het algemeen worden deze counters gemeten op OS-niveau:');
insert into mios_report_text (hostgroupid, paragraph_name, paragraph_text) values (0, 'Beschikbaarheid_business_componenten', E'In deze paragraaf wordt de beschikbaarheid van de business componenten grafisch weergegeven. Business componenten zijn de componenten die samen een business service vormen.\nEen overzicht van de omgeving met aanwezige business componenten is beschikbaar in hoofdstuk 7.');
insert into mios_report_text (hostgroupid, paragraph_name, paragraph_text) values (0, 'Beschikbaarheid_business_services', 'In deze paragraaf wordt de beschikbaarheid van de business services grafisch weergegeven. Business services worden gezien als de services die toegang verschaffen tot core-functionaliteit.');
insert into mios_report_text (hostgroupid, paragraph_name, paragraph_text) values (0, 'Custom', 'Deze paragraaf geeft het gebruik van de relevante business services grafisch weer.');
insert into mios_report_text (hostgroupid, paragraph_name, paragraph_text) values (0, 'Ticket_overzicht', 'Er wordt geen gebruik gemaakt van het Vermont ticket-systeem.');
insert into mios_report_text (hostgroupid, paragraph_name, paragraph_text) values (0, 'Trending', 'De volgende paragrafen laten trending-grafieken zien. Deze grafieken zijn gemaakt op basis van een selectie van basic performance counters en beslaan een periode van minimaal 6 maanden, of sinds de "go-live" van de infrastructuur/business service. Met behulp van de grafieken en strategische planningen moeten voorspellingen kunnen worden gedaan over de toekomstig beschikbare capaciteit van infrastructuur-componenten. Eventuele (kritieke) grenswaarden zijn met een rode lijn aangegeven.');
insert into mios_report_text (hostgroupid, paragraph_name, paragraph_text) values (0, 'Replace_strings', E'String1=Replaced string1\nString2=Replaced string2');
