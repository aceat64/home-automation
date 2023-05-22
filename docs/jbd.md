# JBD BMS Cheat Sheet

Sourced from: https://gitlab.com/bms-tools/bms-tools/-/blob/master/JBD_REGISTER_MAP.md

## Get Info (`\x03`)

### Command

| Data   | Meaning                       |
| ------ | ----------------------------- |
| `\xdd` | start                         |
| `\xa5` | command: read                 |
| `\x03` | register address (basic info) |
| `\x00` | length of data                |
| `\xff` | checksum byte1                |
| `\xfd` | checksum byte2                |
| `\x77` | end                           |

Checksum is `\x10000` (65536) minus the sum of the payload.

Payload is the register address, length of data (0 if no data being sent) and the data bytes. Payload does _not_ include the command (e.g. `\xa5`).

### Response

| Data   | Meaning                              |
| ------ | ------------------------------------ |
| `\xdd` | start                                |
| `\x03` | register address                     |
| `\x00` | status (`\x00` = ok, `\x80` = error) |
| `\x1d` | length of data                       |
| `\x15` | pack_mv (unsigned)                   |
| `\x84` | ^                                    |
| `\x00` | pack_ma (signed)                     |
| `\x00` | ^                                    |
| `\x6c` | cycle_cap (unsigned)                 |
| `\xa6` | ^                                    |
| `\x6d` | design_cap (unsigned)                |
| `\x60` | ^                                    |
| `\x00` | cycle_cnt (unsigned)                 |
| `\x00` | ^                                    |
| `\x2b` | Manufacture date                     |
| `\x56` | ^                                    |
| `\x00` | Cell balance status                  |
| `\x00` | ^                                    |
| `\x00` | Cell balance status 2                |
| `\x00` | ^                                    |
| `\x00` | Errors                               |
| `\x00` | ^                                    |
| `\x20` | version (unsigned?)                  |
| `\x63` | cap_pct (unsigned?)                  |
| `\x03` | FET status                           |
| `\x10` | cell_cnt (unsigned)                  |
| `\x03` | ntc_cnt (unsigned)                   |
| `\x0b` | ntc0 (signed?)                       |
| `\x29` | ^                                    |
| `\x0b` | ntc1 (signed?)                       |
| `\x1a` | ^                                    |
| `\x0b` | ntc2 (signed?)                       |
| `\x2c` | ^                                    |
| `\xfb` | checksum byte1                       |
| `\xc1` | checksum byte2                       |
| `\x77` | end                                  |

For calculating the checksum, payload does _not_ include the register address (e.g. `\x03`).

## Get Cell Voltages (`\x04`)

### Command

| Data   | Meaning                          |
| ------ | -------------------------------- |
| `\xdd` | start                            |
| `\xa5` | command: read                    |
| `\x04` | register address (cell voltages) |
| `\x00` | length of data                   |
| `\xff` | checksum byte1                   |
| `\xfc` | checksum byte2                   |
| `\x77` | end                              |

### Response

| Data   | Meaning                              |
| ------ | ------------------------------------ |
| `\xdd` | start                                |
| `\x04` | register address                     |
| `\x00` | status (`\x00` = ok, `\x80` = error) |
| `\x20` | length of data                       |
| `\x??` | cell0_mv                             |
| `\x??` | ^                                    |
| `\x??` | cell1_mv                             |
| `\x??` | ^                                    |
| ...    | ...                                  |
| `\x??` | cellN_mv                             |
| `\x??` | ^                                    |
| `\x??` | checksum byte1                       |
| `\x??` | checksum byte2                       |
| `\x77` | end                                  |
