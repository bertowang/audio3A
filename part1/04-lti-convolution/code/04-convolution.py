#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在不同滤波器长度下比较两种实现的最大误差与耗时，并观察混响尾能量。

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
LENS = (64, 128, 256, 512, 1024, 2048)   # 扫描到 2048，加速比才明显
DECAY = 0.006

# ---- 计算与作图 ----
rng = random.Random(7)
x = white_noise(rng, N, 0.4)
errors, t_naive, t_fft = [], [], []
for L in LENS:
    h = rir(rng, L, decay=DECAY, direct_delay=min(24, L // 4))
    t0 = time.perf_counter()
    a = convolve(x[:1200], h)
    t1 = time.perf_counter()
    b = fft_convolve(x[:1200], h)
    t2 = time.perf_counter()
    errors.append(max(abs(u - v) for u, v in zip(a, b)))
    t_naive.append(t1 - t0)
    t_fft.append(t2 - t1)

h = rir(rng, 256, decay=DECAY)
wet = fft_convolve(synthetic_speech(rng, N), h)[:N]
energy = [10 * math.log10(sum(v * v for v in h[i:i + 16]) / 16 + 1e-12)
          for i in range(0, len(h) - 16, 16)]
c = Chart(FIG / "04-complexity.svg", "两种卷积实现的耗时对比（毫秒）",
          xlabel="滤波器长度 L", ylabel="耗时 ms",
          xticks=[(i, "L=%d" % L) for i, L in enumerate(LENS)])
c.bars(range(len(LENS)), [1000 * t for t in t_naive], RED, label="朴素 O(L)")
c.bars(range(len(LENS)), [1000 * t for t in t_fft], GREEN, label="分块频域 OLA")
print("复杂度图:", c.save())
e = Chart(FIG / "04-rir-energy.svg", "RIR 分段能量衰减（dB）", xlabel="16 抽头块", ylabel="dB")
e.line(range(len(energy)), energy, BLUE, label="分段能量")
print("能量图:", e.save())
write_wav(AUDIO / "04-dry.wav", normalize_peak(x))
write_wav(AUDIO / "04-wet.wav", normalize_peak(wet))
print("最大数值误差: " + " ".join("L=%d→%.1e" % (L, e) for L, e in zip(LENS, errors)))
print("L=%d 时 朴素=%.1fms 频域=%.1fms 加速=%.1f× | RIR能量衰减 %.1f dB" %
      (LENS[-1], 1000 * t_naive[-1], 1000 * t_fft[-1], t_naive[-1] / max(t_fft[-1], 1e-9),
       energy[0] - energy[-1]))
