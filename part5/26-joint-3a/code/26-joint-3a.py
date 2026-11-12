#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构造回声、噪声、时变电平三种退化与三个 oracle 校正，扫描权重画出综合得分热力图。

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
N = 6000
LEVEL_MIN, LEVEL_SWING = 0.85, 0.15   # 时变电平（AGC 要修的退化）
GRID = (0.0, 0.25, 0.50, 0.75, 1.00)

# ---- 计算与作图 ----
rng = random.Random(7)
clean = synthetic_speech(rng, N)
far = synthetic_speech(rng, N)
h = rir(rng, 128, decay=0.006)
echo = [0.35 * v for v in fft_convolve(far, h)[:N]]
noise = white_noise(rng, N, 0.070)
level = [LEVEL_MIN + LEVEL_SWING * math.sin(2 * math.pi * i / N) for i in range(N)]
base = [clean[i] + echo[i] + noise[i] for i in range(N)]
y = [level[i] * base[i] for i in range(N)]
# 三个 oracle 校正：各自只负责一种退化，权重之和为 1 意味着算力/预算被分摊
corr_aec = [-level[i] * echo[i] for i in range(N)]
corr_ans = [-level[i] * noise[i] for i in range(N)]
corr_agc = [(1.0 - level[i]) * base[i] for i in range(N)]
echo_scaled = [level[i] * echo[i] for i in range(N)]

def task_score(w):
    return min(35.0, -20.0 * math.log10(max(1e-4, 1.0 - w)))
def apply(w1, w2):
    w3 = 1.0 - w1 - w2
    out = [y[i] + w1 * corr_aec[i] + w2 * corr_ans[i] + w3 * corr_agc[i] for i in range(N)]
    residual = [out[i] - clean[i] for i in range(N)]
    e = erle_db(echo_scaled, residual)
    s = seg_snr_db(clean, scale_align(out, clean))
    tasks = [task_score(w) for w in (w1, w2, w3)]
    return min(tasks), tasks, out, e, s
matrix, best = [], (-1e9, 0.0, 0.0, None)
for w1 in GRID:
    row = []
    for w2 in GRID:
        if w1 + w2 > 1.0 + 1e-9:
            row.append(-20.0)
            continue
        score, tasks, out, e, s = apply(w1, w2)
        row.append(round(score, 2))
        if score > best[0]:
            best = (score, w1, w2, out)
    matrix.append(row)
eq_out = apply(1.0 / 3, 1.0 / 3)[2]
a1, a2, a3 = apply(0.75, 0.15), apply(1.0 / 3, 1.0 / 3), apply(0.15, 0.75)
c = Chart(FIG / "26-grid.svg", "三种权重下三个任务各自的抑制比", xlabel="权重组合", ylabel="dB",
          xticks=[(0, "偏AEC"), (1, "均衡"), (2, "偏ANS")])
for j, (name, color) in enumerate((("AEC 抑制比", BLUE), ("ANS 抑制比", GREEN), ("AGC 抑制比", AMBER))):
    dx = (j - 1) * 0.24
    c.bars([i + dx for i in range(3)], [a[1][j] for a in (a1, a2, a3)], color, label=name)
print("任务图:", c.save())
heatmap(FIG / "26-surface.svg", matrix,
        ["w1=%.2f" % v for v in GRID], ["w2=%.2f" % v for v in GRID],
        title="最短板得分 min(S_aec,S_ans,S_agc) 的权重曲面", vmin=-20, vmax=12, annotate=True)
print("曲面图:", str(FIG / "26-surface.svg"))
write_wav(AUDIO / "26-equal.wav", normalize_peak(eq_out))
write_wav(AUDIO / "26-best.wav", normalize_peak(best[3]))
for name, a in (("偏AEC", a1), ("均衡", a2), ("偏ANS", a3)):
    print("%s 三项抑制比(AEC/ANS/AGC)=%.1f/%.1f/%.1f dB | 最短板=%.1f dB" %
          (name, a[1][0], a[1][1], a[1][2], a[0]))
print("最短板最优=%.2f dB (w1=%.2f w2=%.2f w3=%.2f) | SAMPLE_RATE=%d" %
      (best[0], best[1], best[2], 1.0 - best[1] - best[2], SAMPLE_RATE))
