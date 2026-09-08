from pathlib import Path
import re

root = Path("llmedge")
changed = []

# ISOLATED_PROCESS を IN_PROCESS にする。
# enum定義やwhen分岐そのものは触らず、workerModeへの代入だけ変更。
patterns = [
    re.compile(
        r'(workerMode\s*=\s*)DiffusionWorkerMode\.ISOLATED_PROCESS'
    ),
    re.compile(
        r'(workerMode:\s*DiffusionWorkerMode\s*=\s*)'
        r'DiffusionWorkerMode\.ISOLATED_PROCESS'
    ),
]

for p in root.rglob("*.kt"):
    sp = str(p)

    if "/src/test/" in sp or "/src/androidTest/" in sp:
        continue

    try:
        s = p.read_text()
    except Exception:
        continue

    old = s

    for pat in patterns:
        s = pat.sub(
            r'\1DiffusionWorkerMode.IN_PROCESS',
            s
        )

    if s != old:
        p.write_text(s)
        changed.append(sp)

if not changed:
    raise SystemExit(
        "ERROR: isolated workerMode assignment not found"
    )

print("===== V14 IN-PROCESS PATCH =====")
for x in changed:
    print(x)

# forceSequentialLoad=false がアプリ側にあれば true にする
for p in (root / "llmedge-examples/app/src/main").rglob("*.kt"):
    s = p.read_text()
    old = s

    s = re.sub(
        r'forceSequentialLoad\s*=\s*false',
        'forceSequentialLoad = true',
        s
    )

    if s != old:
        p.write_text(s)
        print("SEQUENTIAL:", p)

# v13 -> v14 package
gradle = root / "llmedge-examples/app/build.gradle.kts"

g = gradle.read_text()
g = g.replace(
    'applicationId = "com.example.llmedgei2vv13"',
    'applicationId = "com.example.llmedgei2vv14"'
)
gradle.write_text(g)

# label
for p in [
    root / "llmedge-examples/app/src/main/AndroidManifest.xml",
    root / "llmedge-examples/app/src/main/res/values/strings.xml",
]:
    if p.exists():
        s = p.read_text()
        s = s.replace(
            "LLMEdge I2V v13 LowRAM",
            "LLMEdge I2V v14 InProcess"
        )
        p.write_text(s)

print("===== V14 APP PATCH OK =====")
