#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 NLMS 在线估计 h，画学习曲线、比较三个步长，并输出消除后的可听残差。

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
N, L = 6000, 96
MUS = (0.15, 0.50, 1.20)      # 三个步长对照
DELTA = 1e-3                   # 正则项
SMOOTH = 200                   # 学习曲线平滑窗

# ---- 计算与作图 ----
rng = random.Random(7)
far = white_noise(rng, N, 0.35)      # 白噪声激励充分，收敛最快
true_h = rir(rng, L, decay=0.004, direct_delay=12)
echo = fft_convolve(far, true_h)[:N]
target = [echo[i] + rng.gauss(0, 0.002) for i in range(N)]

def nlms(mu):
    w, errs, out = [0.0] * L, [], []
    for n in range(L, N):
        xv = [far[n - i] for i in range(L)]
        y = sum(w[i] * xv[i] for i in range(L))
        e = target[n] - y
        power = sum(v * v for v in xv) + DELTA
        for i in range(L):
            w[i] += mu * e * xv[i] / power
        errs.append(e * e)
        out.append(e)
    return w, errs, out

results = {mu: nlms(mu) for mu in MUS}

def smooth_curve(vals, win):
    out, v = [], 0.0
    for i, x in enumerate(vals):
        v = v + (x - v) / min(i + 1, win)
        out.append(10 * math.log10(v + 1e-12))
    return out

c = Chart(FIG / "05-learning.svg", "NLMS 学习曲线：不同步长的残差能量 (dB)",
          xlabel="迭代样本", ylabel="dB")
for mu, color in zip(MUS, (BLUE, GREEN, RED)):
    c.line(range(len(results[mu][1])), smooth_curve(results[mu][1], SMOOTH),
           color, label="μ=%.2f" % mu)
print("学习图:", c.save())
w = Chart(FIG / "05-weights.svg", "μ=0.50 时估计的滤波器系数 vs 真实 RIR",
          xlabel="抽头 k", ylabel="幅度")
w.line(range(L), true_h, "#9aa6b2", label="真实 h[k]")
w.line(range(L), results[0.50][0], RED, label="估计 w[k]")
print("权重图:", w.save())
write_wav(AUDIO / "05-before.wav", normalize_peak(target))
write_wav(AUDIO / "05-error.wav", normalize_peak(results[0.50][2]))
for mu in MUS:
    wt, errs, out = results[mu]
    mse = statistics.fmean(errs[len(errs) // 2:])
    werr = math.sqrt(sum((a - b) ** 2 for a, b in zip(wt, true_h)))
    print("μ=%.2f 稳态MSE=%.6f 权重误差=%.4f 输出/输入能量比=%.4f" %
          (mu, mse, werr, sum(v * v for v in out) / sum(v * v for v in target)))
print("前半段均方误差=%.6f 后半段=%.6f（下降说明收敛）" %
      (statistics.fmean(results[0.50][1][:1000]),
       statistics.fmean(results[0.50][1][-1000:])))
