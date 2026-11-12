#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用合成偏好响度拟合对数域增益律，比较无 AGC、固定目标与学习增益律的响度偏差。

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
LEVELS = (0.08, 0.15, 0.30, 0.50, 0.80, 1.20)
TRAIN_N = 4                 # 前 4 个电平用于拟合，后 2 个留出验证
FIXED_TARGET = 0.16
G_MIN, G_MAX = 0.20, 8.0

# ---- 计算与作图 ----
rng = random.Random(7)
base = synthetic_speech(rng, N)
def pref(level):
    return 0.10 + 0.06 * (1.0 - math.exp(-3.0 * level))
signals = [(L, [L * base[i] for i in range(N)]) for L in LEVELS]
xs, ys = [], []
for L, x in signals[:TRAIN_N]:
    r = rms(x) + 1e-9
    xs.append(math.log10(r))
    ys.append(math.log10(pref(L) / r))
mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
var = sum((v - mx) ** 2 for v in xs)
cov = sum((xs[i] - mx) * (ys[i] - my) for i in range(len(xs)))
a = cov / (var + 1e-12)
b = my - a * mx
rows = []
for L, x in signals:
    r = rms(x) + 1e-9
    gains = [1.0, min(G_MAX, FIXED_TARGET / r),
             max(G_MIN, min(G_MAX, 10 ** (a * math.log10(r) + b)))]
    outs = [clip([v * g for v in x]) for g in gains]
    rows.append((L, [rms(o) for o in outs], gains, outs, pref(L)))
c = Chart(FIG / "25-levels.svg", "各输入电平下的输出 RMS 与偏好曲线",
          xlabel="输入电平", ylabel="RMS", xticks=[(i, "%.2f" % L) for i, L in enumerate(LEVELS)])
c.line(range(len(LEVELS)), [r[1][0] for r in rows], "#9aa6b2", label="无 AGC")
c.line(range(len(LEVELS)), [r[1][1] for r in rows], BLUE, label="固定目标 AGC")
c.line(range(len(LEVELS)), [r[1][2] for r in rows], GREEN, label="学习增益律")
c.line(range(len(LEVELS)), [r[4] for r in rows], RED, label="偏好曲线")
print("电平图:", c.save())
g = Chart(FIG / "25-gains.svg", "固定目标与学习增益律的增益曲线",
          xlabel="输入电平", ylabel="增益", xticks=[(i, "%.2f" % L) for i, L in enumerate(LEVELS)])
g.line(range(len(LEVELS)), [r[2][1] for r in rows], BLUE, label="固定目标")
g.line(range(len(LEVELS)), [r[2][2] for r in rows], GREEN, label="学习增益律")
print("增益图:", g.save())
write_wav(AUDIO / "25-quiet.wav", normalize_peak(signals[0][1]))
write_wav(AUDIO / "25-learned.wav", rows[0][3][2])
mae = [sum(abs(r[1][m] - r[4]) for r in rows) / len(rows) for m in range(3)]
held = [sum(abs(r[1][m] - r[4]) for r in rows[TRAIN_N:]) / (len(rows) - TRAIN_N) for m in range(3)]
clips = sum(1 for r in rows for v in r[3][2] if abs(v) >= 0.999)
print("拟合: log g = %.3f * log L_in + %.3f | 训练电平=%d 留出=%d" % (a, b, TRAIN_N, len(LEVELS) - TRAIN_N))
print("响度偏差 MAE 无AGC=%.4f 固定=%.4f 学习=%.4f | 留出集: %.4f/%.4f/%.4f" %
      (mae[0], mae[1], mae[2], held[0], held[1], held[2]))
print("学习增益钳位样本=%d | SAMPLE_RATE=%d | 偏好曲线为人为设定" % (clips, SAMPLE_RATE))
