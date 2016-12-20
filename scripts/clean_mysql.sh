#!/bin/bash
#
# Run via cron to remove older entries for chatty sensors/entities
#
mysql hass --execute="
DELETE states, events
FROM states
JOIN events ON states.event_id = events.event_id
WHERE states.entity_id IN ('sensor.eth0_in', 'sensor.eth0_out', 'sensor.eth0_in_mbps', 'sensor.eth0_out_mbps') AND states.created < DATE_SUB(UTC_TIMESTAMP(), INTERVAL 5 MINUTE);

DELETE states, events
FROM states
JOIN events ON states.event_id = events.event_id
WHERE
  (
    states.entity_id IN (
      'sensor.cpu_use',
      'sensor.ram_free',
      'sensor.coinbase_price',
      'sensor.ups_input_voltage_2',
      'sensor.ups_load_w_2',
      'sensor.ups_load_2',
      'sensor.ups_battery_2',
      'sensor.ups_time_left_2',
      'sensor.ups_input_voltage',
      'sensor.ups_load_w',
      'sensor.ups_load',
      'sensor.ups_battery',
      'sensor.ups_time_left'
    )
    OR states.entity_id LIKE 'sensor.aeotec_dsb09104_home_energy%'
    OR states.entity_id LIKE 'sensor.dark_sky%'
  )
  AND states.created < DATE_SUB(UTC_TIMESTAMP(), INTERVAL 1 HOUR);
";
