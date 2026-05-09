# combinational-logic-board
RFID Based Logic Simulator
# Combinational Logic Board
**Created by Tyler Morrissey**

## Overview
An educational RFID-based logic gate simulator allowing students 
to physically place gate tokens on RFID readers to build and 
simulate combinational logic circuits in real time.

## Hardware
- Raspberry Pi 3B
- Arduino Mega
- 5× RC522 RFID readers
- Custom PCB bus board (KiCad)
- Raspberry Pi Pico 2 (v2)

## Gate Types Supported
AND, OR, XOR, NAND, NOR, XNOR

## Features
- Real time circuit simulation
- Live truth table with active row highlight  
- Boolean expression generation
- Full adder auto detection mode
- Scalable pygame display

## Files
- `code/arduino_rfid.ino` — Arduino RFID reader sketch
- `code/rfid_display_arduino.py` — Pi display script
- `code/display_test_mac.py` — Mac simulation
- `pcb/` — KiCad and Gerber files

## Setup
See [setup guide](docs/setup.md)
