# ==========================================================
# Hybrid CFG + ML Smart Home Assistant
# ==========================================================

import re, uuid, sqlite3, time, threading, sched
from datetime import datetime
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression

# ---------------- CONFIG ----------------
DB_NAME = "smart_home.db"
DEFAULT_LIGHT = "living room light"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id TEXT PRIMARY KEY,
            time TEXT,
            command TEXT,
            intent TEXT,
            source TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_event(cmd, intent, source, status):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO logs VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), datetime.now().isoformat(),
         cmd, intent, source, status)
    )
    conn.commit()
    conn.close()

# ---------------- DEVICE CONTROLLER ----------------
class DeviceController:
    def __init__(self):
        self.devices = {
            "living room light": "off",
            "kitchen fan": "off",
            "bedroom heater": "off"
        }

    def set_device(self, device, state):
        print("   ⚙️  Executing device action...")
        time.sleep(0.4)
        if device in self.devices:
            self.devices[device] = state
            print(f"   ✅  {device.title()} → {state.upper()}")
            return True
        print("   ⚠️  Device not found")
        return False

# ---------------- NORMALIZATION ----------------
def normalize(text):
    return re.sub(r"[^\w\s]", "", text.lower())

# ---------------- CFG MATCH ----------------
def cfg_device_match(text):
    patterns = [
        r"(turn|switch)\s+(on|off)\s+(living room light|kitchen fan|bedroom heater)",
        r"(living room light|kitchen fan|bedroom heater)\s+(on|off)"
    ]
    return any(re.search(p, text) for p in patterns)

# ---------------- ML CLASSIFIER ----------------
class MLIntentClassifier:
    def __init__(self):
        self.vec = CountVectorizer()
        self.model = LogisticRegression()

        training_data = [
            ("turn on living room light", "device"),
            ("switch off kitchen fan", "device"),
            ("pls light on", "device"),
            ("heater on", "device"),
            ("light on", "device"),
            ("remind me to take medicine", "schedule"),
        ]

        X = [x[0] for x in training_data]
        y = [x[1] for x in training_data]

        self.model.fit(self.vec.fit_transform(X), y)

    def predict(self, text):
        return self.model.predict(self.vec.transform([text]))[0]

# ---------------- SEMANTIC EXTRACTION ----------------
def extract_device(text):
    if "living" in text and "light" in text:
        return "living room light"
    if "kitchen" in text and "fan" in text:
        return "kitchen fan"
    if "heater" in text:
        return "bedroom heater"

    if "light" in text:
        print("   ℹ️  No room specified → defaulting to Living Room Light")
        return DEFAULT_LIGHT

    return None

def extract_state(text):
    if "on" in text:
        return "on"
    if "off" in text:
        return "off"
    return None

# ---------------- REMINDER ----------------
class ReminderScheduler:
    def __init__(self):
        self.s = sched.scheduler(time.time, time.sleep)
        threading.Thread(target=self.s.run, daemon=True).start()

    def add(self, task):
        print("   ⏳  Scheduling reminder (5s demo)...")
        self.s.enter(5, 1, lambda: print(
            f"\n🔔  REMINDER ALERT\n   ➜ {task.upper()}\n"))

# ---------------- MAIN ASSISTANT ----------------
class SmartHomeAssistant:
    def __init__(self):
        init_db()
        self.ctrl = DeviceController()
        self.ml = MLIntentClassifier()
        self.scheduler = ReminderScheduler()

    def handle(self, command):
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"🗣  USER INPUT")
        print(f"   ➜ {command}")

        text = normalize(command)
        print("\n🔤  STEP 1: NORMALIZATION")
        print(f"   ➜ {text}")

        print("\n📐  STEP 2: CFG PARSING")
        if cfg_device_match(text):
            print("   ✅ Grammar matched")
            device = extract_device(text)
            state = extract_state(text)

            print("\n⚙️  STEP 3: EXECUTION (CFG)")
            self.ctrl.set_device(device, state)
            log_event(command, "device", "CFG", "success")

            print("\n🧠  DECISION SOURCE → CFG")
            return

        print("   ❌ Grammar failed")

        print("\n🤖  STEP 3: ML INTENT PREDICTION")
        intent = self.ml.predict(text)
        print(f"   ➜ Intent = {intent.upper()}")

        if intent == "device":
            device = extract_device(text)
            state = extract_state(text)

            print("\n⚙️  STEP 4: EXECUTION (ML)")
            self.ctrl.set_device(device, state)
            log_event(command, "device", "ML", "success")

            print("\n🧠  DECISION SOURCE → ML")
            return

        if intent == "schedule":
            print("\n⏰  STEP 4: SCHEDULING")
            self.scheduler.add(command)
            log_event(command, "schedule", "ML", "scheduled")

            print("\n🧠  DECISION SOURCE → ML")
            return

        print("\n❌  Unable to process command")

# ---------------- RUN ----------------
if __name__ == "__main__":
    bot = SmartHomeAssistant()

    print("\n╔════════════════════════════════════════╗")
    print("║   🤖 HYBRID SMART HOME ASSISTANT        ║")
    print("║   Privacy-Preserving | Offline         ║")
    print("╚════════════════════════════════════════╝")

    print("\n📌 EXAMPLE COMMANDS YOU CAN USE:\n")

    print("  🟢 Grammar-Based (CFG)")
    print("     • turn on living room light")
    print("     • switch off kitchen fan\n")

    print("  🟡 Short / Noisy (ML)")
    print("     • pls light on")
    print("     • heater on\n")

    print("  🔵 Scheduling (ML)")
    print("     • remind me to take medicine\n")

    print("Type 'exit' to quit")
    print("────────────────────────────────────────")

    while True:
        cmd = input("\n▶ Command: ")
        if cmd.lower() == "exit":
            print("\n👋 Exiting Smart Home Assistant. Goodbye!")
            break
        bot.handle(cmd)
