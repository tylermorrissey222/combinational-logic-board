/*
THIS FILE IS INTERNAL ONLY, DO NOT ADD THIS TO GITHUB

RFID MULTI READER — Arduino Mega
5 RC522 readers, sends gate assignments to Pi over Serial

Wiring:
   All readers share: MOSI->51, MISO->50, SCK->52, RST->44

CHECK ALL THESE FPR ACCURACY
   Reader 1 CS -> Pin 49 
   Reader 2 CS -> Pin 53
   Reader 3 CS -> Pin 38
   Reader 4 CS -> Pin 46
   Reader 5 CS -> Pin 45

   All readers: 3.3V -> 3.3V, GND -> GND
*/

#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN  44
#define NUM_READERS 5

// CS pins for each reader 38 39 40 43 49 {49, 53, 38, 46, 45};
const int CS_PINS[NUM_READERS] = {38, 40, 39, 43, 49};

// Create reader instances
MFRC522 readers[NUM_READERS] = {
    MFRC522(CS_PINS[0], RST_PIN),
    MFRC522(CS_PINS[1], RST_PIN),
    MFRC522(CS_PINS[2], RST_PIN),
    MFRC522(CS_PINS[3], RST_PIN),
    MFRC522(CS_PINS[4], RST_PIN)
};

// UID to gate type mapping
String getGate(String uid) {
    if (uid == "346BC201") return "AND";
    if (uid == "CAB31406") return "AND";
    if (uid == "47241DA3") return "AND";
    if (uid == "E7AB99A2")  return "OR";
    if (uid == "A4E700E5")  return "OR";
    if (uid == "1A16F8E1")  return "OR";
    if (uid == "271E9C04")  return "XOR";
    if (uid == "E71837A2")  return "XOR";
    if (uid == "E4F0FBE5")  return "NAND";
    if (uid == "C79213A2")  return "NAND";
    if (uid == "E76CB4A2")  return "XNOR";
    if (uid == "66971306")  return "XNOR";
    if (uid == "E77228A2")  return "NOR";
    if (uid == "05812C1F")  return "NOR";
    return "EMPTY";
}

// Current gate in each slot
String slots[NUM_READERS] = {
    "EMPTY", "EMPTY", "EMPTY", "EMPTY", "EMPTY"
};

// Track last UID per slot for debounce
String lastUIDs[NUM_READERS] = {"", "", "", "", ""};

// SETUP
void setup() {
    Serial.begin(9600);   // USB Serial to Pi

    SPI.begin();

    // Init all readers
    for (int i = 0; i < NUM_READERS; i++) {
        readers[i].PCD_Init();
        delay(50);

        // Version check
        byte ver = readers[i].PCD_ReadRegister(MFRC522::VersionReg);
        Serial.print("[RFID] Reader ");
        Serial.print(i + 1);
        Serial.print(" CS=");
        Serial.print(CS_PINS[i]);
        Serial.print(" version=");
        Serial.print(ver, HEX);
        if (ver == 0x91 || ver == 0x92 || ver == 0x82 || ver == 0x88 || ver == 0xB2) {
            Serial.println(" OK");
        } else {
            Serial.println(" CHECK WIRING");
        }
    }

    Serial.println("[READY]");
    sendSlots();   // send initial empty state to Pi
}


// Build UID string from card serial
String getUID(MFRC522 &reader) {
    String uid = "";
    for (byte i = 0; i < reader.uid.size; i++) {
        if (reader.uid.uidByte[i] < 0x10) uid += "0";
        uid += String(reader.uid.uidByte[i], HEX);
    }
    uid.toUpperCase();
    return uid;
}

// Send all slot states to Pi
// Format: "S1:AND,S2:OR,S3:EMPTY,S4:NAND,S5:XNOR\n"
void sendSlots() {
    String msg = "";
    for (int i = 0; i < NUM_READERS; i++) {
        msg += "S" + String(i + 1) + ":" + slots[i];
        if (i < NUM_READERS - 1) msg += ",";
    }
    Serial.println(msg);
}

// MAIN LOOP

void loop() {
    bool changed = false;

    for (int i = 0; i < NUM_READERS; i++) {
        if (readers[i].PICC_IsNewCardPresent() &&
            readers[i].PICC_ReadCardSerial()) {

            String uid  = getUID(readers[i]);
            String gate = getGate(uid);

            // Only update if this is a different tag than last time
            if (uid != lastUIDs[i]) {
                lastUIDs[i] = uid;   
                slots[i]    = gate;
                changed     = true;

                if (gate != "EMPTY") {
                    Serial.print("[RFID] Slot ");
                    Serial.print(i + 1);
                    Serial.print(" = ");
                    Serial.print(gate);
                    Serial.print("  UID: ");
                    Serial.println(uid);
                } else {
                    Serial.print("[RFID] Unknown UID slot ");
                    Serial.print(i + 1);
                    Serial.print(": ");
                    Serial.println(uid);
                    Serial.println("       Add to getGate()");
                }
            }

            readers[i].PICC_HaltA();
            readers[i].PCD_StopCrypto1();
        }
        
        delay(10);
    }

    if (changed) {
        sendSlots();
    }

    delay(50);

    // Reset button, possibly add extra rfid tag as a reset
    /*
    if (digitalRead(2) == LOW) {
    for (int i = 0; i < NUM_READERS; i++) {
        lastUIDs[i] = "";
        slots[i] = "EMPTY";
    }
    changed = true;
    Serial.println("[RESET] All slots cleared");
    }
    */
}
