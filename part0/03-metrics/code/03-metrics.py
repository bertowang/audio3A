#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描噪声与回声强度，计算 ERLE / segSNR / SI-SDR / LUFS，并演示 AGC 尺度错配。

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
AMPS = (0.004, 0.012, 0.030, 0.070)   # 噪声幅度扫描
ECHO_GAINS = (0.3, 0.9, 1.8, 3.0)     # 回声强度扫描

# ---- 计算与作图 ----
rng = random.Random(7)
clean = synthetic_speech(rng, N)
h = rir(rng, 128, decay=0.006)
far = synthetic_speech(rng, N)
echo_ref = fft_convolve(far, h)[:N]      # 卷积只算一次，避免在循环/推导里重复 O(N log N)
rows, noisy_samples = [], []
for amp in AMPS:
    nz = white_noise(rng, N, amp)
    noisy = [clean[i] + nz[i] for i in range(N)]
    noisy_samples.append(noisy)
    rows.append([snr_db(clean, nz), seg_snr_db(clean, noisy),
                 si_sdr_db(noisy, clean), lufs_approx(noisy)])
erle_rows = []
for g in ECHO_GAINS:
    echo = [g * v for v in echo_ref]
    mic = [clean[i] + echo[i] for i in range(N)]
    # 理想 AEC 上界：减去真实回声，残余只剩近端语音，用回声/残余比衡量
    erle_rows.append(erle_db(echo, clean))

c = Chart(FIG / "03-metrics.svg", "噪声增强时四个指标的变化", xlabel="噪声幅度", ylabel="数值",
          xticks=[(i, "%.3f" % a) for i, a in enumerate(AMPS)])
c.line(range(len(AMPS)), [r[1] for r in rows], BLUE, label="分段 SNR (dB)")
c.line(range(len(AMPS)), [r[2] for r in rows], GREEN, label="SI-SDR (dB)")
c.line(range(len(AMPS)), [r[0] for r in rows], AMBER, label="全局 SNR (dB)")
print("指标图:", c.save())
heatmap(FIG / "03-heatmap.svg", [[round(v, 2) for v in r] for r in rows],
        ["amp=%.3f" % a for a in AMPS], ["SNR", "segSNR", "SI-SDR", "LUFS"],
        title="不同噪声强度下的指标矩阵", vmin=-25, vmax=30, annotate=True)
print("矩阵图:", str(FIG / "03-heatmap.svg"))
write_wav(AUDIO / "03-clean.wav", normalize_peak(clean))
write_wav(AUDIO / "03-noisy.wav", normalize_peak(noisy_samples[2]))
write_wav(AUDIO / "03-echo.wav", normalize_peak(
    [clean[i] + 1.8 * echo_ref[i] for i in range(N)]))

# 尺度错配：把 clean 放大 2.5 倍后再直接算 segSNR
scaled = [2.5 * v for v in clean]
before = seg_snr_db(clean, scaled)
after = seg_snr_db(clean, scale_align(scaled, clean))
print("ERLE(理想AEC): " + " ".join("g=%.1f→%.1fdB" % (g, e)
                                  for g, e in zip(ECHO_GAINS, erle_rows)))
print("噪声扫描 segSNR: " + " ".join("amp=%.3f→%.2f" % (a, r[1]) for a, r in zip(AMPS, rows)))
print("噪声扫描 SI-SDR: " + " ".join("amp=%.3f→%.2f" % (a, r[2]) for a, r in zip(AMPS, rows)))
print("噪声 amp=%.3f 时 segSNR=%.2f SI-SDR=%.2f LUFS≈%.1f" %
      (AMPS[2], rows[2][1], rows[2][2], rows[2][3]))
print("AGC 尺度错配演示：直接相减 segSNR=%.2f dB，尺度对齐后=%.2f dB" % (before, after))
