# Combinational Logic Board

### IECE 442 — Systems Analysis & Design

**Created by Tyler Morrissey**

-----

## Overview

An educational RFID based logic gate simulator that allows
students to physically place gate tokens on RFID readers to
build and simulate combinational logic circuits in real time.

The system evaluates a 5 gate combinational circuit, displays
a live schematic with wire states, generates the Boolean
expression, and shows a truth table with the active input
row highlighted.

-----

## Hardware

### Version 1 & 1.5

- Raspberry Pi 3B — display and GPIO switches
- Arduino Mega — 5x RC522 RFID readers
- Custom PCB bus board (KiCad)
- 5x RC522 RFID readers
- 4x input switches
- Sotsu FlipAction Go 14” display

### Version 2 (in development)

- Raspberry Pi CM5 — display
- Raspberry Pi Pico 2 — RFID readers and switches
- Custom PCB with integrated Pico socket (KiCad)

-----

## Supported Gate Types

|Gate|Symbol|
|----|------|
|AND |A·B   |
|OR  |A+B   |
|XOR |A⊕B   |
|NAND|(A·B)’|
|NOR |(A+B)’|
|XNOR|(A⊕B)’|

-----

## Features

- Real time circuit simulation
- Live truth table with active row highlight
- Boolean expression generation
- Full adder auto detection mode
- Scalable pygame display (SCALE variable)
- Arduino/Pico handles RFID over Serial to Pi

-----

## Circuit Netlist

```
Slot 1: A, B     → Gate 1 output
Slot 2: B, C     → Gate 2 output
Slot 3: G1, G2   → Gate 3 output
Slot 4: G2, D    → Gate 4 output
Slot 5: G3, G4   → Final output Y
```

-----

## Files

### Code

|File                        |Description                        |
|----------------------------|-----------------------------------|
|code/arduino_rfid.ino       |Arduino RFID reader sketch         |
|code/rfid_display_arduino.py|Pi display script                  |
|code/display_test_mac.py    |Mac simulation (no hardware needed)|

### PCB

|Folder      |Description                           |
|------------|--------------------------------------|
|pcb/v1/     |V1 bus board — Arduino to RC522       |
|pcb/v2_pico/|V2 Pico board — integrated Pico socket|

-----

## Setup

### Hardware Setup

1. Connect Arduino Mega to Pi via USB
1. Wire 5x RC522 readers to Arduino per wiring guide
1. Wire 4x switches to Pi GPIO
1. Connect display via HDMI

### Software Setup

```bash
# On Raspberry Pi
pip3 install pyserial pygame RPi.GPIO

# Run display
python3 rfid_display_arduino.py
```

### Running Mac Simulation

```bash
pip3 install pygame
python3 display_test_mac.py
```

-----

## Wiring

### Arduino Mega — RC522 Readers

```
MOSI → Pin 51
MISO → Pin 50
SCK  → Pin 52
RST  → Pin 44
CS1  → Pin 38
CS2  → Pin 40
CS3  → Pin 39
CS4  → Pin 43
CS5  → Pin 49
```

### Raspberry Pi — Input Switches

```
Switch A → GPIO17
Switch B → GPIO27
Switch C → GPIO22
Switch D → GPIO23
GND      → GND
```

-----

## Gate Token UIDs

Add your RFID tag UIDs to the Arduino sketch getGate() function:

```cpp
if (uid == "YOUR_UID") return "AND";
```

Scan unknown tags with the Arduino — UIDs print to Serial Monitor.

-----

## License

MIT License — free to use and modify
