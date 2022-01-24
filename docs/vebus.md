# VE.Bus Cheatsheet

Sourced from (Victron Energy)[https://www.victronenergy.com/support-and-downloads/technical-information], click on "Interfacing with VE Bus products - MK2 protocol" and put in an email address to get access to their PDF documentation.

## Commands

* Get Version
  * Code: `buildFrame('V')`
  * Request: `\x02\xff\x56\xa9`
  * Response: `\x07\xff\x56\x24\xdb\x11\x00\x00\x94`
* Get LEDs
  * `buildFrame('L')`
  * Request: `\x02\xff\x4c\xb3`
  * Response: `\x08\xff\x4c\x09\x00\x00\x00\x80\x00\x24`
* Get DC Info
  * `buildFrame('F', '\x00')`
  * Request: `\x03\xff\x46\x00\xb8`
  * Response: `\x0f\x20\x8b\x5f\xc8\x03\x0c\x92\x15\x00\x00\x00\x00\x00\x00\x45\x24`
* Get AC Info
  * `buildFrame('F', '\x01')`
  * Request: `\x03\xff\x46\x01\xb7`
  * Response: `\x0f\x20\x01\x01\x01\x09\x08\x1d\x60\xdf\x00\x1d\x60\xaf\x00\xa2\x93`

## LED Frame

Data   | Meaning
-------|---
`\x08` | length
`\xff` | padding
`\x4c` | command 'L'
`\x09` | leds on
`\x00` | leds blinking
`\x00` | ???
`\x00` | ???
`\x80` | ???
`\x00` | ???
`\x24` | checksum

### LEDs

Bit | LED
----|---
0   | Mains
1   | Absorption
2   | Bulk
3   | Float
4   | Inverter
5   | Overload
6   | Low Battery
7   | Temperature

### LEDs On

```text
\x09 = 00001001
           |  ^ bit 0 (Mains)
           ^ bit 3 (Float)
```

### LEDs Blinking

```text
\x00 = 00000000
No bits set
```

## DC Frame

Data   | Meaning
-------|---
`\x0f` | length
`\x20` | info frame
`\x8b` | `0`  reserved
`\x5f` | `1`  reserved
`\xc8` | `2`  reserved
`\x03` | `3`  reserved
`\x0c` | `4`  phase info
`\x92` | `5`  dc voltage
`\x15` | `6`  ^
`\x00` | `7`  dc current used by inverting devices
`\x00` | `8`  ^
`\x00` | `9`  ^
`\x00` | `10` dc current provided by charging devices
`\x00` | `11` ^
`\x00` | `12` ^
`\x45` | `13` inverter period
`\x24` | checksum

### Phase Info

Value   | Meaning
--------|---
`\x05`  | This frame describes L4.
`\x06`  | This frame describes L3.
`\x07`  | This frame describes L2.
`\x08`  | This frame describes L1, there is 1 phase in this system.
`\x09`  | This frame describes L1, there are 2 phases in this system.
`\x0A`  | This frame describes L1, there are 3 phases in this system.
`\x0B`  | This frame describes L1, there are 4 phases in this system.
`\x0C`  | This in a DC frame.

Phase info in the example data is `\x0c` so this is a DC frame.

### DC Voltage

2 byte, unsigned int, little endian

```text
\x92\x15 = 5522 / 100 = 55.2v
```

Using unpack: `unpack('<H', '\x92\x15')`

`<` means little endian: https://docs.python.org/3/library/struct.html#byte-order-size-and-alignment

`H` means short (2 byte int, unsigned): https://docs.python.org/3/library/struct.html#format-characters

### DC Current Used

3 byte, unsigned int, little endian

```text
\x00\x00\x00 = 0 / 100 = 0.00A
```

Using unpack: `unpack('<I', '\x00\x00\x00' + '\x00)`

We have to pad with another (empty byte) because `I` means 4 byte int (signed).

## DC Current Provided

3 byte, unsigned int, little endian

```text
\x00\x00\x00 = 0 / 100 = 0.00A
```

Using unpack: `unpack('<I', '\x00\x00\x00' + '\x00)`

We have to pad with another (empty byte) because `I` means 4 byte int (unsigned).

### Inverter Period

1 byte, unsigned int, little endian

```text
\x45 = 69
(10 / 69) * 1000 = 144.92hz
```

Using unpack: `unpack('<B', '\x45)`

`B` means short (1 byte int, unsigned).

I don't know why this shows such a high frequency, ~60Hz was expected, but this seems to return ~144Hz when the inverter is on and off.

## AC Frame

Data   | Meaning
-------|---
`\x0f` | length |
`\x20` | info frame
`\x01` | `0`  bf factor
`\x01` | `1`  inverter factor
`\x01` | `2`  reserved
`\x09` | `3`  state
`\x08` | `4`  phase info
`\x1d` | `5`  mains voltage
`\x60` | `6`  ^
`\xdf` | `7`  mains current
`\x00` | `8`  ^
`\x1d` | `9`  inverter voltage
`\x60` | `10` ^
`\xaf` | `11` inverter current
`\x00` | `12` ^
`\xa2` | `13` mains period
`\x93` | checksum

### BF Factor

This is used to correctly calculate current later.
`\x01` = 1

### Inverter Factor

This is used to correctly calculate current later.
`\x01` = 1

### State

Value   | Meaning
--------|---
`\x00`  | Down
`\x01`  | Startup
`\x02`  | Off
`\x03`  | Slave
`\x04`  | InvertFull
`\x05`  | InvertHalf
`\x06`  | InvertAES
`\x07`  | PowerAssist
`\x08`  | Bypass
`\x09`  | Charge

State example is `\x09` so the state is "Charge".

### Phase Info (AC)

The loopup table is the same as for DC frames. Phase info in the example data is `\x08` so this is an AC frame that describes L1 and there is only 1 phase in the system.

### Mains Voltage

2 byte, unsigned int, little endian

```text
\xdf\x00 =  223 / 100 = 2.23A
```

Using unpack: `unpack('<H', '\xdf\x00')`

### Mains Current

2 byte, unsigned int, little endian

```text
\x1d\x60 =  24605 / 100 = 246.05v
```

Using unpack: `unpack('<H', '\x1d\x60')`

### Inverter Voltage

2 byte, unsigned int, little endian

```text
\x1d\x60 =  24605 / 100 = 246.05v
```

Using unpack: `unpack('<H', '\x1d\x60')`

### Inverter Current

2 byte, unsigned int, little endian

```text
\xaf\x00 =  175 / 100 = 1.75A
```

Using unpack: `unpack('<H', '\xaf\x00')`

### Mains Period

1 byte, unsigned int, little endian

```text
\xa2 = 162
(10 / 162) * 1000 = 61.72hz
```

Using unpack: `unpack('<B', '\x45)`

`B` means short (1 byte int, unsigned).
