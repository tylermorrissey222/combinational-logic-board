import threading
import time
import itertools
import os
import pygame
from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO

"""
RFID LOGIC GATE SYSTEM & DISPLAY — 5 Readers (FULL VERSION)

Project Name: Combinational Logic Board
Team Name: Team Won
Team Members: Tyler Morrissey, Dillon O'Brien, Kemarli Thomas

This file is the software architecture implementation for the Combinational Logic Board,
which was originally developed by Tyler Morrissey, a member of Team Won for the Junior Design Project (IECE442). 

We Reserve ALL rights and ownership of this file & its contents, which includes (and not limited) to:
    Functions
    Algorithms
    Classes

The following description outlines the wiring requirements for the RFIDs and Input Switches.

Wiring:
   Reader 1 SDA -> GPIO8  (CE0)
   Reader 2 SDA -> GPIO7  (CE1)
   Reader 3 SDA -> GPIO5
   Reader 4 SDA -> GPIO6
   Reader 5 SDA -> GPIO13

   All readers share: SCK->GPIO11, MOSI->GPIO10, MISO->GPIO9, RST->GPIO25
   
Switches:
   Switch A -> GPIO17, B -> GPIO27, C -> GPIO22, D -> GPIO23, RESET -> GPIO24
   All switches: one leg to GPIO pin, other leg to GND
"""
# Gate UIDs
rfid_gate_map = {
    879477249: "AND",
    3400733702: "AND",
    1193549219: "AND",
    3886782882: "OR",
    2766602469: "OR",
    437713121: "OR",
    656317444: "XOR",
    3877124002: "XOR",
    3840998373: "NAND",
    3348239266: "NAND",
    3882661026: "XNOR",
    1721176838: "XNOR",
    3883018402: "NOR",
    92351519: "NOR",
}

NUM_SLOTS   = 5
INPUT_NAMES = ["A", "B", "C", "D"]
RESET_PIN = 24

# CS pin for each reader slot
CS_PINS     = [8, 7, 5, 6, 13]

# Switch GPIO pins
INPUT_PINS  = [17, 27, 22, 23]   # A, B, C, D

# GATE LOGIC

def evaluate_gate(gate_type, a, b=0):
    """
    This Function describes the logic of each gate that we defined.

    :param gate_type:
    :param a:
    :param b:
    :return:
    """
    if gate_type == "AND":  return a & b
    if gate_type == "OR":   return a | b
    if gate_type == "XOR":  return a ^ b
    if gate_type == "NAND": return 1 - (a & b)
    if gate_type == "NOR":  return 1 - (a | b)
    if gate_type == "NOT":  return 1 - a
    if gate_type == "XNOR": return 1 - (a ^ b)
    return 0


def eval_circuit(slots, inputs):
    """
    Netlist:
      Slot 0: A, B
      Slot 1: B, C
      Slot 2: S0_out, S1_out
      Slot 3: S1_out, D
      Slot 4: S2_out, S3_out -> OUT
    """
    a, b, c, d = inputs
    out0 = evaluate_gate(slots[0], a, b)
    out1 = evaluate_gate(slots[1], b, c)
    out2 = evaluate_gate(slots[2], out0, out1)
    out3 = evaluate_gate(slots[3], out1, d)
    out4 = evaluate_gate(slots[4], out2, out3)
    return out0, out1, out2, out3, out4


def get_truth_table(slots):
    """
    This function builds a truth table from the input slots.
    :param slots:
    :return:
    """
    results = []
    for bits in itertools.product((0, 1), repeat=4):
        _, _, _, _, final = eval_circuit(slots, bits)
        results.append((*bits, final))
    return results


def build_boolean_expr(slots):
    """
    This function builds a boolean expression from the input slots.
    :param slots:
    :return:
    """
    def sym(gate, a, b=None):
        if gate == "AND":   return f"({a}\u00b7{b})"
        if gate == "OR":    return f"({a}+{b})"
        if gate == "XOR":   return f"({a}\u2295{b})"
        if gate == "NAND":  return f"({a}\u00b7{b})'"
        if gate == "NOR":   return f"({a}+{b})'"
        if gate == "NOT":   return f"{a}'"
        if gate == "XNOR":  return f"({a}\u2295{b})'"
        if gate == "EMPTY": return "?"
        return "?"
    e0 = sym(slots[0], "A", "B")
    e1 = sym(slots[1], "B", "C")
    e2 = sym(slots[2], e0, e1)
    e3 = sym(slots[3], e1, "D")
    e4 = sym(slots[4], e2, e3)
    return f"Y = {e4}"


# GPIO INPUT READER

def get_inputs():
    """Read all 4 switch inputs. Returns [A, B, C, D] as 0/1."""
    return [1 if GPIO.input(pin) == GPIO.LOW else 0 for pin in INPUT_PINS]


# RFID THREAD — 5 readers polled in background

slots     = ["EMPTY"] * NUM_SLOTS
rfid_lock = threading.Lock()

reset_event = threading.Event()

def rfid_thread():
    """
    Creates one SimpleMFRC522 per slot using its CS pin.
    Polls all 5 nonblocking — updates slots[] directly.
    """
    readers = []
    for cs in CS_PINS:
        try:
            r = SimpleMFRC522(dev=0, speed=1000000, pin_cs=cs, pin_rst=25)
            readers.append(r)
            print(f"[RFID] Reader on CS {cs} initialized")
        except Exception as e:
            print(f"[RFID] Failed to init reader on CS {cs}: {e}")
            readers.append(None)

    # Track last UID per slot for debounce
    last_uids = [None] * NUM_SLOTS

    while True:
        if reset_event.is_set():
            with rfid_lock:
                for i in range(NUM_SLOTS):
                    slots[i] = "EMPTY"

            last_uids = [None] * NUM_SLOTS
            reset_event.clear()
            print("[RESET] All slots cleared")

        for i, reader in enumerate(readers):
            if reader is None:
                continue
            try:
                uid = reader.read_no_block()
                if uid and uid != last_uids[i]:
                    last_uids[i] = uid
                    gate = rfid_gate_map.get(uid, "EMPTY")
                    with rfid_lock:
                        slots[i] = gate
                    if gate != "EMPTY":
                        print(f"[RFID] Slot {i+1} = {gate}  (UID {uid})")
                    else:
                        print(f"[RFID] Unknown UID on slot {i+1}: {uid}")
                        print(f"       Add:  {uid}: \"GATE_TYPE\"")
                elif not uid and last_uids[i] is not None:
                    # Tag removed — clear debounce so it can be re read
                    last_uids[i] = None
            except Exception as e:
                pass   # ignore transient SPI errors during polling
        time.sleep(0.05)


# PYGAME DISPLAY

SW, SH = 1920, 1080   # change to 1280, 720 for 720p display

pygame.init()
screen      = pygame.display.set_mode((SW, SH), pygame.FULLSCREEN)
pygame.display.set_caption("RFID Logic Gate System")
clock       = pygame.time.Clock()
font        = pygame.font.SysFont("Verdana",   17)
small_font  = pygame.font.SysFont("Verdana",   14)
header_font = pygame.font.SysFont("Verdana",   22, bold=True)
expr_font   = pygame.font.SysFont("dejavusans", 18, bold=True)

# Gate images
base_path   = os.path.dirname(os.path.abspath(__file__))
GATE_IMAGES = {}
for gate in ["AND", "OR", "XOR", "NAND", "NOR", "NOT", "XNOR"]:
    path = os.path.join(base_path, f"{gate}.png")
    try:
        if os.path.exists(path):
            raw  = pygame.image.load(path).convert_alpha()
            surf = pygame.Surface((120, 80))
            surf.fill((255, 255, 255))
            surf.blit(pygame.transform.smoothscale(raw, (120, 80)), (0, 0))
            GATE_IMAGES[gate] = surf
    except Exception as e:
        print(f"[IMG] Could not load {gate}.png: {e}")

GATE_COLORS = {
    "AND": (0,130,220), "OR": (220,100,0), "XOR": (140,0,220),
    "NAND": (220,50,50), "NOR": (50,180,100), "NOT": (180,180,180), "XNOR": (0,150,150)
}

GW, GH = 120, 80

GATE_POS = {
    0: (200, 140),
    1: (200, 440),
    2: (460, 240),
    3: (460, 500),
    4: (720, 360),
}

NODE_R = 14
INPUT_POS = {
    "A": (50, 165),
    "B": (50, 280),
    "C": (50, 545),
    "D": (50, 630),
}

PIN_TOP_Y = int(GH * 0.28)
PIN_BOT_Y = int(GH * 0.72)
PIN_OUT_Y = GH // 2
WIRE_W    = 3
BG_COL    = (18, 22, 34)


def gate_out_pos(idx):
    gx, gy = GATE_POS[idx]; return gx + GW, gy + PIN_OUT_Y

def gate_in_top(idx):
    gx, gy = GATE_POS[idx]; return gx, gy + PIN_TOP_Y

def gate_in_bot(idx):
    gx, gy = GATE_POS[idx]; return gx, gy + PIN_BOT_Y


def wire(p1, p2, val):
    col = (0, 210, 230) if val else (45, 55, 70)
    pygame.draw.line(screen, col, p1, p2, WIRE_W)


def draw_node(name, val, cx, cy):
    col = (0, 210, 230) if val else (60, 65, 80)
    pygame.draw.circle(screen, col, (cx, cy), NODE_R)
    pygame.draw.circle(screen, (140,145,160), (cx, cy), NODE_R, 2)
    v = small_font.render(str(val), True, (10,10,10) if val else (200,205,215))
    screen.blit(v, (cx - v.get_width()//2, cy - v.get_height()//2))
    lbl = small_font.render(name, True, (180,185,200))
    screen.blit(lbl, (cx - NODE_R - lbl.get_width() - 6, cy - lbl.get_height()//2))


def draw_gate_box(idx, gate_type):
    gx, gy = GATE_POS[idx]
    pygame.draw.rect(screen, (255,255,255), (gx, gy, GW, GH))
    if gate_type == "EMPTY":
        pygame.draw.rect(screen, (55,60,75), (gx,gy,GW,GH), 2, border_radius=8)
    else:
        pygame.draw.rect(screen, (220,220,220), (gx,gy,GW,GH), 2, border_radius=8)
    if gate_type not in ("EMPTY", None):
        if GATE_IMAGES.get(gate_type):
            screen.blit(GATE_IMAGES[gate_type], (gx, gy))
            pygame.draw.rect(screen, (220,220,220), (gx,gy,GW,GH), 2, border_radius=8)
        else:
            col = GATE_COLORS.get(gate_type, (100,100,100))
            pygame.draw.rect(screen, col, (gx,gy,GW,GH), border_radius=8)
            lbl = font.render(gate_type, True, (255,255,255))
            screen.blit(lbl, (gx+(GW-lbl.get_width())//2, gy+(GH-lbl.get_height())//2))
    n = small_font.render(f"S{idx+1}", True, (130,135,150))
    screen.blit(n, (gx+GW//2 - n.get_width()//2, gy+GH+4))


def draw_all(slots, inputs):
    """
    This function draws the entire screen.
    :param slots:
    :param inputs:
    :return:
    """
    screen.fill(BG_COL)

    out0, out1, out2, out3, out4 = eval_circuit(slots, inputs)
    a, b, c, d = inputs

    # Header
    screen.blit(header_font.render("RFID Logic Gate System", True, (0,220,220)), (20,12))
    screen.blit(expr_font.render(build_boolean_expr(slots), True, (255,210,0)), (20,44))
    screen.blit(small_font.render("ESC = exit", True, (80,85,100)), (20,76))

    # Input nodes
    for name, (nx, ny) in INPUT_POS.items():
        val = {"A":a,"B":b,"C":c,"D":d}[name]
        draw_node(name, val, nx, ny)

    # A -> S1 top
    ax, ay = INPUT_POS["A"]; t0x, t0y = gate_in_top(0)
    wire((ax+NODE_R, ay), (t0x, ay), a)
    wire((t0x, ay), (t0x, t0y), a)

    # B -> S1 bot + S2 top (shared)
    bx, by = INPUT_POS["B"]
    b0x, b0y = gate_in_bot(0); t1x, t1y = gate_in_top(1)
    jbx = b0x - 18
    wire((bx+NODE_R, by), (jbx, by), b)
    wire((jbx, by), (jbx, b0y), b); wire((jbx, b0y), (b0x, b0y), b)
    wire((jbx, by), (jbx, t1y), b); wire((jbx, t1y), (t1x, t1y), b)
    pygame.draw.circle(screen, (0,210,230) if b else (45,55,70), (jbx, by), 5)

    # C -> S2 bot
    cx2, cy2 = INPUT_POS["C"]; b1x, b1y = gate_in_bot(1)
    wire((cx2+NODE_R, cy2), (b1x, cy2), c)
    wire((b1x, cy2), (b1x, b1y), c)

    # D -> S4 bot
    dx, dy = INPUT_POS["D"]; b3x, b3y = gate_in_bot(3)
    wire((dx+NODE_R, dy), (b3x, dy), d)
    wire((b3x, dy), (b3x, b3y), d)

    # S1 out -> S3 top
    o0x, o0y = gate_out_pos(0); t2x, t2y = gate_in_top(2)
    mid0x = o0x + 20
    wire((o0x, o0y), (mid0x, o0y), out0)
    wire((mid0x, o0y), (mid0x, t2y), out0)
    wire((mid0x, t2y), (t2x, t2y), out0)

    # S2 out -> S3 bot + S4 top (shared)
    o1x, o1y = gate_out_pos(1)
    b2x, b2y = gate_in_bot(2); t3x, t3y = gate_in_top(3)
    mid1x = o1x + 50
    jsy = (b2y + t3y) // 2
    wire((o1x, o1y), (mid1x, o1y), out1)
    wire((mid1x, o1y), (mid1x, jsy), out1)
    wire((mid1x, jsy), (mid1x, b2y), out1); wire((mid1x, b2y), (b2x, b2y), out1)
    wire((mid1x, jsy), (mid1x, t3y), out1); wire((mid1x, t3y), (t3x, t3y), out1)
    pygame.draw.circle(screen, (0,210,230) if out1 else (45,55,70), (mid1x, o1y), 6)

    # S3 out -> S5 top
    o2x, o2y = gate_out_pos(2); t4x, t4y = gate_in_top(4)
    mid2x = o2x + 20
    wire((o2x, o2y), (mid2x, o2y), out2)
    wire((mid2x, o2y), (mid2x, t4y), out2)
    wire((mid2x, t4y), (t4x, t4y), out2)

    # S4 out -> S5 bot
    o3x, o3y = gate_out_pos(3); b4x, b4y = gate_in_bot(4)
    mid3x = o3x + 20
    wire((o3x, o3y), (mid3x, o3y), out3)
    wire((mid3x, o3y), (mid3x, b4y), out3)
    wire((mid3x, b4y), (b4x, b4y), out3)

    # Final output
    o4x, o4y = gate_out_pos(4)
    out_col = (0,220,80) if out4 else (200,60,60)
    pygame.draw.line(screen, out_col, (o4x, o4y), (o4x+70, o4y), WIRE_W)
    screen.blit(font.render("OUT", True, (130,135,150)), (o4x+74, o4y+20))
    pygame.draw.circle(screen, out_col, (o4x+110, o4y), NODE_R)
    v = small_font.render(str(out4), True, (10,10,10))
    screen.blit(v, (o4x+110-v.get_width()//2, o4y-v.get_height()//2))

    # Gate boxes
    for i in range(NUM_SLOTS):
        draw_gate_box(i, slots[i])

    # Truth table
    table  = get_truth_table(slots)
    tx, ty = 1020, 50
    headers = ["A","B","C","D","|","OUT"]
    col_xs  = [tx + i*46 for i in range(6)]
    col_xs[4] -= 6
    screen.blit(header_font.render("Truth Table", True, (0,220,220)), (tx, ty))
    ty += 36
    for ci, h in enumerate(headers):
        screen.blit(font.render(h, True, (0,210,230)), (col_xs[ci], ty))
    ty += 28

    active_row = tuple(inputs)
    for ri, row in enumerate(table):
        is_active = (row[:4] == active_row)
        if is_active:
            pygame.draw.rect(screen, (35,58,88),
                             (tx-8, ty+ri*24-3, 262, 22), border_radius=4)
            pygame.draw.rect(screen, (0,160,200),
                             (tx-8, ty+ri*24-3, 262, 22), 1, border_radius=4)
        for ci in range(6):
            if ci == 4:
                screen.blit(small_font.render("|", True, (70,75,90)),
                            (col_xs[4], ty+ri*24))
                continue
            val    = row[ci] if ci < 4 else row[4]
            x      = col_xs[ci] if ci < 4 else col_xs[5]
            is_out = (ci == 5)
            if is_active:
                col = (0,235,255) if (is_out and val==1) else (255,255,255)
            else:
                col = (0,210,230) if (is_out and val==1) else (170,175,185)
            screen.blit(small_font.render(str(val), True, col), (x, ty+ri*24))


# MAIN

def main():
    # Setup switch GPIO pins
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in INPUT_PINS:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    GPIO.setup(RESET_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    # Start RFID polling thread
    t = threading.Thread(target=rfid_thread, daemon=True)
    t.start()

    running = True

    try:
        while running:
            inputs = get_inputs()

            if GPIO.input(RESET_PIN) == GPIO.HIGH:
                reset_event.set()
                time.sleep(0.25)  # simple debounce delay

            with rfid_lock:
                current_slots = slots[:]

            draw_all(current_slots, inputs)
            pygame.display.flip()
            clock.tick(30)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

    finally:
        GPIO.cleanup()
        pygame.quit()


if __name__ == "__main__":
    main()