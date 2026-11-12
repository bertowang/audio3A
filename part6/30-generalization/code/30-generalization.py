#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用纯标准库合成四组数据，扫描可解释阈值掩码的超参，分别打印泄漏虚高与 OOD 落差。

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
N = 4096                    # 每条样本 0.256 s @ 16 kHz
N_FFT, HOP = 256, 128
THETAS = (0.20, 0.35, 0.50, 0.65, 0.80, 0.95, 1.20, 1.50, 2.00)
NOISE_AMP = 0.035           # 训练与同分布测试的高斯噪声幅度
FLOOR = 0.12                # 掩码增益下限

# ---- 计算与作图 ----
rng = random.Random(7)

def noise_of(kind, n):
    if kind == "white":
        return white_noise(rng, n, NOISE_AMP)
    hum = [0.75 * NOISE_AMP * math.sin(2 * math.pi * 93 * i / SAMPLE_RATE)
           + 0.45 * NOISE_AMP * math.sin(2 * math.pi * 187 * i / SAMPLE_RATE)
           for i in range(n)]
    for start in range(400, n, 900):
        for i in range(start, min(start + 60, n)):
            hum[i] += 2.4 * NOISE_AMP * (1.0 if (i - start) % 2 == 0 else -1.0)
    return [hum[i] + 0.15 * rng.gauss(0, NOISE_AMP) for i in range(n)]


def mix(kind):
    clean = synthetic_speech(rng, N)
    nz = noise_of(kind, N)
    return clean, [clean[i] + nz[i] for i in range(N)], nz


train_clean, train_noisy, train_nz = mix("white")
val_clean, val_noisy, val_nz = mix("white")
id_clean, id_noisy, id_nz = mix("white")
ood_clean, ood_noisy, ood_nz = mix("ood")

# 噪声谱只从训练集估计：这是模型带进测试集的先验
nz_frames = stft(train_nz, N_FFT, HOP)
ns = [sum(math.hypot(re[k], im[k]) for re, im in nz_frames) / len(nz_frames)
      for k in range(N_FFT)]


def frames_of(noisy):
    return stft(noisy, N_FFT, HOP)


def apply_mask(frame_list, theta):
    out_frames = []
    for re, im in frame_list:
        rr, ii = list(re), list(im)
        for k in range(N_FFT):
            mag = math.hypot(rr[k], ii[k])
            g = max(FLOOR, 1.0 - theta * ns[k] / (mag + 1e-9))
            rr[k] *= g
            ii[k] *= g
        out_frames.append((rr, ii))
    return istft(out_frames, N_FFT, HOP, N)


def score(clean, est):
    return si_sdr_db(est, clean)


val_frames = frames_of(val_noisy)
id_frames = frames_of(id_noisy)
ood_frames = frames_of(ood_noisy)
val_curve = [score(val_clean, apply_mask(val_frames, t)) for t in THETAS]
id_curve = [score(id_clean, apply_mask(id_frames, t)) for t in THETAS]
best_val_i = max(range(len(THETAS)), key=lambda i: val_curve[i])
theta_star = THETAS[best_val_i]
leak_i = max(range(len(THETAS)), key=lambda i: id_curve[i])
leak_theta = THETAS[leak_i]
correct_id = id_curve[best_val_i]
leak_id = id_curve[leak_i]
correct_ood = score(ood_clean, apply_mask(ood_frames, theta_star))
baseline_id = score(id_clean, id_noisy)
baseline_ood = score(ood_clean, ood_noisy)
inflate = leak_id - correct_id
gap_ood = correct_id - correct_ood

c = Chart(FIG / "30-leak.svg", "阈值 theta 在验证集与测试集上的扫描曲线",
          xlabel="theta", ylabel="SI-SDR (dB)",
          xticks=[(i, "%.2f" % t) for i, t in enumerate(THETAS)])
c.line(range(len(THETAS)), val_curve, BLUE, label="验证集（允许调参）")
c.line(range(len(THETAS)), id_curve, RED, label="测试集（不可调参）")
c.vline(best_val_i, GREEN, label="验证集最优点")
print("泄漏图:", c.save())
b = Chart(FIG / "30-ood.svg", "泄漏虚高与分布外落差", xlabel="评测口径", ylabel="SI-SDR (dB)",
          xticks=[(0, "ID基线"), (1, "ID正确"), (2, "ID泄漏"), (3, "OOD基线"), (4, "OOD正确")])
b.bars(range(5), [baseline_id, correct_id, leak_id, baseline_ood, correct_ood], AMBER,
       label="实测分数")
b.hline(0.0, "#9aa6b2")
print("分布外图:", b.save())

write_wav(AUDIO / "30-clean.wav", normalize_peak(id_clean))
write_wav(AUDIO / "30-id-noisy.wav", normalize_peak(id_noisy))
write_wav(AUDIO / "30-id-masked.wav", normalize_peak(apply_mask(id_frames, theta_star)))
write_wav(AUDIO / "30-ood-noisy.wav", normalize_peak(ood_noisy))
write_wav(AUDIO / "30-ood-masked.wav", normalize_peak(apply_mask(ood_frames, theta_star)))
print("WAV: %d 帧 / %d Hz / %.2f s / %d 字节" % wav_info(AUDIO / "30-clean.wav"))
print("验证集最优 theta=%.2f | 用测试集挑到 theta=%.2f" % (theta_star, leak_theta))
print("同分布：基线=%.2f dB 正确口径=%.2f dB 测试集挑参=%.2f dB | 虚高=%.2f dB" %
      (baseline_id, correct_id, leak_id, inflate))
print("分布外：基线=%.2f dB 同一 theta=%.2f dB" % (baseline_ood, correct_ood))
print("泄漏虚高=%.2f dB | 分布外落差=%.2f dB | 采样率=%d Hz | 扫描候选数=%d" %
      (inflate, gap_ood, SAMPLE_RATE, len(THETAS)))
