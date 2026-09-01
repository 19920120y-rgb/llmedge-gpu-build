from pathlib import Path
import re

ex = Path("llmedge/llmedge-examples")

activity = ex / (
    "app/src/main/java/com/example/llmedgeexample/"
    "demo/video/VideoGenerationActivity.kt"
)

s = activity.read_text()

# v11 -> v12 package/label is handled after v11 patch.
gradle = ex / "app/build.gradle.kts"
g = gradle.read_text()
g = g.replace(
    'applicationId = "com.example.llmedgei2vv11"',
    'applicationId = "com.example.llmedgei2vv12"',
)
gradle.write_text(g)

manifest = ex / "app/src/main/AndroidManifest.xml"
m = manifest.read_text().replace(
    "LLMEdge I2V v11 Offline",
    "LLMEdge I2V v12 Offline",
)
manifest.write_text(m)

strings = ex / "app/src/main/res/values/strings.xml"
if strings.exists():
    x = strings.read_text().replace(
        "LLMEdge I2V v11 Offline",
        "LLMEdge I2V v12 Offline",
    )
    strings.write_text(x)

# Replace heavyweight GGUF importer with a plain 1MB-buffer copy.
pattern = re.compile(
    r"    private fun loadImportedModel\(uri: Uri\) \{.*?"
    r"(?=    private fun clearImportedModel\(\))",
    re.S,
)

replacement = r'''    private fun loadImportedModel(uri: Uri) {
        if (generationController.isGenerating()) return

        val previous = selectedModelOverride
        val previousLabel = views.modelLabel.text

        views.selectModelButton.isEnabled = false
        views.generateButton.isEnabled = false
        views.modelLabel.text = "Copying GGUF..."

        lifecycleScope.launch {
            try {
                val target = withContext(Dispatchers.IO) {
                    val directory =
                        File(filesDir, "imported-models").apply { mkdirs() }

                    val partial = File(directory, "wan-local.gguf.partial")
                    val finalFile = File(directory, "wan-local.gguf")

                    partial.delete()

                    val input = contentResolver.openInputStream(uri)
                        ?: error("Unable to open selected GGUF")

                    input.use { source ->
                        partial.outputStream().use { output ->
                            val buffer = ByteArray(1024 * 1024)
                            while (true) {
                                val count = source.read(buffer)
                                if (count < 0) break
                                output.write(buffer, 0, count)
                            }
                            output.flush()
                        }
                    }

                    check(partial.length() > 1024L * 1024L) {
                        "GGUF copy failed"
                    }

                    if (finalFile.exists()) finalFile.delete()

                    if (!partial.renameTo(finalFile)) {
                        partial.copyTo(finalFile, overwrite = true)
                        partial.delete()
                    }

                    finalFile
                }

                selectedModelOverride = ModelSpec.localFile(target)
                views.modelLabel.text =
                    "Wan local (${target.length() / 1024 / 1024} MB)"
                views.clearModelButton.visibility = View.VISIBLE
                views.modelSpinner.isEnabled = false

                FileLogger.i(
                    TAG,
                    "Safe GGUF import complete: ${target.absolutePath}",
                )

            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (t: Throwable) {
                selectedModelOverride = previous
                views.modelLabel.text = previousLabel
                views.clearModelButton.visibility =
                    if (previous == null) View.GONE else View.VISIBLE
                views.modelSpinner.isEnabled = previous == null

                FileLogger.e(TAG, "Safe GGUF import failed", t)

                Toast.makeText(
                    this@VideoGenerationActivity,
                    "GGUF import failed: ${t.localizedMessage ?: "unknown"}",
                    Toast.LENGTH_LONG,
                ).show()
            } finally {
                views.selectModelButton.isEnabled = true
                if (!generationController.isGenerating()) {
                    views.generateButton.isEnabled = true
                }
            }
        }
    }

'''

s, n = pattern.subn(replacement, s, count=1)

if n != 1:
    raise SystemExit("ERROR: GGUF importer patch failed")

activity.write_text(s)
print("V12 GGUF importer patched")
