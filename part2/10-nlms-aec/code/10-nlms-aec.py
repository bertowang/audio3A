#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实现带双讲冻结的逐样本 NLMS，扫描三个步长与三个阶数，打印滑动 ERLE、收敛迭代数、权重误差与稳态 ERLE。

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
N, L = 3072, 64
MUS = (0.15, 0.50, 1.10)   # 步长扫描
LENS = (32, 64, 128)       # 阶数扫描
DELTA = 1e-3               # 正则项
DT_START = int(0.70 * N)   # 双讲起点（理想检测上界）
H_WIN = 256                # 滑动 ERLE 窗长

# ---- 计算与作图 ----
rng = random.Random(7)
sp = synthetic_speech(rng, N)
far = [0.78 * a + 0.22 * b for a, b in zip(sp, white_noise(rng, N, 0.18))]
h = rir(rng, 128, decay=0.006, direct_delay=20)
echo = fft_convolve(far, h)[:N]
near_raw = synthetic_speech(rng, N)
near = [0.65 * near_raw[i] if i >= DT_START else 0.0 for i in range(N)]
noise = white_noise(rng, N, 0.004)
mic = [echo[i] + near[i] + noise[i] for i in range(N)]

def run_nlms(mu, length):
    w = [0.0] * length
    err = [0.0] * N
    for n in range(length, N):
        xv = [far[n - i] for i in range(length)]
        y = sum(w[i] * xv[i] for i in range(length))
        e = mic[n] - y
        err[n] = e
        if n < DT_START:
            p = sum(v * v for v in xv) + DELTA
            for i in range(length):
                w[i] += mu * e * xv[i] / p
    curve = []
    for s in range(length, DT_START - H_WIN, H_WIN):
        curve.append(erle_db(echo[s:s + H_WIN], err[s:s + H_WIN]))
    werr = math.sqrt(sum((w[i] - h[i]) ** 2 for i in range(length)))
    steady = erle_db(echo[N // 2:DT_START], err[N // 2:DT_START])
    return curve, steady, werr, err

curves, steadies, werrs = [], [], []
best_err = None
for mu in MUS:
    cv, st, we, err = run_nlms(mu, L)
    curves.append(cv)
    steadies.append(st)
    werrs.append(we)
    if mu == 0.50:
        best_err = err
len_steadies = []
for ln in LENS:
    _cv, st, _we, _err = run_nlms(0.50, ln)
    len_steadies.append(st)

c = Chart(FIG / "10-learning.svg", "不同步长的滑动窗 ERLE 曲线", xlabel="窗序号", ylabel="ERLE (dB)")
for mu, cv, col in zip(MUS, curves, (BLUE, GREEN, RED)):
    c.line(range(len(cv)), cv, col, label="mu=%.2f" % mu)
c.hline(10.0, AMBER, label="10 dB 收敛线")
print("学习图:", c.save())
d = Chart(FIG / "10-erle-lens.svg", "滤波器阶数对稳态 ERLE 的影响", xlabel="抽头数 L", ylabel="ERLE (dB)",
          xticks=[(i, "L=%d" % ln) for i, ln in enumerate(LENS)])
d.bars(range(len(LENS)), len_steadies, BLUE, label="稳态 ERLE")
print("阶数图:", d.save())
write_wav(AUDIO / "10-mic.wav", normalize_peak(mic))
write_wav(AUDIO / "10-echo.wav", normalize_peak(echo))
write_wav(AUDIO / "10-error.wav", normalize_peak(best_err))
print("采样率=%d Hz 样本=%d 真值h=128抽头 双讲起点=%d 冻结=是 真值延迟=20" %
      (SAMPLE_RATE, N, DT_START))
for mu, st, we, cv in zip(MUS, steadies, werrs, curves):
    hit = next((i + 1 for i, v in enumerate(cv) if v >= 10.0), -1)
    print("mu=%.2f 稳态ERLE=%.2f dB 权重误差=%.4f 首次10dB窗=%d 约=%d样本" %
          (mu, st, we, hit, L + hit * H_WIN if hit > 0 else -1))
print("阶数扫描 稳态ERLE: " + " ".join("L=%d→%.2fdB" % (ln, s)
                                   for ln, s in zip(LENS, len_steadies)))
print("双讲段 segSNR=%.2f dB SI-SDR=%.2f dB" %
      (seg_snr_db(near[DT_START:], best_err[DT_START:]),
       si_sdr_db(best_err[DT_START:], near[DT_START:])))
