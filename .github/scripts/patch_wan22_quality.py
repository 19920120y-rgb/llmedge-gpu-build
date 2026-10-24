#!/usr/bin/env python3
"""Quality-oriented post-patch for an existing Clean I2V source build.

Does not convert/reshape GGUF tensors. Does not touch model files or Android data.
Raises on unexpected upstream changes instead of building an unverified variant.
"""
from pathlib import Path
import re
import sys

ACT = Path('llmedge/llmedge-examples/app/src/main/java/com/example/llmedgeexample/demo/video/VideoGenerationActivity.kt')
FORM = Path('llmedge/llmedge-examples/app/src/main/java/com/example/llmedgeexample/demo/video/VideoGenerationFormSupport.kt')
MARKER = 'WAN22_QUALITY_DIRECT_GGUF_V1'


def replace_single(s, pattern, replacement, description):
    out, n = re.subn(pattern, replacement, s, count=1)
    if n != 1:
        raise RuntimeError(f'{description}: missing source marker')
    return out


def quality_patch(root=Path('.')):
    activity, form = root / ACT, root / FORM
    if not activity.is_file() or not form.is_file():
        raise RuntimeError('Official video source files missing; no changes applied')
    a0, f0 = activity.read_text('utf8'), form.read_text('utf8')
    if MARKER in a0 and 'return 3.0f' in f0:
        return 'ALREADY_PATCHED'
    if MARKER in a0:
        raise RuntimeError('Partial old patch, refusing to continue')
    if 'selectedTextEncoderOverride' not in a0 or 'taehvPath = selectedTaehvPath' not in a0:
        raise RuntimeError('Clean I2V prerequisite missing: T5/TAEHV')
    if 'vae = null' not in a0 or 'textEncoder = selectedTextEncoderOverride' not in a0:
        raise RuntimeError('Clean I2V model wiring differs from expected version')
    if 'views.modelSpinner.setSelection(2)' not in a0:
        raise RuntimeError('Wan 2.2 5B model preset differs from expected version')

    a = a0
    a = replace_single(a, r'(?m)^(\s*private const val DEFAULT_STEPS = )\d+(\s*)$', r'\g<1>20\2', 'steps')
    a = replace_single(a, r'(?m)^(\s*private const val DEFAULT_CFG = )\d+(?:\.\d+)?f(\s*)$', r'\g<1>6.0f\2', 'cfg')
    a = replace_single(a, r'(?m)^(\s*private const val DEFAULT_FRAMES = )\d+(\s*)$', r'\g<1>5\2', 'frames')
    if a.count('views.progressBar.progress = 0') != 1:
        raise RuntimeError('UI initialisation location mismatch')
    a = a.replace('views.progressBar.progress = 0',
      'views.progressBar.progress = 0\n        // '+MARKER+'\n        if (views.flowShiftInput.text.isNullOrBlank()) {\n            views.flowShiftInput.setText("3.0")\n        }', 1)
    if 'return Float.POSITIVE_INFINITY' not in f0:
        raise RuntimeError('Flow Shift default source mismatch')
    f = f0.replace('return Float.POSITIVE_INFINITY', 'return 3.0f', 1)
    if f.count('value > 0f') != 1:
        raise RuntimeError('Flow Shift finite validation location mismatch')
    f = f.replace('value > 0f', 'value.isFinite() && value > 0f', 1)
    if 'return 3.0f' not in f or MARKER not in a:
        raise RuntimeError('Invalid generated patch')
    # Prepare and validate both replacements before updating either original.
    tmpa, tmpf = activity.with_suffix('.kt.wan22-new'), form.with_suffix('.kt.wan22-new')
    tmpa.write_text(a, 'utf8')
    tmpf.write_text(f, 'utf8')
    tmpa.replace(activity)
    tmpf.replace(form)
    return 'PATCHED: direct model GGUF + Flow Shift 3.0; Steps 20; CFG 6.0; Frames 5'

if __name__ == '__main__':
    try:
        print(quality_patch())
    except Exception as e:
        print('STOP: ' + str(e), file=sys.stderr)
        sys.exit(1)
