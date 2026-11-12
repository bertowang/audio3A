#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在单讲、双讲、强噪声、路径突变四种场景下运行同一条链路，输出指标热力图。

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
N_FFT, HOP = 256, 128
LEAK = 0.03
NOISE_AMP = 0.020
TARGET = 0.16

# ---- 计算与作图 ----
rng = random.Random(7)
far = synthetic_speech(rng, N)
near = synthetic_speech(rng, N)
h1 = rir(rng, 128, decay=0.006)
h2 = rir(rng, 128, decay=0.006, direct_delay=31)
e1 = fft_convolve(far, h1)[:N]
e2 = fft_convolve(far, h2)[:N]
SCENARIOS = ("单讲基准", "强双讲", "强噪声", "路径突变")
LEAKS = (LEAK, 2.4 * LEAK, 1.9 * LEAK, LEAK)

def scenario(idx):
    near_gain = 0.9 if idx == 1 else 0.5
    clean = [near_gain * near[i] for i in range(N)]
    amp = 0.09 if idx == 2 else NOISE_AMP
    noise = white_noise(rng, N, amp)
    echo = [1.4 * (e2[i] if (idx == 3 and i >= N // 2) else e1[i]) for i in range(N)]
    mic = [clean[i] + echo[i] + noise[i] for i in range(N)]
    # 线性 AEC：已知 h1 加场景相关的受控泄漏；路径突变场景后半段来不及重收敛
    ref = [1.4 * e1[i] for i in range(N)]
    stage = [mic[i] - (1.0 - LEAKS[idx]) * ref[i] for i in range(N)]
    nf = stft(noise, N_FFT, HOP)[:8]
    nmag = [sum(math.hypot(re[k], im[k]) for re, im in nf) / len(nf) for k in range(N_FFT)]
    frames = stft(stage, N_FFT, HOP)
    for re, im in frames:
        for k in range(N_FFT):
            g = max(0.15, 1.0 - 1.2 * nmag[k] / (math.hypot(re[k], im[k]) + 1e-9))
            re[k] *= g
            im[k] *= g
    enhanced = istft(frames, N_FFT, HOP, N)
    gain = min(6.0, TARGET / (rms(enhanced) + 1e-6))
    out = clip([v * gain for v in enhanced])
    residual = [stage[i] - clean[i] - noise[i] for i in range(N)]
    return (erle_db(echo, residual),
            seg_snr_db(clean, scale_align(mic, clean)),
            seg_snr_db(clean, scale_align(out, clean)),
            si_sdr_db(out, clean), lufs_approx(out), mic, out)

rows, mics, outs = [], [], []
for i in range(len(SCENARIOS)):
    a, b, c, d, e, m, o = scenario(i)
    rows.append([round(a, 2), round(b, 2), round(c, 2), round(d, 2), round(e, 1)])
    mics.append(m)
    outs.append(o)
c = Chart(FIG / "18-scenarios.svg", "四类场景的处理前后分段 SNR", xlabel="场景", ylabel="dB",
          xticks=[(i, s) for i, s in enumerate(SCENARIOS)])
c.bars(range(4), [r[1] for r in rows], RED, label="处理前")
c.bars(range(4), [r[2] for r in rows], GREEN, label="处理后")
print("场景图:", c.save())
heatmap(FIG / "18-matrix.svg", [[r[0] for r in rows], [r[1] for r in rows],
                                [r[2] for r in rows], [r[3] for r in rows], [r[4] for r in rows]],
        ["ERLE", "输入segSNR", "输出segSNR", "SI-SDR", "LUFS近似"], list(SCENARIOS),
        title="四类场景的指标矩阵", vmin=-20, vmax=35, annotate=True)
print("矩阵图:", str(FIG / "18-matrix.svg"))
write_wav(AUDIO / "18-doubletalk-mic.wav", normalize_peak(mics[1]))
write_wav(AUDIO / "18-doubletalk-out.wav", normalize_peak(outs[1]))
for s, r in zip(SCENARIOS, rows):
    print("%s: ERLE=%.2f segSNR %.2f->%.2f SI-SDR=%.2f LUFS≈%.1f" %
          (s, r[0], r[1], r[2], r[3], r[4]))
print("SAMPLE_RATE=%d | 场景数=%d | 链路: AEC -> ANS -> AGC" % (SAMPLE_RATE, len(SCENARIOS)))
