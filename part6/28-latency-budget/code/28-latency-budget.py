#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""列出链路延迟组成，并用计时实测三种 STFT 帧长下的实时因子。

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
N = 4000
REPEAT = 6
FFTS = (128, 256, 512)
BUDGET = (("采集/播放", 10.0), ("帧长与WOLA", 16.0), ("AEC分块", 4.0),
          ("神经推理", 6.0), ("AGC平滑", 2.0), ("抖动缓冲", 20.0), ("编解码", 10.0))

# ---- 计算与作图 ----
rng = random.Random(7)
sp = synthetic_speech(rng, N)
nz = white_noise(rng, N, 0.02)
sig = [sp[i] + nz[i] for i in range(N)]
rtfs, frame_ms = [], []
for n_fft in FFTS:
    hop = n_fft // 2
    t0 = time.perf_counter()
    for _ in range(REPEAT):
        frames = stft(sig, n_fft, hop)
        for re, im in frames:
            for k in range(n_fft):
                g = max(0.2, 1.0 - 0.3 / (math.hypot(re[k], im[k]) + 1e-9))
                re[k] *= g
                im[k] *= g
        out = istft(frames, n_fft, hop, N)
    elapsed = time.perf_counter() - t0
    rtfs.append(elapsed / (REPEAT * N / SAMPLE_RATE))
    frame_ms.append(1000.0 * hop / SAMPLE_RATE)
names = [b[0] for b in BUDGET]
values = [b[1] for b in BUDGET]
total = sum(values)
c = Chart(FIG / "28-budget.svg", "一份可逐行相加的端到端延迟预算（示意值）",
          xlabel="组成", ylabel="ms", xticks=[(i, n) for i, n in enumerate(names)])
c.bars(range(len(names)), values, BLUE, label="延迟 ms")
print("预算图:", c.save())
r = Chart(FIG / "28-rtf.svg", "三种帧长下实测的实时因子 RTF", xlabel="FFT 长度", ylabel="RTF",
          xticks=[(i, "%d" % v) for i, v in enumerate(FFTS)])
r.bars(range(len(FFTS)), rtfs, GREEN, label="实测 RTF")
r.hline(1.0, RED, label="实时上限 RTF=1")
print("RTF图:", r.save())
write_wav(AUDIO / "28-input.wav", normalize_peak(sig))
write_wav(AUDIO / "28-output.wav", normalize_peak(out))
print("延迟组成: " + " ".join("%s=%.0fms" % (n, v) for n, v in BUDGET))
print("单向合计=%.1f ms | 帧长(跳)=" % total + " ".join("%d=%.1fms" % (f, m) for f, m in zip(FFTS, frame_ms)))
print("实测 RTF: " + " ".join("%d=%.4f" % (f, v) for f, v in zip(FFTS, rtfs)))
print("SAMPLE_RATE=%d REPEAT=%d | 数值随机器而变，重点是口径" % (SAMPLE_RATE, REPEAT))
