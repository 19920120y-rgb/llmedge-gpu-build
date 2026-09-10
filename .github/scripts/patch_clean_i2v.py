from pathlib import Path
import re

root = Path("llmedge")
ex = root / "llmedge-examples"

activity = ex / (
    "app/src/main/java/com/example/llmedgeexample/"
    "demo/video/VideoGenerationActivity.kt"
)

controller = ex / (
    "app/src/main/java/com/example/llmedgeexample/"
    "demo/video/VideoGenerationController.kt"
)

layout = ex / "app/src/main/res/layout/activity_video_generation.xml"
gradle = ex / "app/build.gradle.kts"
manifest = ex / "app/src/main/AndroidManifest.xml"
strings = ex / "app/src/main/res/values/strings.xml"

s = activity.read_text()

print("===== CLEAN I2V PATCH =====")

# 軽量テスト初期値
for old, new in [
    ("private const val DEFAULT_WIDTH = 512",
     "private const val DEFAULT_WIDTH = 256"),
    ("private const val DEFAULT_HEIGHT = 512",
     "private const val DEFAULT_HEIGHT = 256"),
    ("private const val DEFAULT_STEPS = 30",
     "private const val DEFAULT_STEPS = 4"),
    ("private const val DEFAULT_FRAMES = 9",
     "private const val DEFAULT_FRAMES = 1"),
]:
    if old not in s:
        raise SystemExit("ERROR missing: " + old)
    s = s.replace(old, new, 1)

# LoRA欄だけをローカルT5欄として使用。
# TAEHV部分には一切触らない。
old = "    private var selectedLoraPath: String? = null"
new = "    private var selectedTextEncoderOverride: ModelSpec? = null"

if old not in s:
    raise SystemExit("ERROR: LoRA state not found")
s = s.replace(old, new, 1)

old = "result.data?.data?.let { uri -> loadLoraFile(uri) }"
new = "result.data?.data?.let { uri -> loadTextEncoderFile(uri) }"

if old not in s:
    raise SystemExit("ERROR: LoRA picker callback not found")
s = s.replace(old, new, 1)

s = s.replace(
    "views.selectLoraButton.setOnClickListener { selectLoraFile() }",
    "views.selectLoraButton.setOnClickListener { selectTextEncoderFile() }",
    1,
)

s = s.replace(
    "views.clearLoraButton.setOnClickListener { clearLoraFile() }",
    "views.clearLoraButton.setOnClickListener { clearTextEncoderFile() }",
    1,
)

# Wan2.2 presetを初期選択、EasyCache OFF
bind = """        VideoGenerationFormSupport.bindAdapters(
            this,
            views.modelSpinner,
            views.samplerSpinner,
            views.schedulerSpinner,
        )"""

if bind not in s:
    raise SystemExit("ERROR: bindAdapters block not found")

s = s.replace(
    bind,
    bind + """
        views.modelSpinner.setSelection(2)
        views.easyCacheToggle.isChecked = false""",
    1,
)

# 公式LoRA handlerだけをT5 handlerへ交換
pattern = re.compile(
    r"    private fun selectLoraFile\(\) \{.*?"
    r"(?=    private fun selectTaehvFile\(\) \{)",
    re.S,
)

replacement = r'''    private fun selectTextEncoderFile() {
        loraPickerLauncher.launch(
            ImportedModelSupport.createPickerIntent(
                "Select local T5 encoder (.gguf)"
            )
        )
    }

    private fun loadTextEncoderFile(uri: Uri) {
        if (generationController.isGenerating()) return

        val previous = selectedTextEncoderOverride
        val previousLabel = views.loraLabel.text

        views.selectLoraButton.isEnabled = false
        views.generateButton.isEnabled = false
        views.loraLabel.text = "Importing T5..."

        lifecycleScope.launch {
            try {
                val imported =
                    withContext(Dispatchers.IO) {
                        ImportedModelSupport.copyToAppStorage(
                            context = this@VideoGenerationActivity,
                            uri = uri,
                            internalNamePrefix = "t5-",
                        )
                    }

                selectedTextEncoderOverride =
                    ModelSpec.localFile(imported.file)

                views.loraLabel.text = imported.displayName
                views.clearLoraButton.visibility = View.VISIBLE

                FileLogger.i(
                    TAG,
                    "Local T5: ${imported.file.absolutePath}"
                )
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (t: Throwable) {
                selectedTextEncoderOverride = previous
                views.loraLabel.text = previousLabel

                views.clearLoraButton.visibility =
                    if (previous == null) View.GONE
                    else View.VISIBLE

                FileLogger.e(TAG, "T5 import failed", t)

                Toast.makeText(
                    this@VideoGenerationActivity,
                    "T5 import failed: ${t.localizedMessage ?: "unknown"}",
                    Toast.LENGTH_LONG,
                ).show()
            } finally {
                views.selectLoraButton.isEnabled = true

                if (!generationController.isGenerating()) {
                    views.generateButton.isEnabled = true
                }
            }
        }
    }

    private fun clearTextEncoderFile() {
        if (generationController.isGenerating()) return

        (selectedTextEncoderOverride as? ModelSpec.LocalFile)
            ?.file
            ?.let {
                ImportedModelSupport.deleteFromAppStorage(this, it)
            }

        selectedTextEncoderOverride = null
        views.loraLabel.text = "No local T5 selected"
        views.clearLoraButton.visibility = View.GONE
    }

'''

s, n = pattern.subn(replacement, s, count=1)

if n != 1:
    raise SystemExit("ERROR: T5 handler replacement failed")

# buildGenerationConfig のmodelPreset直後に
# OFFLINE 3点チェックを追加
needle = """        val modelPreset =
            VideoGenerationFormSupport.withModelOverride(
                    VideoGenerationFormSupport.selectedModelPreset(
                            views.modelSpinner.selectedItemPosition,
                    ),
                    selectedModelOverride,
            )
"""

if needle not in s:
    raise SystemExit("ERROR: modelPreset block not found")

guard = needle + """
        if (
            selectedModelOverride == null ||
            selectedTextEncoderOverride == null ||
            selectedTaehvPath == null
        ) {
            Toast.makeText(
                this,
                "OFFLINE: select GGUF + T5 + TAEHV first",
                Toast.LENGTH_LONG,
            ).show()
            return null
        }
"""

s = s.replace(needle, guard, 1)

# フルVAEは使わない。
# 公式TAEHVをそのまま使う。
if "            vae = modelPreset.vae," not in s:
    raise SystemExit("ERROR: VAE assignment not found")

s = s.replace(
    "            vae = modelPreset.vae,",
    "            vae = null,",
    1,
)

if "            textEncoder = modelPreset.textEncoder," not in s:
    raise SystemExit("ERROR: textEncoder assignment not found")

s = s.replace(
    "            textEncoder = modelPreset.textEncoder,",
    "            textEncoder = selectedTextEncoderOverride,",
    1,
)

if "            loraDirectory = selectedLoraPath," not in s:
    raise SystemExit("ERROR: LoRA assignment not found")

s = s.replace(
    "            loraDirectory = selectedLoraPath,",
    "            loraDirectory = null,",
    1,
)

# ここは公式のまま残す
if "            taehvPath = selectedTaehvPath," not in s:
    raise SystemExit("ERROR: official TAEHV path missing")

activity.write_text(s)

# Sequential loading ON
c = controller.read_text()

if "            forceSequentialLoad = false," not in c:
    raise SystemExit("ERROR: sequential flag not found")

c = c.replace(
    "            forceSequentialLoad = false,",
    "            forceSequentialLoad = true,",
    1,
)

controller.write_text(c)

# UI
x = layout.read_text()

x = x.replace(
    "LoRA (Optional)",
    "Local T5 encoder (OFFLINE)"
)
x = x.replace("SELECT LORA", "SELECT T5")
x = x.replace("No LoRA selected", "No local T5 selected")

# TAEHV表示は公式のまま
layout.write_text(x)

# package
g = gradle.read_text()

if 'applicationId = "com.example.llmedgeexample"' not in g:
    raise SystemExit("ERROR: original applicationId not found")

g = g.replace(
    'applicationId = "com.example.llmedgeexample"',
    'applicationId = "com.example.llmedgecleani2v"',
    1,
)

gradle.write_text(g)

# app label
m = manifest.read_text()
m = m.replace(
    'android:label="llmedge Example"',
    'android:label="LLMEdge Clean I2V"'
)
manifest.write_text(m)

if strings.exists():
    z = strings.read_text()
    z = re.sub(
        r'<string name="app_name">.*?</string>',
        '<string name="app_name">LLMEdge Clean I2V</string>',
        z,
    )
    strings.write_text(z)

# 最終検査
final = activity.read_text()

required = [
    "private var selectedTaehvPath: String? = null",
    "loadTaehvFile(uri)",
    "selectedTextEncoderOverride",
    "vae = null,",
    "textEncoder = selectedTextEncoderOverride,",
    "taehvPath = selectedTaehvPath,",
]

for r in required:
    if r not in final:
        raise SystemExit("ERROR FINAL CHECK: " + r)

for forbidden in [
    "selectedVaeOverride",
    "loadVaeFile(uri)",
    "taehvPath = null",
]:
    if forbidden in final:
        raise SystemExit("ERROR OLD PATCH REMAINS: " + forbidden)


# GGUF SUMMARY JNI BYPASS
support = ex / (
    "app/src/main/java/com/example/llmedgeexample/"
    "common/ImportedModelSupport.kt"
)

u = support.read_text()

old = "            summary = GgufFileSummary.read(partialFile)"
new = """            // GGUF magic is already validated above.
            // Skip diagnostic GGUFReader JNI parsing during large model import.
            summary = null"""

if old not in u:
    raise SystemExit("ERROR: GGUF SUMMARY LINE NOT FOUND")

u = u.replace(old, new, 1)
support.write_text(u)

print("GGUF JNI summary bypass = OK")

print("===== CLEAN PATCH VERIFIED =====")
print("Official TAEHV preserved")
print("Local GGUF + Local T5 + TAEHV")
print("Sequential loading ON")
