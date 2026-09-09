from pathlib import Path
import re

root = Path("llmedge")
marker = "OFFLINE: select GGUF + VAE + T5 first"

targets = []

for p in (root / "llmedge-examples/app/src/main").rglob("*.kt"):
    try:
        s = p.read_text()
    except Exception:
        continue
    if marker in s:
        targets.append(p)

if len(targets) != 1:
    print("TARGET COUNT =", len(targets))
    for p in targets:
        print(p)
    raise SystemExit("ERROR: offline guard target not unique")

p = targets[0]
s = p.read_text()
pos = s.index(marker)

ifpos = s.rfind("if (", max(0, pos - 2500), pos)
if ifpos < 0:
    raise SystemExit("ERROR: if condition not found")

start = ifpos + 3
depth = 1
i = start

while i < len(s) and depth:
    if s[i] == "(":
        depth += 1
    elif s[i] == ")":
        depth -= 1
    i += 1

if depth:
    raise SystemExit("ERROR: condition parse failed")

condition = s[start:i-1]

print("===== OLD OFFLINE CONDITION =====")
print(condition)

patterns = [
    re.compile(
        r'([A-Za-z_][A-Za-z0-9_.]*(?:vae|Vae|VAE)[A-Za-z0-9_.]*)'
        r'\s*==\s*null'
    ),
    re.compile(
        r'([A-Za-z_][A-Za-z0-9_.]*(?:vae|Vae|VAE)[A-Za-z0-9_.]*)'
        r'\.isNullOrBlank\(\)'
    ),
]

newcond = condition
changed = False

for pat in patterns:
    m = pat.search(newcond)
    if not m:
        continue

    oldcheck = m.group(0)

    replacement = (
        "(" + oldcheck +
        " && selectedTaehvPath == null)"
    )

    newcond = (
        newcond[:m.start()] +
        replacement +
        newcond[m.end():]
    )

    changed = True
    break

if not changed:
    print("===== CONDITION CONTEXT =====")
    print(s[max(0,pos-1800):pos+400])
    raise SystemExit("ERROR: VAE missing check not found")

s = s[:start] + newcond + s[i-1:]
p.write_text(s)

print("===== NEW OFFLINE CONDITION =====")
print(newcond)

if "selectedTaehvPath" not in newcond:
    raise SystemExit("ERROR: TAEHV guard missing")

print("OFFLINE guard: VAE OR TAEHV = OK")

# v14 -> v15 package
gradle = root / "llmedge-examples/app/build.gradle.kts"
g = gradle.read_text()

g2 = g.replace(
    'applicationId = "com.example.llmedgei2vv14"',
    'applicationId = "com.example.llmedgei2vv15"'
)

if g2 == g:
    raise SystemExit("ERROR: v14 applicationId not found")

gradle.write_text(g2)

# label
for q in [
    root / "llmedge-examples/app/src/main/AndroidManifest.xml",
    root / "llmedge-examples/app/src/main/res/values/strings.xml",
]:
    if q.exists():
        x = q.read_text()
        x = x.replace(
            "LLMEdge I2V v14 InProcess",
            "LLMEdge I2V v15 TAEHV"
        )
        q.write_text(x)

print("===== V15 PATCH OK =====")
