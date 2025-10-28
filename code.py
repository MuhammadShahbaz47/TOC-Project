# smart_home_project_fixed_trace.py
# ------------------------------------------------------
# SMART HOME COMMAND PARSER (CFG-based with Stack Trace)
# ------------------------------------------------------

# --------------------
# Grammar definition
# --------------------
grammar = {
    "COMMAND": [["ACTION"]],
    "ACTION": [["VERB", "SWITCH", "TARGET"]],
    "VERB": [["turn"], ["switch"]],
    "SWITCH": [["on"], ["off"]],
    "TARGET": [["ALL_PHRASE"], ["DEVICE_PHRASE"], ["DEVICE_IN_ROOM"]],
    "ALL_PHRASE": [["all", "DEVICE_PLURAL"]],
    "DEVICE_PHRASE": [["LOCATION_OPT", "DEVICE_NP"]],
    "DEVICE_IN_ROOM": [["DEVICE_NP", "in", "ROOM"]],
    "LOCATION_OPT": [["the", "ROOM"], ["in", "ROOM"], ["the"], []],
    "DEVICE_NP": [
        ["lights"], ["light"], ["fan"], ["fans"],
        ["heater"], ["air", "conditioner"], ["conditioner"]
    ],
    "DEVICE_PLURAL": [["lights"], ["fans"]],
    "ROOM": [
        ["living", "room"],
        ["kitchen"],
        ["bedroom"],
        ["bathroom"]
    ]
}

# --------------------
# Tokenizer
# --------------------
def tokenize(s):
    s = s.strip().lower()
    if s.endswith('.'):
        s = s[:-1]
    tokens = s.split()
    return tokens

# --------------------
# Parser (recursive descent for better accuracy)
# --------------------
def parse_symbol(symbol, tokens, i, trace):
    if symbol not in grammar:  # terminal
        if i < len(tokens) and tokens[i] == symbol:
            trace.append(f"Matched terminal '{symbol}'")
            return True, i + 1
        else:
            trace.append(f"❌ Expected '{symbol}', got '{tokens[i] if i < len(tokens) else 'EOF'}'")
            return False, i

    for prod in grammar[symbol]:
        trace.append(f"Expanding {symbol} → {' '.join(prod) if prod else 'ε'}")
        j = i
        success = True
        for s2 in prod:
            ok, j = parse_symbol(s2, tokens, j, trace)
            if not ok:
                success = False
                break
        if success:
            return True, j
        trace.append(f"Backtrack on rule {symbol} → {' '.join(prod) if prod else 'ε'}")

    return False, i

def parse(tokens, show_trace=False):
    trace = []
    ok, index = parse_symbol("COMMAND", tokens, 0, trace)
    if show_trace:
        print("\n--- PARSING TRACE ---")
        for line in trace:
            print(line)
    return ok and index == len(tokens)

# --------------------
# Commands
# --------------------
commands = [
    "turn on the living room lights",
    "turn off the kitchen fan",
    "turn on the bedroom heater",
    "switch off the bathroom lights",
    "switch on the living room fan",
    "turn off all lights",
    "turn on all fans",
    "switch on the heater in bedroom",
    "turn off the light in kitchen",
    "turn on the air conditioner in living room",
    # Incorrect for testing
    "turn living on lights",
    "switch on the lights in garden",
    "turn off all heater",
]

# --------------------
# Interactive Mode
# --------------------
print("------ SMART HOME COMMAND PARSER (Fixed & Traced) ------")
print("Examples you can try:")
for c in commands[:10]:
    print(" •", c)
print("\nType 'exit' to quit.\n")

while True:
    user_input = input("Enter a command: ").strip()
    if user_input.lower() == "exit":
        print("Exiting... Goodbye!")
        break
    tokens = tokenize(user_input)
    result = parse(tokens, show_trace=True)
    print(f"\nFinal Result: {'✅ Correct' if result else '❌ Incorrect'}\n")