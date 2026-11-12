#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成带静音段的语音与非平稳噪声，实现最小值控制的递推平均，打印检测率、谱误差与 segSNR。

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
N, NF, HOP = 8000, 256, 128
ALPHA_S, ALPHA_N = 0.50, 0.90    # 时间平滑 / 噪声更新平滑
WIN = 12                         # 最小值跟踪窗（帧）
RATIO_TH = 2.2                   # S/S_min 更新闸门
VAD_TH_DB = 3.0                  # 帧级后验 SNR 阈值
SUB_FACTOR, FLOOR = 1.0, 0.15    # 谱减过减因子与增益下限

# ---- 计算与作图 ----
rng = random.Random(7)
base = synthetic_speech(rng, N)
gate = [1.0 if (0.18 * N <= i < 0.45 * N or 0.60 * N <= i < 0.90 * N) else 0.0
        for i in range(N)]
speech = [base[i] * gate[i] for i in range(N)]
noise = [rng.gauss(0.0, 0.012 if i < N // 2 else 0.045) for i in range(N)]
noisy = [speech[i] + noise[i] for i in range(N)]

frames = stft(noisy, NF, HOP)
T = len(frames)
P = [[re[k] ** 2 + im[k] ** 2 for k in range(NF)] for re, im in frames]
nframes = stft(noise, NF, HOP)
Ntrue = [statistics.fmean(nr[k] ** 2 + ni[k] ** 2 for nr, ni in nframes) for k in range(NF)]
Nfix = [statistics.fmean(P[t][k] for t in range(min(4, T))) for k in range(NF)]

S = P[0][:]
Nhat = S[:]
hist, track, snr_t = [], [], []
for t in range(T):
    sm = [0.25 * P[t][(k - 1) % NF] + 0.5 * P[t][k] + 0.25 * P[t][(k + 1) % NF]
          for k in range(NF)]
    S = [ALPHA_S * S[k] + (1 - ALPHA_S) * sm[k] for k in range(NF)]
    hist.append(S[:])
    if len(hist) > WIN:
        hist.pop(0)
    Smin = [min(h[k] for h in hist) for k in range(NF)]
    for k in range(NF):
        if S[k] / (Smin[k] + 1e-12) < RATIO_TH:
            Nhat[k] = ALPHA_N * Nhat[k] + (1 - ALPHA_N) * P[t][k]
    track.append(sum(Nhat))
    snr_t.append(sum(P[t]) / (sum(Nhat) + 1e-9))

def spec_err(est, ref):
    return statistics.fmean(abs(10 * math.log10((e + 1e-12) / (r + 1e-12)))
                            for e, r in zip(est, ref))

vad = [1 if 10 * math.log10(s + 1e-12) > VAD_TH_DB else 0 for s in snr_t]
truth = [1 if gate[min(t * HOP, N - 1)] > 0 else 0 for t in range(T)]
tp = sum(1 for a, b in zip(vad, truth) if a and b)
fp = sum(1 for a, b in zip(vad, truth) if a and not b)
fn = sum(1 for a, b in zip(vad, truth) if not a and b)
tn = sum(1 for a, b in zip(vad, truth) if not a and not b)

def suppress(noise_est):
    out = []
    for re, im in frames:
        rr, ii = re[:], im[:]
        for k in range(NF):
            mag = math.hypot(re[k], im[k])
            g = max(FLOOR, 1.0 - SUB_FACTOR * math.sqrt(noise_est[k]) / (mag + 1e-9))
            rr[k] *= g
            ii[k] *= g
        out.append((rr, ii))
    return istft(out, NF, HOP, N)

out_fix, out_mcra = suppress(Nfix), suppress(Nhat)
ntrack = [sum(nr[k] ** 2 + ni[k] ** 2 for k in range(NF)) for nr, ni in nframes]

c = Chart(FIG / "08-noise-track.svg", "非平稳噪声功率：真实 / 固定估计 / MCRA 跟踪",
          xlabel="帧 t", ylabel="全带功率（线性求和）")
c.line(range(T), ntrack, "#9aa6b2", label="真实噪声帧功率", opacity=0.85)
c.line(range(T), track, GREEN, label="MCRA 跟踪 λ_n")
c.line(range(T), [sum(Nfix)] * T, RED, label="固定估计（前 4 帧）")
print("跟踪图:", c.save())
d = Chart(FIG / "08-vad.svg", "逐帧后验 SNR 与 VAD 判决", xlabel="帧 t", ylabel="dB / 判决")
d.line(range(T), [10 * math.log10(s + 1e-12) for s in snr_t], BLUE, label="帧级 SNR (dB)")
d.hline(VAD_TH_DB, RED, label="VAD 阈值")
d.bars(range(T), vad, AMBER, label="VAD=1 判语音", opacity=0.35)
print("VAD图:", d.save())
write_wav(AUDIO / "08-noisy.wav", normalize_peak(noisy))
write_wav(AUDIO / "08-fixed.wav", normalize_peak(out_fix))
write_wav(AUDIO / "08-mcra.wav", normalize_peak(out_mcra))
print("采样率=%d Hz STFT=%d/%d 帧数=%d 最小值窗=%d帧 噪声amp 0.012→0.045" %
      (SAMPLE_RATE, NF, HOP, T, WIN))
print("噪声谱平均绝对误差: 固定=%.2f dB MCRA=%.2f dB" %
      (spec_err(Nfix, Ntrue), spec_err(Nhat, Ntrue)))
print("VAD TP=%d FP=%d FN=%d TN=%d | 检测率=%.3f 虚警率=%.3f 帧准确率=%.3f" %
      (tp, fp, fn, tn, tp / max(tp + fn, 1), fp / max(fp + tn, 1), (tp + tn) / T))
print("segSNR 带噪=%.2f 固定谱减=%.2f MCRA谱减=%.2f dB" %
      (seg_snr_db(speech, noisy), seg_snr_db(speech, out_fix), seg_snr_db(speech, out_mcra)))
