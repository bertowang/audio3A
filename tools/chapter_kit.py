#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""章节撰写套件：HTML 片段助手 + 统一 Python 实验样板。

所有实验脚本由 mk_demo() 拼装同一份零依赖样板：
    shebang → 标准库导入 → 引入 tools/dsp.py 与 tools/chart.py → random.seed(7)
    → 参数区 → 计算与作图 → 打印可核对数值 + 写出 fig/*.svg 与 audio/*.wav
读者只需关注「参数区」和「计算与作图」两段。
"""
from __future__ import annotations

from book_schema import demo

PREAMBLE = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""@DOC@

全部语音 / 噪声 / 房间冲激响应均为代码合成信号，仅用于教学演示机制与量级。
"""
from __future__ import annotations

import math
import pathlib
import random
import statistics
import sys
import time

_here = pathlib.Path(__file__).resolve()
for _p in _here.parents:
    if (_p / "tools" / "dsp.py").exists():
        sys.path.insert(0, str(_p / "tools"))
        break
from dsp import (SAMPLE_RATE, fft, hann, stft, istft, magnitude_db, spectrum,
                 white_noise, tone, chirp, synthetic_speech, rir, convolve,
                 fft_convolve, delay, clip, normalize_peak, rms, rolling_rms,
                 smooth, db, energy_db, snr_db, erle_db, seg_snr_db,
                 scale_align, si_sdr_db, lufs_approx,
                 write_wav, read_wav, wav_info)
from chart import Chart, heatmap, BLUE, RED, GREEN, AMBER

FIG = _here.parents[1] / "fig"
AUDIO = _here.parents[1] / "audio"
FIG.mkdir(exist_ok=True)
AUDIO.mkdir(exist_ok=True)

random.seed(7)

# ---- 参数区 ----
'''


def mk_demo(file, title, doc, params, body, figs=(), audio=(), steps="",
            expect="", tweak=""):
    """组装一个实验脚本。

    params : 参数区源码（纯文本，可含中文注释）
    body   : 计算与作图源码（须含 print 与 .save() / heatmap() / write_wav()）
    figs   : [(fig/xx.svg, 图注), ...]，与 body 写出的文件一一对应
    audio  : [(audio/xx.wav, 试听说明), ...]，与 body 写出的 WAV 一一对应
    steps / expect / tweak : 操作步骤、预期与判读、改参数提示
    """
    code = (PREAMBLE.replace("@DOC@", doc.strip())
            + params.strip("\n") + "\n\n"
            + "# ---- 计算与作图 ----\n" + body.strip("\n") + "\n")
    return demo(file, title, code, steps, expect, tweak, figs, audio)


def shell(title, code, note):
    """一段可选的真机命令（不参与批量运行，需自行安装对应工具）。"""
    return (title, code.strip("\n"), note)


# ---------------------------------------------------------------- HTML 片段
def p(s):
    return "<p>" + s + "</p>"


def ul(items):
    return "<ul>\n" + "\n".join("<li>" + x + "</li>" for x in items) + "\n</ul>"


def ol(items):
    return "<ol>\n" + "\n".join("<li>" + x + "</li>" for x in items) + "\n</ol>"


def note(label, body):
    return ('<div class="card note"><span class="card-label">' + label + "</span>"
            '<p style="margin-bottom:0">' + body + "</p></div>")


def warn(label, body):
    return ('<div class="card warn"><span class="card-label">' + label + "</span>"
            '<p style="margin-bottom:0">' + body + "</p></div>")


def sec(*parts):
    return "\n".join(parts)
