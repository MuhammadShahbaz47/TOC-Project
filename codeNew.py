# ===============================================
# INTERACTIVE SMART HOME ASSISTANT (Colab Ready)
# Updated version with 🕒 & ⚠️ user feedback
# ===============================================

import re, time, uuid, json, sqlite3, threading, sched, logging
from datetime import datetime, timedelta

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SmartHome")

# ---------- Database ----------
DB_FILENAME = "smart_home_interactive.db"

def init_db():
    conn = sqlite3.connect(DB_FILENAME)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        ts_created TEXT,
        command_text TEXT,
        action_type TEXT,
        target TEXT,
        scheduled_time TEXT,
        status TEXT,
        meta TEXT
    )''')
    conn.commit(); conn.close()

def persist_event(ev: dict):
    conn = sqlite3.connect(DB_FILENAME)
    cur = conn.cursor()
    cur.execute('''INSERT OR REPLACE INTO events
        (id, ts_created, command_text, action_type, target, scheduled_time, status, meta)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (ev['id'], ev['ts_created'], ev['command_text'], ev['action_type'],
         ev.get('target') or '', ev.get('scheduled_time') or '',
         ev.get('status') or 'scheduled', json.dumps(ev.get('meta') or {})))
    conn.commit(); conn.close()

# ---------- Device Controller ----------
class DeviceController:
    def __init__(self):
        self.devices = {
            'living room lights': {'state': 'off'},
            'kitchen fan': {'state': 'off'},
            'bedroom heater': {'state': 'off'},
            'bathroom lights': {'state': 'off'},
            'air conditioner': {'state': 'off'}
        }
        self.lock = threading.Lock()

    def list_devices(self):
        return list(self.devices.keys())

    def set_device(self, name, state):
        name = name.strip().replace("  ", " ")
        with self.lock:
            if name in self.devices:
                old = self.devices[name]['state']
                self.devices[name]['state'] = state
                logger.info(f"✅ {name}: {old} → {state}")
                return True
            logger.warning(f"⚠️ Unknown device '{name}'")
            return False

# ---------- Tokenizer ----------
def tokenize(s):
    s = s.strip().lower()
    s = re.sub(r'[.,;!?]', '', s)
    return s.split()

# ---------- Grammar ----------
GRAMMAR = {
 "COMMAND":[["ACTION"],["SCHEDULE"]],
 "ACTION":[["VERB","SWITCH","DEVICE"]],
 "VERB":[["turn"],["switch"]],
 "SWITCH":[["on"],["off"]],
 "DEVICE":[["the","ROOM","DEVICE_NP"],["DEVICE_NP","in","ROOM"],["DEVICE_NP"]],
 "ROOM":[["living","room"],["kitchen"],["bedroom"],["bathroom"]],
 "DEVICE_NP":[["light"],["lights"],["fan"],["heater"],["air","conditioner"]],
 "SCHEDULE":[["REMIND_PHRASE","TASK","TIME_PHRASE"]],
 "REMIND_PHRASE":[["remind","me","to"],["set","alarm","for"],["schedule","a"]],
 "TASK":[["take","medicine"],["water","the","plants"],["meeting","with","team"],["read","the","book"]],
 "TIME_PHRASE":[["at","TIME"],["after","DURATION"],["tomorrow","at","TIME"]],
 "TIME":[["6","pm"],["7","am"],["3","pm"],["9","am"]],
 "DURATION":[["1","hour"],["2","hours"],["30","minutes"]]
}

def parse_symbol(sym, tokens, i, trace):
    if sym not in GRAMMAR:
        if i < len(tokens) and tokens[i] == sym:
            trace.append(f"✓ Matched '{sym}'")
            return True, i + 1
        trace.append(f"❌ Expected '{sym}', got '{tokens[i] if i < len(tokens) else 'EOF'}'")
        return False, i
    for prod in GRAMMAR[sym]:
        j = i; ok = True
        trace.append(f"Expanding {sym} → {' '.join(prod)}")
        for s2 in prod:
            ok, j = parse_symbol(s2, tokens, j, trace)
            if not ok: break
        if ok: return True, j
        trace.append(f"Backtrack on {sym} → {' '.join(prod)}")
    return False, i

def parse_command(tokens):
    trace = []
    ok, idx = parse_symbol("COMMAND", tokens, 0, trace)
    return ok and idx == len(tokens), trace

# ---------- Interpreter ----------
def parse_time_of_day(t, ref=None):
    ref = ref or datetime.now()
    m = re.match(r'(\d{1,2})\s*(am|pm)', t)
    if not m: raise ValueError
    h = int(m.group(1)); ampm = m.group(2)
    if ampm == 'pm' and h != 12: h += 12
    if ampm == 'am' and h == 12: h = 0
    dt = ref.replace(hour=h, minute=0, second=0, microsecond=0)
    if dt <= ref: dt += timedelta(days=1)
    return dt

def parse_duration(num, unit, ref=None):
    ref = ref or datetime.now()
    if 'hour' in unit: return ref + timedelta(hours=num)
    return ref + timedelta(minutes=num)

def interpret(text):
    joined = " ".join(tokenize(text))
    result = {'command_text': text, 'action_type': None, 'device': None,
              'task': None, 'scheduled_time': None, 'state': None}
    # Device control
    m = re.search(r'(turn|switch)\s+(on|off)\s+(?:the\s+)?((?:living|kitchen|bedroom|bathroom)\s+)?(lights?|fan|heater|air conditioner)', joined)
    if m:
        room = (m.group(3) or '').strip()
        device = (room + " " + m.group(4)).strip()
        result.update({'action_type': 'device', 'device': device, 'state': m.group(2)})
        return result
    # Reminder/schedule
    m = re.search(r'(remind me to|set alarm for|schedule a)\s+(.+?)\s+(at\s+\d{1,2}\s*(?:am|pm)|after\s+\d+\s+(?:hours|minutes)|tomorrow\s+at\s+\d{1,2}\s*(?:am|pm))', joined)
    if m:
        phrase = m.group(3)
        if 'after' in phrase:
            n = int(re.search(r'(\d+)', phrase).group(1))
            unit = 'hours' if 'hour' in phrase else 'minutes'
            t = parse_duration(n, unit)
        elif 'tomorrow' in phrase:
            hr = re.search(r'(\d{1,2}\s*(?:am|pm))', phrase).group(1)
            t = parse_time_of_day(hr, datetime.now() + timedelta(days=1))
        else:
            hr = re.search(r'(\d{1,2}\s*(?:am|pm))', phrase).group(1)
            t = parse_time_of_day(hr)
        result.update({'action_type': 'schedule', 'task': m.group(2).strip(), 'scheduled_time': t})
        return result
    return result

# ---------- Scheduler ----------
class AssistantScheduler:
    def __init__(self, ctrl):
        self.ctrl = ctrl
        self.sched = sched.scheduler(time.time, time.sleep)
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        while True:
            self.sched.run(blocking=False)
            time.sleep(0.5)

    def add(self, t, func, meta):
        self.sched.enterabs(t.timestamp(), 1, func, argument=(meta,))

# ---------- Main Assistant ----------
class SmartHomeAssistant:
    def __init__(self):
        init_db()
        self.ctrl = DeviceController()
        self.scheduler = AssistantScheduler(self.ctrl)

    def handle(self, text):
        tokens = tokenize(text)
        ok, trace = parse_command(tokens)
        sem = interpret(text)
        now = datetime.now()

        if sem['action_type'] == 'device':
            done = self.ctrl.set_device(sem['device'], sem['state'])
            ev = {'id': str(uuid.uuid4()), 'ts_created': now.isoformat(), 'command_text': text,
                  'action_type': 'device', 'target': sem['device'], 'scheduled_time': '',
                  'status': 'done' if done else 'failed', 'meta': {'state': sem['state']}}
            persist_event(ev)
            return {"ok": ok, "trace": trace,
                    "result": "✅ Device command executed" if done else "⚠️ Unknown device"}

        elif sem['action_type'] == 'schedule':
            def remind(m):
                print(f"\n🔔 Reminder Alert: {m.get('task')} (Triggered at {datetime.now().strftime('%H:%M:%S')})\n")
            self.scheduler.add(sem['scheduled_time'], remind, {'task': sem['task']})
            ev = {'id': str(uuid.uuid4()), 'ts_created': now.isoformat(), 'command_text': text,
                  'action_type': 'schedule', 'target': sem['task'],
                  'scheduled_time': sem['scheduled_time'].isoformat(), 'status': 'scheduled', 'meta': {}}
            persist_event(ev)
            return {"ok": ok, "trace": trace, "result": f"🕒 Reminder set for {sem['scheduled_time']}"}

        else:
            return {"ok": False, "trace": trace, "result": "❌ Command not recognized"}

# ---------- Interactive Mode (Improved Output) ----------
def interactive_mode():
    bot = SmartHomeAssistant()
    print("🤖 Smart Home Assistant (Interactive Mode)")
    print("Type 'exit' to quit.")
    print("--------------------------------------------\n")

    while True:
        cmd = input("Enter command: ").strip()
        if cmd.lower() == 'exit':
            print("👋 Exiting... Goodbye!")
            break

        res = bot.handle(cmd)
        print("\n--- RESULT ---")
        print(res["result"])

        # 🕒 Reminder confirmation
        if "🕒" in res["result"]:
            print("🕒 A reminder has been successfully scheduled.")

        # ⚠️ Unknown device message
        if "⚠️" in res["result"]:
            print("⚠️ The system could not find that device name in its list.")
            print("💡 Try: 'turn on the kitchen fan' or 'turn off the living room lights'.")

        # ❌ Grammar mismatch
        if not res["ok"]:
            print("❌ The input structure did not match expected grammar rules.")
            print("💬 Tip: Try 'turn on the bedroom heater' or 'remind me to take medicine after 2 hours'.")

        print("-----------------------------\n")

# ---------- Run ----------
interactive_mode()