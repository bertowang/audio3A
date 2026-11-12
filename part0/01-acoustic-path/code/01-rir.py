#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成含直达声与混响尾的 RIR，卷积出回声，再用归一化互相关估计延迟。

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
TRUE_DELAY = 24             # 真实直达声延迟（样本）
RIR_LEN = 256               # 冲激响应长度
DECAY = 0.008               # 混响能量衰减时间常数（秒）
CORR_LEN = 2048             # 互相关累加点数
MAX_LAG = 120               # 搜索的最大延迟

# ---- 计算与作图 ----
rng = random.Random(7)
far = synthetic_speech(rng, N)
probe = white_noise(rng, N, 0.35)     # 宽带探测信号：自相关接近冲激，便于对齐
h = rir(rng, RIR_LEN, decay=DECAY, direct_delay=TRUE_DELAY)
echo = fft_convolve(far, h)[:N]
near = [0.30 * v for v in synthetic_speech(rng, N)]
mic = [near[i] + echo[i] for i in range(N)]
probe_echo = fft_convolve(probe, h)[:N]
mic_probe = [probe_echo[i] + 0.3 * near[i] for i in range(N)]

# 归一化互相关：用参考信号 x 与麦克风 y 找最强线性相关的滞后
def norm_corr(a, b, lag, k):
    num = sum(a[i] * b[i + lag] for i in range(k))
    da = math.sqrt(sum(a[i] ** 2 for i in range(k)))
    db_ = math.sqrt(sum(b[i + lag] ** 2 for i in range(k)))
    return num / (da * db_ + 1e-12)

lags = list(range(MAX_LAG))
corr = [norm_corr(probe, mic_probe, lag, CORR_LEN) for lag in lags]
best_lag = lags[max(range(len(lags)), key=lambda i: corr[i])]
peak = max(corr)

c = Chart(FIG / "01-rir.svg", "合成房间冲激响应 h[k]", xlabel="抽头 k（16 kHz）", ylabel="幅度")
c.line(range(RIR_LEN), h, BLUE, label="h[k]")
c.vline(TRUE_DELAY, RED, label="真实直达延迟")
print("冲激图:", c.save())
d = Chart(FIG / "01-corr.svg", "参考信号与麦克风信号的归一化互相关",
          xlabel="滞后 lag", ylabel="相关系数")
d.line(lags, corr, GREEN, label="归一化互相关")
d.vline(best_lag, RED, label="峰值")
print("互相关图:", d.save())
write_wav(AUDIO / "01-far.wav", normalize_peak(far))
write_wav(AUDIO / "01-mic.wav", normalize_peak(mic))
print("真实延迟=%d 估计延迟=%d 峰值相关=%.3f | 直达增益=%.3f RIR能量=%.4f" %
      (TRUE_DELAY, best_lag, peak, h[TRUE_DELAY], sum(v * v for v in h)))
print("混响时间常数=%.4f s 理论 T60≈%.3f s（指数衰减到 -60 dB）" %
      (DECAY, 6.9 * DECAY))
