-- Run as user Zabbix
grant usage on schema zabbix to mios;
grant select on history_uint to mios;
grant select on history_text to mios;
grant select on timeperiods to mios;
grant select on maintenances_windows to mios;
grant select on maintenances to mios;
grant select on maintenances_groups to mios;
grant select on groups to mios;
grant select on hosts_groups to mios;
grant select on hosts to mios;
grant select on items to mios;
