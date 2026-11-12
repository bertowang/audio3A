#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成强弱交替的语音段，实现带攻击/释放的 AGC，测量分段 RMS、增益起伏与钳位计数。

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
N = 12000
SEG = 2000
TARGET = 0.16
MAX_GAIN = 8.0
ATTACK = 0.004
RELEASE = 0.030

# ---- 计算与作图 ----
rng = random.Random(7)
base = synthetic_speech(rng, N)
noise = white_noise(rng, N, 0.002)
level = [0.15 if (i // SEG) % 2 == 0 else 1.0 for i in range(N)]
x = [base[i] * level[i] + noise[i] for i in range(N)]
env = rolling_rms(x, 256)
raw_g = [min(MAX_GAIN, TARGET / (e + 1e-4)) for e in env]
g = smooth(raw_g, ATTACK, RELEASE)
out = clip([x[i] * g[i] for i in range(N)])
before = [rms(x[s:s + SEG]) for s in range(0, N, SEG)]
after = [rms(out[s:s + SEG]) for s in range(0, N, SEG)]
clipped = sum(1 for v in out if abs(v) >= 0.999)
c = Chart(FIG / "14-agc.svg", "输入包络与 AGC 增益轨迹", xlabel="样本 / 200", ylabel="RMS 或归一化增益")
c.line(range(0, N, 200), [env[i] for i in range(0, N, 200)], BLUE, label="输入 RMS 包络")
c.line(range(0, N, 200), [g[i] / MAX_GAIN for i in range(0, N, 200)], RED, label="归一化增益")
print("包络图:", c.save())
b = Chart(FIG / "14-levels.svg", "各段 RMS：处理前 vs 处理后", xlabel="段序号", ylabel="RMS")
b.bars(range(len(before)), before, RED, label="处理前")
b.bars(range(len(after)), after, GREEN, label="处理后")
b.hline(TARGET, BLUE, label="目标 RMS")
print("电平图:", b.save())
write_wav(AUDIO / "14-before.wav", normalize_peak(x))
write_wav(AUDIO / "14-after.wav", out)
print("分段 RMS 前: " + " ".join("%.3f" % v for v in before))
print("分段 RMS 后: " + " ".join("%.3f" % v for v in after))
print("LUFS近似 %.1f -> %.1f | 增益 %.2f~%.2f | 钳位 %d | SAMPLE_RATE=%d" %
      (lufs_approx(x), lufs_approx(out), min(g), max(g), clipped, SAMPLE_RATE))
