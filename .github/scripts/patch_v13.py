from pathlib import Path

root = Path("llmedge")

# ==========================================
# LOW RAM GUARD
# ==========================================
planner = root / (
    "llmedge/src/main/java/io/aatricks/llmedge/image/"
    "VideoExecutionPlanner.kt"
)

s = planner.read_text()

old = """if (sequentialPeak > budget) {"""

new = """if (
    sequentialPeak >
        saturatingAdd(budget, 512L * MEBIBYTE)
) {"""

if old not in s:
    raise SystemExit("ERROR: sequential memory guard not found")

s = s.replace(old, new, 1)
planner.write_text(s)

print("===== V13 MEMORY PATCH OK =====")
print("Allow deficit: 512 MiB")

# ==========================================
# APP ID v12 -> v13
# ==========================================
gradle = root / "llmedge-examples/app/build.gradle.kts"

g = gradle.read_text()

old_id = 'applicationId = "com.example.llmedgei2vv12"'
new_id = 'applicationId = "com.example.llmedgei2vv13"'

if old_id not in g:
    raise SystemExit("ERROR: v12 applicationId not found")

g = g.replace(old_id, new_id, 1)
gradle.write_text(g)

# ==========================================
# APP LABEL
# ==========================================
manifest = root / "llmedge-examples/app/src/main/AndroidManifest.xml"

m = manifest.read_text()
m = m.replace(
    "LLMEdge I2V v12 Offline",
    "LLMEdge I2V v13 LowRAM",
)
manifest.write_text(m)

strings = root / (
    "llmedge-examples/app/src/main/res/values/strings.xml"
)

if strings.exists():
    x = strings.read_text()
    x = x.replace(
        "LLMEdge I2V v12 Offline",
        "LLMEdge I2V v13 LowRAM",
    )
    strings.write_text(x)

print("===== V13 APP PATCH OK =====")
