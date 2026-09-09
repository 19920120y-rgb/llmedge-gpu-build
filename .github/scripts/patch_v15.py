from pathlib import Path
import re

ex = Path("llmedge/llmedge-examples")

activity = ex / (
    "app/src/main/java/com/example/llmedgeexample/"
    "demo/video/VideoGenerationActivity.kt"
)

s = activity.read_text()

def must_replace(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"ERROR: {label} not found")
    s = s.replace(old, new, 1)
    print("OK:", label)

print("===== V15 REAL TAEHV PATCH =====")

# v11でTAEHV変数をVAE変数へ変えていたので元へ戻す
must_replace(
    "    private var selectedVaeOverride: ModelSpec? = null",
    "    private var selectedTaehvPath: String? = null",
    "TAEHV state"
)

# picker callback
must_replace(
    "result.data?.data?.let { uri -> loadVaeFile(uri) }",
    "result.data?.data?.let { uri -> loadTaehvFile(uri) }",
    "TAEHV picker callback"
)

# buttons
must_replace(
    "views.selectTaehvButton.setOnClickListener { selectVaeFile() }",
    "views.selectTaehvButton.setOnClickListener { selectTaehvFile() }",
    "TAEHV select button"
)

must_replace(
    "views.clearTaehvButton.setOnClickListener { clearVaeFile() }",
    "views.clearTaehvButton.setOnClickListener { clearTaehvFile() }",
    "TAEHV clear button"
)

# v11で作ったfull VAE handlerだけを公式TAEHV handlerへ置換
pattern = re.compile(
    r"    private fun selectVaeFile\(\) \{.*?"
    r"(?=    private fun loadImportedModel\(uri: Uri\) \{)",
    re.S,
)

replacement = r'''    private fun selectTaehvFile() {
        taehvPickerLauncher.launch(
            VideoGenerationMediaSupport.createSafetensorPickerIntent(
                "Select TAEHV (.safetensors)"
            ),
        )
    }

    private fun loadTaehvFile(uri: Uri) {
        try {
            val taehvFile =
                VideoGenerationMediaSupport.loadTaehvFile(this, uri)

            selectedTaehvPath = taehvFile.selectionPath
            views.taehvLabel.text = taehvFile.file.name
            views.clearTaehvButton.visibility = View.VISIBLE

            FileLogger.i(
                TAG,
                "TAEHV loaded: $selectedTaehvPath"
            )
        } catch (e: Exception) {
            selectedTaehvPath = null

            FileLogger.e(
                TAG,
                "Failed to load TAEHV file",
                e
            )

            Toast.makeText(
                this,
                "Failed to load TAEHV: ${e.message}",
                Toast.LENGTH_SHORT
            ).show()
        }
    }

    private fun clearTaehvFile() {
        selectedTaehvPath = null
        views.taehvLabel.text = "No TAEHV selected"
        views.clearTaehvButton.visibility = View.GONE
    }

'''

s, n = pattern.subn(replacement, s, count=1)

if n != 1:
    raise SystemExit("ERROR: VAE handler block not found")

print("OK: real TAEHV handlers")

# v11の旧VAE自動復元を削除
vae_restore = re.compile(
    r'\n        val vaeFile =\s*'
    r'File\(filesDir, "imported-vae/Wan2\.2_VAE\.safetensors"\)'
    r'.*?views\.clearTaehvButton\.visibility = View\.VISIBLE\s*'
    r'\}\n',
    re.S,
)

s, n = vae_restore.subn("\n", s, count=1)

if n != 1:
    raise SystemExit("ERROR: old VAE restore block not found")

print("OK: old VAE restore removed")

# OFFLINE条件を GGUF + TAEHV + T5 に直接変更
must_replace(
'''            selectedModelOverride == null ||
            selectedVaeOverride == null ||
            selectedTextEncoderOverride == null''',
'''            selectedModelOverride == null ||
            selectedTaehvPath == null ||
            selectedTextEncoderOverride == null''',
    "offline asset guard"
)

must_replace(
    "OFFLINE: select GGUF + VAE + T5 first",
    "OFFLINE: select GGUF + TAEHV + T5 first",
    "offline message"
)

# フルVAEを生成経路から外す
must_replace(
    "            vae = selectedVaeOverride,",
    "            vae = null,",
    "full VAE disabled"
)

# TAEHVを本当に生成リクエストへ渡す
must_replace(
    "            taehvPath = null,",
    "            taehvPath = selectedTaehvPath,",
    "TAEHV generation path"
)

activity.write_text(s)

# UIをTAEHV表示へ戻す
layout = ex / "app/src/main/res/layout/activity_video_generation.xml"
x = layout.read_text()

x = x.replace(
    "Local VAE override (OFFLINE)",
    "Local TAEHV (OFFLINE)"
)
x = x.replace("SELECT VAE", "SELECT TAEHV")
x = x.replace("No local VAE selected", "No TAEHV selected")

layout.write_text(x)

# v14 -> v15
gradle = ex / "app/build.gradle.kts"
g = gradle.read_text()

if 'applicationId = "com.example.llmedgei2vv14"' not in g:
    raise SystemExit("ERROR: v14 package id not found")

g = g.replace(
    'applicationId = "com.example.llmedgei2vv14"',
    'applicationId = "com.example.llmedgei2vv15"',
    1
)

gradle.write_text(g)

for q in [
    ex / "app/src/main/AndroidManifest.xml",
    ex / "app/src/main/res/values/strings.xml",
]:
    if q.exists():
        z = q.read_text()
        z = z.replace(
            "LLMEdge I2V v14 InProcess",
            "LLMEdge I2V v15 TAEHV"
        )
        q.write_text(z)

# 最終検査
final = activity.read_text()

checks = [
    "private var selectedTaehvPath: String? = null",
    "loadTaehvFile(uri)",
    "selectedTaehvPath == null",
    "vae = null,",
    "taehvPath = selectedTaehvPath,",
]

for c in checks:
    if c not in final:
        raise SystemExit("ERROR: FINAL CHECK FAILED: " + c)

if "selectedVaeOverride" in final:
    raise SystemExit("ERROR: old selectedVaeOverride remains")

print("===== V15 PATCH VERIFIED =====")
