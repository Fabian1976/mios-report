-- This should be run on the Zabbix database
create role mios login password 'm0n1t0R' nosuperuser inherit nocreatedb nocreaterole noreplication;
-- mkdir /database/mios/pgdata/pg_tblspc/mios_index
create tablespace mios_index owner mios location '/mios_index';
-- mkdir /database/mios/pgdata/pg_tblspc/mios_table
create tablespace mios_table owner mios location '/mios_table';

alter role mios in database zabbix_server set default_tablespace = 'mios_table';

create schema mios authorization mios;
grant connect on database zabbix_server to mios;
