#!/usr/bin/env python3
"""Create side-by-side test application ID; preserve installed Clean I2V data.
Run after patch_clean_i2v.py and patch_wan22_quality.py, before Gradle build.
"""
from pathlib import Path

base = Path("llmedge/llmedge-examples/app/src/main")
gradle = base.parent.parent / "build.gradle.kts"
manifest = base / "AndroidManifest.xml"
strings = base / "res/values/strings.xml"

old_id = 'applicationId = "com.example.llmedgecleani2v"'
new_id = 'applicationId = "com.example.wan22qualitytest"'
old_label = 'LLMEdge Clean I2V'
new_label = 'Wan2.2 Quality Test'

if not gradle.is_file() or not manifest.is_file():
    raise SystemExit('STOP: App Gradle or Manifest missing')
g = gradle.read_text(encoding="utf-8")
m = manifest.read_text(encoding="utf-8")
if g.count(old_id) != 1:
    raise SystemExit('STOP: expected existing app ID missing or duplicated')
# The preexisting patch must have created this label.
if old_label not in m:
    raise SystemExit('STOP: existing app label missing; refusing app identity change')
g2 = g.replace(old_id, new_id, 1)
m2 = m.replace(old_label, new_label)
# Optional strings: preserve existing fields and modify only the visible label.
s0 = strings.read_text(encoding="utf-8") if strings.is_file() else None
s2 = s0.replace(old_label, new_label) if s0 is not None else None
# Validate in memory before writing files.
assert new_id in g2 and old_id not in g2 and new_label in m2
# No model edits, no app/data deletion, no Android device access.
gradle.write_text(g2, encoding="utf-8")
manifest.write_text(m2, encoding="utf-8")
if s2 is not None and s2 != s0:
    strings.write_text(s2, encoding="utf-8")
print('SEPARATE_APP_ID_OK: com.example.wan22qualitytest')
print('Existing LLMEdge Clean I2V data is untouched')
