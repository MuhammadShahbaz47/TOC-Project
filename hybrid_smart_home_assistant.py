# ==========================================================
# 🤖 Hybrid CFG + ML Smart Home Assistant
# Enterprise-Style CLI Interface (UI Enhanced Only)
# ==========================================================

import re, uuid, sqlite3, time, threading, sched
from datetime import datetime
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression

# ---------------- TERMINAL UI ----------------
class UI:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"

    @staticmethod
    def line():
        print(f"{UI.GRAY}{'─' * 56}{UI.RESET}")

    @staticmethod
    def section(title):
        UI.line()
        print(f"{UI.BOLD}{UI.CYAN}🔹 {title}{UI.RESET}")
        UI.line()

    @staticmethod
    def info(msg):
        print(f"   {UI.BLUE}ℹ️  {msg}{UI.RESET}")

    @staticmethod
    def success(msg):
        print(f"   {UI.GREEN}✅ {msg}{UI.RESET}")

    @staticmethod
    def warn(msg):
        print(f"   {UI.YELLOW}⚠️  {msg}{UI.RESET}")

    @staticmethod
    def error(msg):
        print(f"   {UI.RED}❌ {msg}{UI.RESET}")

    @staticmethod
    def step(n, msg):
        print(f"\n{UI.BOLD}{UI.CYAN}STEP {n}{UI.RESET} ▸ {msg}")

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
        UI.info("Executing device command")
        time.sleep(0.4)

        if device in self.devices:
            self.devices[device] = state
            UI.success(f"{device.title()} → {state.upper()}")
            return True

        UI.warn("Requested device not found")
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
        UI.info("No room specified → defaulting to Living Room Light")
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
        UI.info("Scheduling reminder (5s demo)")
        self.s.enter(5, 1, lambda: print(
            f"\n{UI.BOLD}{UI.YELLOW}🔔 REMINDER ALERT{UI.RESET}\n"
            f"   ➜ {task.upper()}\n"
        ))

# ---------------- MAIN ASSISTANT ----------------
class SmartHomeAssistant:
    def __init__(self):
        init_db()
        self.ctrl = DeviceController()
        self.ml = MLIntentClassifier()
        self.scheduler = ReminderScheduler()

    def handle(self, command):
        UI.section("USER REQUEST")
        print(f"🗣  {UI.BOLD}{command}{UI.RESET}")

        UI.step(1, "Text Normalization")
        text = normalize(command)
        print(f"   ➜ {text}")

        UI.step(2, "CFG Grammar Evaluation")
        if cfg_device_match(text):
            UI.success("Grammar matched")

            device = extract_device(text)
            state = extract_state(text)

            if not device or not state:
                UI.warn("Device command incomplete (use ON or OFF)")
                log_event(command, "device", "CFG", "failed")
                return

            UI.step(3, "Device Execution (CFG)")
            self.ctrl.set_device(device, state)

            log_event(command, "device", "CFG", "success")
            UI.info("Decision Source → CFG")
            return

        UI.warn("Grammar did not match")

        UI.step(3, "ML Intent Prediction")
        intent = self.ml.predict(text)
        print(f"   ➜ Intent detected: {UI.BOLD}{intent.upper()}{UI.RESET}")

        if intent == "device":
            device = extract_device(text)
            state = extract_state(text)

            if not device or not state:
                UI.warn("Device detected but action missing (use ON or OFF)")
                log_event(command, "device", "ML", "failed")
                return

            UI.step(4, "Device Execution (ML)")
            self.ctrl.set_device(device, state)

            log_event(command, "device", "ML", "success")
            UI.info("Decision Source → ML")
            return

        if intent == "schedule":
            UI.step(4, "Reminder Scheduling")
            self.scheduler.add(command)

            log_event(command, "schedule", "ML", "scheduled")
            UI.info("Decision Source → ML")
            return

        UI.error("Unable to process command")

# ---------------- RUN ----------------
if __name__ == "__main__":
    bot = SmartHomeAssistant()

    print(f"""
╔══════════════════════════════════════════════╗
║   🤖 HYBRID SMART HOME ASSISTANT              ║
║   Offline • Privacy-Preserving • AI-Driven   ║
╚══════════════════════════════════════════════╝
""")

    print("📌 EXAMPLE COMMANDS\n")
    print("  🟢 CFG Based")
    print("     • turn on living room light")
    print("     • switch off kitchen fan\n")

    print("  🟡 ML Based")
    print("     • pls light on")
    print("     • heater on\n")

    print("  🔵 Scheduling")
    print("     • remind me to take medicine\n")

    print("Type 'exit' to quit")
    UI.line()

    while True:
        cmd = input("\n▶ Command: ")
        if cmd.lower() == "exit":
            print("\n👋 Exiting Smart Home Assistant. Goodbye!")
            break
        bot.handle(cmd)
