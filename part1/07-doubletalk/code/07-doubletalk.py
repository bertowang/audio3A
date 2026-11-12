#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐帧计算归一化互相关做双讲判决，对照冻结/不冻结的权重误差，并用互相关峰值估计时延漂移。

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
N, L, FRAME = 4096, 64, 256
DT0, DT1 = 1536, 2560       # 双讲区间（样本）
THRESH = 0.90               # NCC 双讲阈值（实测单讲 ρ≈1、双讲 ρ≈0.82~0.87）
NEAR_GAIN = 1.8             # 近端语音电平
MU = 0.50                   # NLMS 步长
DRIFT = 8                   # 模拟时延漂移（样本）

# ---- 计算与作图 ----
rng = random.Random(7)
far = synthetic_speech(rng, N)
near_raw = synthetic_speech(rng, N)
near = [NEAR_GAIN * near_raw[i] if DT0 <= i < DT1 else 0.0 for i in range(N)]
h = rir(rng, L, decay=0.004, direct_delay=12)
echo = fft_convolve(far, h)[:N]
noise = white_noise(rng, N, 0.003)
mic = [echo[i] + near[i] + noise[i] for i in range(N)]
echo_hat = fft_convolve(far, h)[:N]

NFR = N // FRAME
rho, flags, truth = [], [], []
for f in range(NFR):
    s = f * FRAME
    num = sum(echo_hat[s + i] * mic[s + i] for i in range(FRAME))
    da = math.sqrt(sum(echo_hat[s + i] ** 2 for i in range(FRAME)))
    db = math.sqrt(sum(mic[s + i] ** 2 for i in range(FRAME)))
    r = num / (da * db + 1e-12)
    rho.append(r)
    flags.append(r < THRESH)
    truth.append(DT0 <= s < DT1)
tp = sum(1 for a, b in zip(flags, truth) if a and b)
fp = sum(1 for a, b in zip(flags, truth) if a and not b)
fn = sum(1 for a, b in zip(flags, truth) if not a and b)
tn = sum(1 for a, b in zip(flags, truth) if not a and not b)

w_frozen, w_free = h[:], h[:]
out_frozen, out_free = [0.0] * N, [0.0] * N
curve_frozen, curve_free = [], []
den_h = sum(v * v for v in h)
for n in range(L, N):
    xv = [far[n - i] for i in range(L)]
    f = min(n // FRAME, NFR - 1)
    is_dt = flags[f]
    y_f = sum(w_frozen[i] * xv[i] for i in range(L))
    y_u = sum(w_free[i] * xv[i] for i in range(L))
    e_f, e_u = mic[n] - y_f, mic[n] - y_u
    out_frozen[n], out_free[n] = e_f, e_u
    p = sum(v * v for v in xv) + 1e-3
    for i in range(L):
        w_free[i] += MU * e_u * xv[i] / p
        if not is_dt:
            w_frozen[i] += MU * e_f * xv[i] / p
    if n % FRAME == 0:
        curve_frozen.append(10 * math.log10(
            sum((w_frozen[i] - h[i]) ** 2 for i in range(L)) / (den_h + 1e-12) + 1e-12))
        curve_free.append(10 * math.log10(
            sum((w_free[i] - h[i]) ** 2 for i in range(L)) / (den_h + 1e-12) + 1e-12))

probe = white_noise(rng, 2048, 0.35)
h_a = rir(rng, 64, decay=0.004, direct_delay=12)
h_b = rir(rng, 64, decay=0.004, direct_delay=12 + DRIFT)
ya, yb = fft_convolve(probe, h_a)[:2048], fft_convolve(probe, h_b)[:2048]

def peak_lag(y):
    best, bp = -1.0, 0
    for lag in range(60):
        num = sum(probe[i] * y[i + lag] for i in range(1024))
        da = math.sqrt(sum(probe[i] ** 2 for i in range(1024)))
        db = math.sqrt(sum(y[i + lag] ** 2 for i in range(1024)))
        r = num / (da * db + 1e-12)
        if r > best:
            best, bp = r, lag
    return bp, best

la, pa = peak_lag(ya)
lb, pb = peak_lag(yb)
jump = sum((h_b[i] - h_a[i]) ** 2 for i in range(64)) / (sum(v * v for v in h_a) + 1e-12)

c = Chart(FIG / "07-ncc.svg", "逐帧归一化互相关与双讲判决", xlabel="帧 t", ylabel="ρ")
c.line(range(NFR), rho, BLUE, label="NCC ρ")
c.hline(THRESH, RED, label="判决阈值 τ")
c.vline(DT0 // FRAME, GREEN, label="双讲起")
c.vline(DT1 // FRAME, GREEN, label="双讲止")
print("检测图:", c.save())
d = Chart(FIG / "07-weight-error.svg", "双讲期间冻结 vs 不冻结的权重误差",
          xlabel="帧 t", ylabel="‖w−h‖²/‖h‖² (dB)")
d.line(range(len(curve_frozen)), curve_frozen, GREEN, label="检测到双讲即冻结")
d.line(range(len(curve_free)), curve_free, RED, label="全程照常更新")
print("权重图:", d.save())
write_wav(AUDIO / "07-mic.wav", normalize_peak(mic))
write_wav(AUDIO / "07-frozen.wav", normalize_peak(out_frozen))
write_wav(AUDIO / "07-unfrozen.wav", normalize_peak(out_free))
print("采样率=%d Hz 帧数=%d 帧长=%d 阈值=%.2f 双讲区间=[%d,%d)" %
      (SAMPLE_RATE, NFR, FRAME, THRESH, DT0, DT1))
print("双讲检测 TP=%d FP=%d FN=%d TN=%d | 检测率=%.3f 虚警率=%.3f 帧准确率=%.3f" %
      (tp, fp, fn, tn, tp / max(tp + fn, 1), fp / max(fp + tn, 1), (tp + tn) / NFR))
print("互相关峰值 lag 原=%d 漂移后=%d 估计漂移=%d 真值=%d 峰值ρ=%.3f" % (la, lb, lb - la, DRIFT, pb))
print("末帧权重误差 冻结=%.2f dB 不冻结=%.2f dB | 路径突变 ‖h_b−h_a‖²/‖h_a‖²=%.3f" %
      (curve_frozen[-1], curve_free[-1], jump))
