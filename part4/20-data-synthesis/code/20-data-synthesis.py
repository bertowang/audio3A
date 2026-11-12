#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成带 seed 依赖谱峰的训练/测试集，量化噪声泄漏对固定噪声谱估计器的影响。

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
N = 2000
N_FFT, HOP = 128, 64
N_TRAIN, N_TEST = 12, 6
SEED_TRAIN, SEED_LEAK, SEED_OOD = 1000, 1000, 2000

# ---- 计算与作图 ----
def make_noise(seed):
    r = random.Random(seed)
    f1 = 250.0 + 60.0 * (seed % 11)
    f2 = 900.0 + 90.0 * (seed % 7)
    a, b = tone(f1, N, amp=0.055), tone(f2, N, amp=0.045)
    return [a[i] + b[i] + 0.008 * r.gauss(0, 1) for i in range(N)]
def make_pair(seed):
    s = synthetic_speech(random.Random(seed + 50000), N)
    v = make_noise(seed)
    return s, v, [s[i] + v[i] for i in range(N)]

train = [make_pair(SEED_TRAIN + i) for i in range(N_TRAIN)]
leak = [make_pair(SEED_LEAK) for _ in range(N_TEST)]
ood = [make_pair(SEED_OOD + i) for i in range(N_TEST)]
acc = [0.0] * N_FFT
count = 0
for _s, v, _y in train:
    for re, im in stft(v, N_FFT, HOP):
        for k in range(N_FFT):
            acc[k] += math.hypot(re[k], im[k])
        count += 1
nmag = [a / count for a in acc]

def enhance(noisy):
    frames = stft(noisy, N_FFT, HOP)
    for re, im in frames:
        for k in range(N_FFT):
            g = max(0.20, 1.0 - 1.3 * nmag[k] / (math.hypot(re[k], im[k]) + 1e-9))
            re[k] *= g
            im[k] *= g
    return istft(frames, N_FFT, HOP, N)
def score(items):
    vals = []
    for s, _v, y in items:
        vals.append(seg_snr_db(s, scale_align(enhance(y), s)))
    return sum(vals) / len(vals)
s_train, s_leak, s_ood = score(train), score(leak), score(ood)
c = Chart(FIG / "20-split.svg", "固定噪声谱估计器在三个集合上的分段 SNR",
          xlabel="集合", ylabel="dB", xticks=[(0, "训练"), (1, "泄漏测试"), (2, "独立测试")])
c.bars(range(3), [s_train, s_leak, s_ood], BLUE, label="分段 SNR (dB)")
print("划分图:", c.save())
g = Chart(FIG / "20-noise-spectrum.svg", "训练集平均噪声幅度谱（谱峰可被记住）",
          xlabel="频率箱 k", ylabel="平均幅度")
g.line(range(N_FFT // 2), nmag[:N_FFT // 2], RED, label="平均噪声谱")
print("噪声谱图:", g.save())
write_wav(AUDIO / "20-train.wav", normalize_peak(train[0][2]))
write_wav(AUDIO / "20-ood.wav", normalize_peak(ood[0][2]))
print("训练=%d 条 泄漏测试=%d 条 独立测试=%d 条 | 每条 %d 样本" %
      (len(train), len(leak), len(ood), N))
print("segSNR 训练=%.2f 泄漏测试=%.2f 独立测试=%.2f | 泄漏虚高=%.2f dB" %
      (s_train, s_leak, s_ood, s_leak - s_ood))
print("SAMPLE_RATE=%d N_FFT=%d HOP=%d | 划分单位: seed 而非帧" % (SAMPLE_RATE, N_FFT, HOP))
