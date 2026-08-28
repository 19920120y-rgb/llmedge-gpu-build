from pathlib import Path
import re

root = Path("llmedge")
ex = root / "llmedge-examples"

# -------------------------------------------------
# APP ID
# -------------------------------------------------
gradle = ex / "app/build.gradle.kts"
s = gradle.read_text()
s = s.replace(
    'applicationId = "com.example.llmedgeexample"',
    'applicationId = "com.example.llmedgei2vv11"',
)
gradle.write_text(s)

manifest = ex / "app/src/main/AndroidManifest.xml"
s = manifest.read_text()
s = s.replace(
    'android:label="llmedge Example"',
    'android:label="LLMEdge I2V v11 Offline"',
)
manifest.write_text(s)

strings = ex / "app/src/main/res/values/strings.xml"
if strings.exists():
    s = strings.read_text()
    s = re.sub(
        r'<string name="app_name">.*?</string>',
        '<string name="app_name">LLMEdge I2V v11 Offline</string>',
        s,
    )
    strings.write_text(s)

# -------------------------------------------------
# WAN 2.2 MOBILE Q3
# -------------------------------------------------
form = ex / (
    "app/src/main/java/com/example/llmedgeexample/"
    "demo/video/VideoGenerationFormSupport.kt"
)
s = form.read_text()
s = s.replace(
    'displayName = "Wan 2.2 TI2V 5B Q6_K"',
    'displayName = "Wan 2.2 TI2V 5B Q3_K_S (offline mobile)"',
)
s = s.replace(
    'filename = "Wan2.2-TI2V-5B-Q6_K.gguf"',
    'filename = "Wan2.2-TI2V-5B-Q3_K_S.gguf"',
)
form.write_text(s)

# -------------------------------------------------
# VIDEO ACTIVITY
# -------------------------------------------------
activity = ex / (
    "app/src/main/java/com/example/llmedgeexample/"
    "demo/video/VideoGenerationActivity.kt"
)
s = activity.read_text()

if "import java.io.File" not in s:
    s = s.replace(
        "import io.aatricks.llmedge.model.ModelSpec",
        "import io.aatricks.llmedge.model.ModelSpec\nimport java.io.File",
    )

# Safer smoke-test defaults
s = s.replace(
    "private const val DEFAULT_WIDTH = 512",
    "private const val DEFAULT_WIDTH = 256",
)
s = s.replace(
    "private const val DEFAULT_HEIGHT = 512",
    "private const val DEFAULT_HEIGHT = 256",
)
s = s.replace(
    "private const val DEFAULT_STEPS = 30",
    "private const val DEFAULT_STEPS = 8",
)
s = s.replace(
    "private const val DEFAULT_CFG = 5.0f",
    "private const val DEFAULT_CFG = 6.0f",
)
s = s.replace(
    "private const val DEFAULT_FRAMES = 9",
    "private const val DEFAULT_FRAMES = 5",
)

s = s.replace(
    "private var selectedLoraPath: String? = null",
    "private var selectedTextEncoderOverride: ModelSpec? = null",
)
s = s.replace(
    "private var selectedTaehvPath: String? = null",
    "private var selectedVaeOverride: ModelSpec? = null",
)

# Picker callbacks
s = s.replace(
    "result.data?.data?.let { uri -> loadLoraFile(uri) }",
    "result.data?.data?.let { uri -> loadTextEncoderFile(uri) }",
)
s = s.replace(
    "result.data?.data?.let { uri -> loadTaehvFile(uri) }",
    "result.data?.data?.let { uri -> loadVaeFile(uri) }",
)

# Default Wan 2.2
bind = """        VideoGenerationFormSupport.bindAdapters(
            this,
            views.modelSpinner,
            views.samplerSpinner,
            views.schedulerSpinner,
        )"""
if bind in s:
    s = s.replace(
        bind,
        bind + "\n        views.modelSpinner.setSelection(2)",
        1,
    )

# Re-purpose LoRA slot -> local T5
s = s.replace(
    "views.selectLoraButton.setOnClickListener { selectLoraFile() }",
    "views.selectLoraButton.setOnClickListener { selectTextEncoderFile() }",
)
s = s.replace(
    "views.clearLoraButton.setOnClickListener { clearLoraFile() }",
    "views.clearLoraButton.setOnClickListener { clearTextEncoderFile() }",
)

# Re-purpose TAEHV slot -> local full VAE
s = s.replace(
    "views.selectTaehvButton.setOnClickListener { selectTaehvFile() }",
    "views.selectTaehvButton.setOnClickListener { selectVaeFile() }",
)
s = s.replace(
    "views.clearTaehvButton.setOnClickListener { clearTaehvFile() }",
    "views.clearTaehvButton.setOnClickListener { clearVaeFile() }",
)

# Replace LoRA + TAEHV handlers
pattern = re.compile(
    r"    private fun selectLoraFile\(\) \{.*?"
    r"(?=    private fun loadImportedModel\(uri: Uri\) \{)",
    re.S,
)

replacement = r'''    private fun selectTextEncoderFile() {
        loraPickerLauncher.launch(
            ImportedModelSupport.createPickerIntent("Select local T5 encoder (.gguf)")
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

                selectedTextEncoderOverride = ModelSpec.localFile(imported.file)
                views.loraLabel.text = imported.displayName
                views.clearLoraButton.visibility = View.VISIBLE

                FileLogger.i(
                    TAG,
                    "Imported local T5: ${imported.file.absolutePath}"
                )

            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (t: Throwable) {
                selectedTextEncoderOverride = previous
                views.loraLabel.text = previousLabel
                views.clearLoraButton.visibility =
                    if (previous == null) View.GONE else View.VISIBLE

                FileLogger.e(TAG, "Failed to import T5", t)

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

        (selectedTextEncoderOverride as? ModelSpec.LocalFile)?.file?.let {
            ImportedModelSupport.deleteFromAppStorage(this, it)
        }

        selectedTextEncoderOverride = null
        views.loraLabel.text = "No local T5 selected"
        views.clearLoraButton.visibility = View.GONE
    }

    private fun selectVaeFile() {
        taehvPickerLauncher.launch(
            VideoGenerationMediaSupport.createSafetensorPickerIntent(
                "Select local Wan 2.2 VAE (.safetensors)"
            )
        )
    }

    private fun loadVaeFile(uri: Uri) {
        if (generationController.isGenerating()) return

        val previous = selectedVaeOverride
        val previousLabel = views.taehvLabel.text

        views.selectTaehvButton.isEnabled = false
        views.generateButton.isEnabled = false
        views.taehvLabel.text = "Importing VAE..."

        lifecycleScope.launch {
            try {
                val target =
                    withContext(Dispatchers.IO) {
                        val directory =
                            File(filesDir, "imported-vae").apply { mkdirs() }

                        val finalFile =
                            File(directory, "Wan2.2_VAE.safetensors")
                        val partial =
                            File(directory, "Wan2.2_VAE.safetensors.partial")

                        partial.delete()

                        val input =
                            contentResolver.openInputStream(uri)
                                ?: error("Unable to open selected VAE")

                        input.use { source ->
                            partial.outputStream().use { output ->
                                val buffer = ByteArray(1024 * 1024)
                                while (true) {
                                    val count = source.read(buffer)
                                    if (count < 0) break
                                    output.write(buffer, 0, count)
                                }
                            }
                        }

                        check(partial.length() > 0L) {
                            "Selected VAE is empty"
                        }

                        if (finalFile.exists()) finalFile.delete()

                        if (!partial.renameTo(finalFile)) {
                            partial.copyTo(finalFile, overwrite = true)
                            partial.delete()
                        }

                        finalFile
                    }

                selectedVaeOverride = ModelSpec.localFile(target)
                views.taehvLabel.text = target.name
                views.clearTaehvButton.visibility = View.VISIBLE

                FileLogger.i(TAG, "Imported local VAE: ${target.absolutePath}")

            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (t: Throwable) {
                selectedVaeOverride = previous
                views.taehvLabel.text = previousLabel
                views.clearTaehvButton.visibility =
                    if (previous == null) View.GONE else View.VISIBLE

                FileLogger.e(TAG, "Failed to import VAE", t)

                Toast.makeText(
                    this@VideoGenerationActivity,
                    "VAE import failed: ${t.localizedMessage ?: "unknown"}",
                    Toast.LENGTH_LONG,
                ).show()
            } finally {
                views.selectTaehvButton.isEnabled = true
                if (!generationController.isGenerating()) {
                    views.generateButton.isEnabled = true
                }
            }
        }
    }

    private fun clearVaeFile() {
        if (generationController.isGenerating()) return

        (selectedVaeOverride as? ModelSpec.LocalFile)?.file?.delete()

        selectedVaeOverride = null
        views.taehvLabel.text = "No local VAE selected"
        views.clearTaehvButton.visibility = View.GONE
    }

'''

s, count = pattern.subn(replacement, s, count=1)
if count != 1:
    raise SystemExit("ERROR: media handler patch failed")

# Restore completed imports after Activity/process recreation
restore = r'''    private fun restoreOfflineAssets() {
        val importedDirectory = File(filesDir, "imported-models")

        val wanFile =
            importedDirectory.listFiles()
                .orEmpty()
                .filter {
                    it.isFile &&
                        it.name.startsWith("wan-") &&
                        it.name.endsWith(".gguf")
                }
                .maxByOrNull { it.lastModified() }

        if (wanFile != null) {
            selectedModelOverride = ModelSpec.localFile(wanFile)
            views.modelLabel.text = wanFile.name
            views.clearModelButton.visibility = View.VISIBLE
            views.modelSpinner.isEnabled = false
        }

        val t5File =
            importedDirectory.listFiles()
                .orEmpty()
                .filter {
                    it.isFile &&
                        it.name.startsWith("t5-") &&
                        it.name.endsWith(".gguf")
                }
                .maxByOrNull { it.lastModified() }

        if (t5File != null) {
            selectedTextEncoderOverride = ModelSpec.localFile(t5File)
            views.loraLabel.text = t5File.name
            views.clearLoraButton.visibility = View.VISIBLE
        }

        val vaeFile =
            File(filesDir, "imported-vae/Wan2.2_VAE.safetensors")

        if (vaeFile.isFile && vaeFile.length() > 0L) {
            selectedVaeOverride = ModelSpec.localFile(vaeFile)
            views.taehvLabel.text = vaeFile.name
            views.clearTaehvButton.visibility = View.VISIBLE
        }
    }

'''

marker = "    private fun startGeneration() {"
if marker not in s:
    raise SystemExit("ERROR: startGeneration marker missing")
s = s.replace(marker, restore + marker, 1)

# Restore when screen starts
log_marker = "        // Log initial memory state"
if log_marker not in s:
    raise SystemExit("ERROR: restore insertion marker missing")
s = s.replace(
    log_marker,
    "        restoreOfflineAssets()\n" + log_marker,
    1,
)

# Require ALL local assets, preventing Hugging Face access
preset_block = """        val modelPreset =
            VideoGenerationFormSupport.withModelOverride(
                    VideoGenerationFormSupport.selectedModelPreset(
                            views.modelSpinner.selectedItemPosition,
                    ),
                    selectedModelOverride,
            )
"""

if preset_block not in s:
    raise SystemExit("ERROR: modelPreset block missing")

local_check = preset_block + """
        if (
            selectedModelOverride == null ||
            selectedVaeOverride == null ||
            selectedTextEncoderOverride == null
        ) {
            Toast.makeText(
                this,
                "OFFLINE: select GGUF + VAE + T5 first",
                Toast.LENGTH_LONG,
            ).show()
            return null
        }
"""

s = s.replace(preset_block, local_check, 1)

s = s.replace(
    "            vae = modelPreset.vae,",
    "            vae = selectedVaeOverride,",
)
s = s.replace(
    "            textEncoder = modelPreset.textEncoder,",
    "            textEncoder = selectedTextEncoderOverride,",
)
s = s.replace(
    "            loraDirectory = selectedLoraPath,",
    "            loraDirectory = null,",
)
s = s.replace(
    "            taehvPath = selectedTaehvPath,",
    "            taehvPath = null,",
)

activity.write_text(s)

# -------------------------------------------------
# UI
# -------------------------------------------------
layout = ex / "app/src/main/res/layout/activity_video_generation.xml"
s = layout.read_text()

s = s.replace("LoRA (Optional)", "Local T5 encoder (OFFLINE)")
s = s.replace("SELECT LORA", "SELECT T5")
s = s.replace("No LoRA selected", "No local T5 selected")

s = s.replace(
    "TAEHV (Optional, overrides VAE)",
    "Local VAE override (OFFLINE)",
)
s = s.replace("SELECT TAEHV", "SELECT VAE")
s = s.replace("No TAEHV selected", "No local VAE selected")

# Smoke test defaults: 256 x 256, 5 frames, 8 steps
replacements = [
    ('android:text="512"', 'android:text="256"'),
    ('android:text="512"', 'android:text="256"'),
    ('android:text="9"', 'android:text="5"'),
    ('android:text="20"', 'android:text="8"'),
    ('android:text="7.0"', 'android:text="6.0"'),
    ('android:progress="80"', 'android:progress="75"'),
    ('android:text="0.80"', 'android:text="0.75"'),
]

for old, new in replacements:
    s = s.replace(old, new, 1)

layout.write_text(s)

# -------------------------------------------------
# FORCE SEQUENTIAL LOADING
# -------------------------------------------------
controller = ex / (
    "app/src/main/java/com/example/llmedgeexample/"
    "demo/video/VideoGenerationController.kt"
)
s = controller.read_text()
s = s.replace(
    "forceSequentialLoad = false,",
    "forceSequentialLoad = true,",
)
controller.write_text(s)

print("===== V11 PATCH COMPLETE =====")
print("Local GGUF + local VAE + local T5")
print("State restored from app-private files")
print("Sequential loading enabled")
