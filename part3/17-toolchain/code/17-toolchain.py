#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""模拟 volumedetect/astats → dynaudnorm → loudnorm 三阶段，打印可核对的电平报告。

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
N = 8000
WIN = 800
TARGET_LUFS = -23.0
MAX_GAIN = 4.0
MAX_DYN_GAIN = 80.0     # 动态归一化增益上限：太小则弱段抬不动
ATK, REL = 0.20, 0.20    # 增益平滑的攻击/释放系数

# ---- 计算与作图 ----
rng = random.Random(7)
base = synthetic_speech(rng, N)
level = [0.25 if i < N // 2 else 1.0 for i in range(N)]
x = [0.35 * base[i] * level[i] for i in range(N)]
peak = max(abs(v) for v in x)
mean_db = 20 * math.log10(rms(x) + 1e-12)
peak_db = 20 * math.log10(peak + 1e-12)
blocks = [rms(x[s:s + WIN]) for s in range(0, N, WIN)]
g_block = [min(MAX_DYN_GAIN, 0.16 / (b + 1e-6)) for b in blocks]
raw_g = [g_block[min(i // WIN, len(g_block) - 1)] for i in range(N)]
g = smooth(raw_g, ATK, REL)
dyn = clip([x[i] * g[i] for i in range(N)])
l0 = lufs_approx(dyn)
gain = min(MAX_GAIN, 10 ** ((TARGET_LUFS - l0) / 20.0))
norm = clip([v * gain for v in dyn])
l1 = lufs_approx(norm)
blocks_after = [rms(norm[s:s + WIN]) for s in range(0, N, WIN)]
c = Chart(FIG / "17-levels.svg", "逐块 RMS：输入 / dynaudnorm 阶段 / loudnorm 阶段",
          xlabel="块序号 / 800 样本", ylabel="RMS")
c.line(range(len(blocks)), blocks, "#9aa6b2", label="输入")
c.line(range(len(blocks)), [rms(dyn[s:s + WIN]) for s in range(0, N, WIN)], BLUE, label="动态归一化")
c.line(range(len(blocks_after)), blocks_after, GREEN, label="响度归一化")
print("电平图:", c.save())
b = Chart(FIG / "17-gain.svg", "动态归一化阶段的增益轨迹", xlabel="样本 / 200", ylabel="增益")
b.line(range(0, N, 200), [g[i] for i in range(0, N, 200)], RED, label="g[n]")
print("增益图:", b.save())
write_wav(AUDIO / "17-input.wav", normalize_peak(x))
write_wav(AUDIO / "17-normalized.wav", norm)
print("volumedetect 口径: mean_volume=%.2f dB max_volume=%.2f dB" % (mean_db, peak_db))
print("astats 口径: 分块 RMS 前 %.4f~%.4f (%.1f×) 后 %.4f~%.4f (%.1f×)" %
      (min(blocks), max(blocks), max(blocks) / max(min(blocks), 1e-9),
       min(blocks_after), max(blocks_after), max(blocks_after) / max(min(blocks_after), 1e-9)))
print("ebur128 口径(教学近似): LUFS %.2f -> %.2f | 二遍增益=%.3f | SAMPLE_RATE=%d" %
      (l0, l1, gain, SAMPLE_RATE))
