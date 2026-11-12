#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 tanh 制造非线性回声，跑线性 NLMS 后做逐 bin 后滤波，打印 β 扫描下的残余 ERLE 与双讲保真度。

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
BETAS = (0.4, 1.0, 2.0)   # 残余抑制强度扫描
GAMMA = 0.20               # 残余回声功率泄漏系数
FLOOR = 0.12               # 谱增益下限
DT_START = int(0.55 * N)   # 双讲起点

# ---- 计算与作图 ----
rng = random.Random(7)
far = synthetic_speech(rng, N)
h = rir(rng, L, decay=0.005, direct_delay=12)
linear_echo = fft_convolve(far, h)[:N]
echo = [math.tanh(1.8 * v) for v in linear_echo]
near_raw = synthetic_speech(rng, N)
near = [0.7 * near_raw[i] if i >= DT_START else 0.0 for i in range(N)]
noise = white_noise(rng, N, 0.004)
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

def postfilter(beta):
    out_frames = []
    for t, (re, im) in enumerate(ef):
        rr, ii = re[:], im[:]
        ehr, ehi = eh[t]
        for k in range(NF):
            pe = re[k] ** 2 + im[k] ** 2
            pr = GAMMA * (ehr[k] ** 2 + ehi[k] ** 2)
            g = max(FLOOR, 1.0 - beta * pr / (pe + 1e-9))
            rr[k] *= g
            ii[k] *= g
        out_frames.append((rr, ii))
    return istft(out_frames, NF, HOP, N)

def resid_erle(sig, lo, hi):
    r = [sig[i] - near[i] for i in range(lo, hi)]
    return erle_db(echo[lo:hi], r)

results = []
for beta in BETAS:
    o = postfilter(beta)
    o_dt = scale_align(o[DT_START:], near[DT_START:])
    results.append((beta, o, resid_erle(o, 0, DT_START),
                    seg_snr_db(near[DT_START:], o_dt),
                    si_sdr_db(o_dt, near[DT_START:])))

def avg_spec_db(x):
    fr = stft(x, NF, HOP)
    half = NF // 2
    acc = [0.0] * half
    for re, im in fr:
        for k in range(half):
            acc[k] += re[k] ** 2 + im[k] ** 2
    return [10 * math.log10(a / len(fr) + 1e-12) for a in acc]

s_lin, s_out = avg_spec_db(err_linear), avg_spec_db(results[1][1])

c = Chart(FIG / "11-tradeoff.svg", "抑制强度折中：残余 ERLE vs 双讲近端保真",
          xlabel="beta（残余抑制因子）", ylabel="dB",
          xticks=[(i, "beta=%.1f" % BETAS[i]) for i in range(len(BETAS))])
c.line(range(len(results)), [r[2] for r in results], BLUE, label="残余回声 ERLE (dB)")
c.line(range(len(results)), [r[4] for r in results], GREEN, label="双讲段 SI-SDR (dB)")
c.line(range(len(results)), [r[3] for r in results], AMBER, label="双讲段 segSNR (dB)")
print("折中图:", c.save())
d = Chart(FIG / "11-spectrum.svg", "后滤波前后的平均功率谱", xlabel="频率箱 k", ylabel="功率 dB")
d.line(range(len(s_lin)), s_lin, RED, label="线性 AEC 误差谱")
d.line(range(len(s_out)), s_out, GREEN, label="残余抑制后谱")
print("谱图:", d.save())
write_wav(AUDIO / "11-mic.wav", normalize_peak(mic))
write_wav(AUDIO / "11-linear.wav", normalize_peak(err_linear))
write_wav(AUDIO / "11-suppressed.wav", normalize_peak(results[1][1]))
print("采样率=%d Hz 非线性=tanh(1.8x) 线性抽头=%d 频率箱=%d 箱宽=%.1f Hz" %
      (SAMPLE_RATE, L, NF, SAMPLE_RATE / NF))
print("线性级残余ERLE=%.2f dB（削波成分无法被线性滤波器解释）" % resid_erle(err_linear, 0, DT_START))
for b, _o, er, ss, si in results:
    print("beta=%.1f 残余ERLE=%.2f dB 双讲segSNR=%.2f dB(下限−10) 双讲SI-SDR=%.2f dB" %
          (b, er, ss, si))
print("抑制前后平均谱能量差=%.2f dB" % (statistics.fmean(s_lin) - statistics.fmean(s_out)))
