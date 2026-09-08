from pathlib import Path
import re

root = Path("llmedge")

marker = "Insufficient memory for sequential video loading"

targets = []

for p in root.rglob("*.kt"):
    try:
        s = p.read_text()
    except Exception:
        continue

    if marker in s:
        targets.append((p, s))

if len(targets) != 1:
    print("FOUND MEMORY TARGETS:", len(targets))
    for p, _ in targets:
        print(p)
    raise SystemExit("ERROR: expected exactly one sequential-video memory guard")

p, s = targets[0]

idx = s.index(marker)

# エラーメッセージから「必要RAM」「安全に使えるRAM」の
# 実際の変数名を自動取得
window = s[idx:idx + 1000]

m = re.search(
    r'requires approximately\s+'
    r'\$\{?([A-Za-z_][A-Za-z0-9_.]*)\}?MB'
    r'\s+with\s+'
    r'\$\{?([A-Za-z_][A-Za-z0-9_.]*)\}?MB',
    window,
    re.S,
)

if not m:
    print(window)
    raise SystemExit("ERROR: RAM variable names could not be detected")

required_var = m.group(1)
available_var = m.group(2)

throw_text = "throw InsufficientMemoryException("

throw_pos = s.rfind(
    throw_text,
    max(0, idx - 3000),
    idx,
)

if throw_pos < 0:
    raise SystemExit("ERROR: InsufficientMemoryException throw not found")

replacement = (
    f"if ((({required_var}).toLong() - "
    f"({available_var}).toLong()) > 512L) "
    f"{throw_text}"
)

s = (
    s[:throw_pos]
    + replacement
    + s[throw_pos + len(throw_text):]
)

p.write_text(s)

print("===== V13 MEMORY PATCH =====")
print("FILE:", p)
print("REQUIRED:", required_var)
print("AVAILABLE:", available_var)
print("ALLOW DEFICIT: <= 512 MB")

# v13 package ID
gradle = root / "llmedge-examples/app/build.gradle.kts"

g = gradle.read_text()

g, n = re.subn(
    r'applicationId\s*=\s*"[^"]+"',
    'applicationId = "com.example.llmedgei2vv13"',
    g,
    count=1,
)

if n != 1:
    raise SystemExit("ERROR: applicationId patch failed")

gradle.write_text(g)

# アプリ名
for q in [
    root / "llmedge-examples/app/src/main/AndroidManifest.xml",
    root / "llmedge-examples/app/src/main/res/values/strings.xml",
]:
    if not q.exists():
        continue

    x = q.read_text()

    x = re.sub(
        r'LLMEdge I2V v\d+(?: Offline| LowRAM)?',
        'LLMEdge I2V v13 LowRAM',
        x,
    )

    q.write_text(x)

print("===== V13 APP PATCH OK =====")
