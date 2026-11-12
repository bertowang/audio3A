#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成 4 通道阵列信号，按角度扫描固定波束，测量干扰抑制并输出可试听样本。

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
MICS = 4
SPACING = 0.10             # 麦克风间距（米）
SPEED = 340.0              # 声速 m/s
INTERFERER_ANGLE = 65      # 干扰源角度（度）
ANGLES = tuple(range(-80, 81, 20))

# ---- 计算与作图 ----
rng = random.Random(7)
target = chirp(150, 3000, N, amp=0.35)
interf = tone(730, N, amp=0.30)
def shift(x, d):
    return [x[i - d] if 0 <= i - d < N else 0.0 for i in range(N)]
def tdoa(angle, m):
    return int(round(m * SPACING * math.sin(math.radians(angle)) / SPEED * SAMPLE_RATE))
mics = []
for m in range(MICS):
    s = shift(target, tdoa(0, m))
    u = shift(interf, tdoa(INTERFERER_ANGLE, m))
    v = white_noise(rng, N, 0.010)
    mics.append([s[i] + 0.9 * u[i] + v[i] for i in range(N)])
def beam(theta):
    parts = [shift(mics[m], -tdoa(theta, m)) for m in range(MICS)]
    return [sum(p[i] for p in parts) / MICS for i in range(N)]
scores = [seg_snr_db(target, scale_align(beam(a), target)) for a in ANGLES]
best = ANGLES[scores.index(max(scores))]
out = beam(best)
c = Chart(FIG / "15-directivity.svg", "delay-and-sum 指向性：各扫描角的分段 SNR",
          xlabel="扫描角（度）", ylabel="dB",
          xticks=[(i, "%d" % a) for i, a in enumerate(ANGLES)])
c.line(range(len(ANGLES)), scores, BLUE, label="分段 SNR (dB)")
c.vline(ANGLES.index(best), RED, label="峰值角")
print("指向图:", c.save())
w = Chart(FIG / "15-waveform.svg", "单通道与波束输出波形（前 1200 样本）",
          xlabel="样本", ylabel="幅度")
w.line(range(1200), mics[0][:1200], "#9aa6b2", label="单通道")
w.line(range(1200), out[:1200], GREEN, label="波束输出")
print("波形图:", w.save())
write_wav(AUDIO / "15-single.wav", normalize_peak(mics[0]))
write_wav(AUDIO / "15-beam.wav", normalize_peak(out))
print("扫描角 SNR: " + " ".join("%d度=%.1f" % (a, s) for a, s in zip(ANGLES, scores)))
print("最佳角度=%d度 | 单通道 segSNR=%.2f -> 波束=%.2f dB | SAMPLE_RATE=%d MICS=%d" %
      (best, seg_snr_db(target, scale_align(mics[0], target)), max(scores), SAMPLE_RATE, MICS))
