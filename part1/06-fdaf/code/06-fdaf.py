#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在有色激励下对照频域逐 bin 最小二乘辨识与时域 NLMS 的收敛，输出权重误差、收敛块号与 ERLE。

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
N = 4096                  # 约 0.25 s @ 16 kHz
NF, L, B = 128, 64, 64     # FFT 长度 / 滤波器抽头 / 每块新样本，满足 NF ≥ B+L−1
NB = N // B                # 分块数
MU = 0.45                  # 时域对照 NLMS 步长
DELTA = 0.02               # 频域分母正则项（过大会拖慢收敛）
OBS_NOISE = 0.02           # 频域观测扰动（模拟近端/量化噪声）

# ---- 计算与作图 ----
rng = random.Random(7)
far = [0.75 * a + 0.25 * b for a, b in
       zip(synthetic_speech(rng, N), white_noise(rng, N, 0.18))]
h = rir(rng, L, decay=0.004, direct_delay=12)
echo = fft_convolve(far, h)[:N]
hr, hi = fft(h + [0.0] * (NF - L), [0.0] * NF)
den_h = sum(hr[k] ** 2 + hi[k] ** 2 for k in range(NF))

Sxx = [1e-6] * NF
Sxy_r, Sxy_i = [0.0] * NF, [0.0] * NF
hist = [0.0] * (NF - B)
curve_fd, bin_power = [], []
for b in range(NB):
    xnew = far[b * B:(b + 1) * B]
    frame = hist + xnew
    xr, xi = fft(frame[:], [0.0] * NF)
    dr = [hr[k] * xr[k] - hi[k] * xi[k] + rng.gauss(0, OBS_NOISE) for k in range(NF)]
    di = [hr[k] * xi[k] + hi[k] * xr[k] + rng.gauss(0, OBS_NOISE) for k in range(NF)]
    for k in range(NF):
        p = xr[k] * xr[k] + xi[k] * xi[k]
        Sxx[k] += p
        Sxy_r[k] += dr[k] * xr[k] + di[k] * xi[k]
        Sxy_i[k] += di[k] * xr[k] - dr[k] * xi[k]
    wr = [Sxy_r[k] / (Sxx[k] + DELTA) for k in range(NF)]
    wi = [Sxy_i[k] / (Sxx[k] + DELTA) for k in range(NF)]
    num = sum((wr[k] - hr[k]) ** 2 + (wi[k] - hi[k]) ** 2 for k in range(NF))
    curve_fd.append(10 * math.log10(num / (den_h + 1e-12) + 1e-12))
    hist = frame[B:]
    if b == NB // 2:
        bin_power = [10 * math.log10(Sxx[k] / (b + 1) + 1e-9) for k in range(NF // 2)]

w = [0.0] * L
curve_td = []
for b in range(NB):
    for off in range(B):
        n = b * B + off + L
        if n >= N:
            break
        xv = [far[n - i] for i in range(L)]
        y = sum(w[i] * xv[i] for i in range(L))
        e = echo[n] - y + rng.gauss(0, OBS_NOISE)   # 与频域分支一致的观测噪声
        p = sum(v * v for v in xv) + 1e-3
        for i in range(L):
            w[i] += MU * e * xv[i] / p
    num = sum((w[i] - h[i]) ** 2 for i in range(L))
    den = sum(v * v for v in h)
    curve_td.append(10 * math.log10(num / (den + 1e-12) + 1e-12))

wt, _dummy = fft(wr[:], wi[:], inverse=True)
w_hat = wt[:L]
y_hat = fft_convolve(far, w_hat)[:N]
residual = [echo[i] - y_hat[i] for i in range(N)]

def first_below(curve, thr):
    for i, v in enumerate(curve):
        if v < thr:
            return i + 1
    return -1

c = Chart(FIG / "06-convergence.svg", "权重误差范数：频域逐 bin vs 时域 NLMS",
          xlabel="分块序号", ylabel="权重误差 (dB)")
c.line(range(NB), curve_fd, BLUE, label="分块频域（逐 bin 归一化）")
c.line(range(NB), curve_td, RED, label="时域 NLMS")
c.hline(-15.0, GREEN, label="−15 dB 收敛线")
print("收敛图:", c.save())
d = Chart(FIG / "06-bins.svg", "有色激励各频率箱功率（体现逐 bin 白化的必要性）",
          xlabel="频率箱 k", ylabel="功率 dB")
d.line(range(len(bin_power)), bin_power, AMBER, label="|X[k]|² 平滑均值")
d.hline(statistics.fmean(bin_power), BLUE, label="全带均值")
print("功率图:", d.save())
write_wav(AUDIO / "06-far.wav", normalize_peak(far))
write_wav(AUDIO / "06-echo.wav", normalize_peak(echo))
write_wav(AUDIO / "06-residual.wav", normalize_peak(residual))
print("采样率=%d Hz 分块数=%d FFT=%d 抽头=%d 块长=%d" % (SAMPLE_RATE, NB, NF, L, B))
print("频域收敛到 −15dB 的块号=%d 时域=%d | 末块权重误差 频域=%.2f dB 时域=%.2f dB" %
      (first_below(curve_fd, -15.0), first_below(curve_td, -15.0), curve_fd[-1], curve_td[-1]))
print("ERLE(收敛权重重算回声)=%.2f dB | 残余/回声 RMS=%.4f" %
      (erle_db(echo, residual), rms(residual) / (rms(echo) + 1e-9)))
