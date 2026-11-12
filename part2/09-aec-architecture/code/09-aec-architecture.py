#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成参考/近端/回声并跑完线性级与残余抑制级，打印各级 ERLE、segSNR 与 SI-SDR，输出可试听 WAV。

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
N, L, NF, HOP = 4096, 64, 256, 128
MU = 0.60                  # 线性级 NLMS 步长
LEAK = 0.12                # 残余回声功率泄漏系数 γ
BETA = 1.00                # 残余抑制强度 β
FLOOR = 0.18               # 谱增益下限

# ---- 计算与作图 ----
rng = random.Random(7)
far = synthetic_speech(rng, N)
near_raw = synthetic_speech(rng, N)
near = [0.7 * near_raw[i] if i > 0.6 * N else 0.0 for i in range(N)]
h = rir(rng, L, decay=0.005, direct_delay=12)
echo = fft_convolve(far, h)[:N]
noise = white_noise(rng, N, 0.005)
mic = [echo[i] + near[i] + noise[i] for i in range(N)]

w = [0.0] * L
echo_hat, err_linear = [0.0] * N, [0.0] * N
for n in range(L, N):
    xv = [far[n - i] for i in range(L)]
    y = sum(w[i] * xv[i] for i in range(L))
    echo_hat[n] = y
    e = mic[n] - y
    err_linear[n] = e
    p = sum(v * v for v in xv) + 1e-3
    for i in range(L):
        w[i] += MU * e * xv[i] / p

eh, ef = stft(echo_hat, NF, HOP), stft(err_linear, NF, HOP)
out_frames = []
for t, (re, im) in enumerate(ef):
    rr, ii = re[:], im[:]
    ehr, ehi = eh[t]
    for k in range(NF):
        pe = re[k] ** 2 + im[k] ** 2
        pr = LEAK * (ehr[k] ** 2 + ehi[k] ** 2)
        g = max(FLOOR, 1.0 - BETA * pr / (pe + 1e-9))
        rr[k] *= g
        ii[k] *= g
    out_frames.append((rr, ii))
out = istft(out_frames, NF, HOP, N)

DT_START = int(0.6 * N)
def resid_erle(sig, lo, hi):
    r = [sig[i] - near[i] for i in range(lo, hi)]
    return erle_db(echo[lo:hi], r)

erle_lin = resid_erle(err_linear, 0, DT_START)
erle_out = resid_erle(out, 0, DT_START)
s0 = seg_snr_db(near, mic)
s1 = seg_snr_db(near, err_linear)
s2 = seg_snr_db(near, scale_align(out, near))
si0 = si_sdr_db(mic[DT_START:], near[DT_START:])
si2 = si_sdr_db(scale_align(out[DT_START:], near[DT_START:]), near[DT_START:])

c = Chart(FIG / "09-stages.svg", "AEC 各级信号波形（前 1500 样本）", xlabel="样本", ylabel="幅度")
c.line(range(1500), mic[:1500], "#9aa6b2", label="麦克风 y", opacity=0.80)
c.line(range(1500), echo_hat[:1500], AMBER, label="线性预测 ŷ", opacity=0.85)
c.line(range(1500), err_linear[:1500], BLUE, label="线性级误差 e", opacity=0.90)
c.line(range(1500), out[:1500], GREEN, label="残余抑制输出 z", opacity=0.90)
print("波形图:", c.save())
d = Chart(FIG / "09-metrics.svg", "两级结构的 ERLE 与分段 SNR", xlabel="阶段", ylabel="dB",
          xticks=[(0, "麦克风"), (1, "线性后"), (2, "抑制后")])
d.bars([0, 1, 2], [0.0, erle_lin, erle_out], BLUE, label="ERLE (dB)")
d.bars([0, 1, 2], [s0, s1, s2], GREEN, label="segSNR (dB)")
print("指标图:", d.save())
write_wav(AUDIO / "09-mic.wav", normalize_peak(mic))
write_wav(AUDIO / "09-linear.wav", normalize_peak(err_linear))
write_wav(AUDIO / "09-final.wav", normalize_peak(out))
print("采样率=%d Hz 线性抽头=%d STFT=%d/%d 频率箱宽=%.1f Hz" %
      (SAMPLE_RATE, L, NF, HOP, SAMPLE_RATE / NF))
print("ERLE 线性级=%.2f dB 加残余抑制后=%.2f dB | 提升=%.2f dB" %
      (erle_lin, erle_out, erle_out - erle_lin))
print("segSNR 麦克风=%.2f 线性后=%.2f 输出=%.2f dB（−10 为下限钳位）| SI-SDR %.2f→%.2f dB" %
      (s0, s1, s2, si0, si2))
