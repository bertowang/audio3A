#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 06～11 章：频域自适应滤波、双讲/时延、噪声估计与 AEC 三大结构。"""
from __future__ import annotations

from book_schema import C, eq, table
from chapter_kit import mk_demo, shell, p, ul, ol, note, warn, sec
from book_resources import REPOS

CH = [

# ==================================================================== 06
C("06", "p1", "part1/06-fdaf", "频域自适应滤波：FDAF、分块 MDF 与收敛",
  "把 NLMS 的逐点乘加换成 FFT 后的逐 bin 标量乘，长回声路径才跑得动。",
  hours="3 学时",
  goals=["能写出分块频域卷积的 overlap-save 数据帧结构与补零条件。",
         "能推导频域 LMS 的逐 bin 归一化更新式，并说明它为何对有色激励更快。",
         "能解释 MDF 如何把长滤波器拆成若干短块以压低算法延迟。",
         "能运行实验，用权重误差曲线与 ERLE 核对频域辨识的收敛。"],
  points=["overlap-save 分块", "循环卷积与补零", "频域 LMS (FLMS)", "逐 bin 功率归一化",
          "MDF 多延迟分块", "分块数与算法延迟", "有色激励与特征值分散", "频域权重约束"],
  sections=[
      ("6.1", "为什么时域 NLMS 在长路径上不够用", sec(
          eq("时域 NLMS: w[n+1] = w[n] + μ·e[n]·x[n] / (‖x[n]‖² + δ)　，每样本 O(L)"),
          p("16 kHz 下覆盖 128 ms 混响需 L≈2048 抽头。时域每输出样本做 2048 次乘加，"
            "约 33 M 次/秒；分块频域把长度 L 的卷积变成 N 点 FFT 后的逐点乘，每样本代价降到 O(log N)。"
            "<strong>{{ch:04}} 讲的是固定系数的卷积，{{ch:05}} 让系数在线学习，本章把两者合并。</strong>"),
          table(["实现", "每样本代价", "L=2048 量级", "算法延迟"], [
              ["时域 NLMS", "O(L)", "约 2048 乘加", "1 样本"],
              ["单块 FLMS", "O(log N)", "约 11 复数乘", "N 样本（整块）"],
              ["分块 MDF", "O(P·log N)", "P 个短块并行", "B 样本（仅一块）"],
          ], ["22%", "22%", "28%", "28%"]),
          note("两个不同的『分块』", "overlap-save 的『块』是输入数据流的时间分块，决定算法延迟；"
               "MDF 的『分块』是把长 h 切成 P 段、每段单独做频域自适应，决定单块 FFT 长度。"
               "两者叠加就是 WebRTC AEC3 主滤波器的结构。"))),
      ("6.2", "频域更新式：每个 bin 是一个独立的标量回归", sec(
          eq("Xₚ[k] = FFT{histₚ ⊕ xₚ}　，Yₚ[k] = Wₚ[k]·Xₚ[k]　，eₚ = 取 IFFT{Yₚ} 的有效尾部"),
          eq("Wₚ[k] ← Wₚ[k] + μ·Eₚ[k]·Xₚ*[k] / (Pₚ[k] + δ)　，Pₚ[k] = α·Pₚ[k] + (1−α)·|Xₚ[k]|²"),
          p("关键在分母 <code>Pₚ[k]</code>：<strong>每个频率箱按自己的能量归一化</strong>。语音是强有色信号，"
            "低频 bin 功率可能比高频大几十 dB；时域 NLMS 只有一个全局 ‖x‖²，等效学习率被最大特征值卡住，"
            "而频域按 bin 白化后各 bin 可同时快速收敛。这与 Adam / RMSProp 按参数尺度自适应学习率同源。"),
          warn("频域更新必须做时域约束", "E·X* 是圆周卷积梯度，IFFT 后尾部会出现环绕抽头。每块更新后要把 W 变回时域、"
               "只保留前 L 个系数、尾部清零再 FFT 回去，否则滤波器长度被悄悄放大，产生时域混叠。"))),
      ("6.3", "实验里怎么判断『收敛了』", sec(
          ul(["<strong>权重误差范数</strong>：10log₁₀(‖W−H‖²/‖H‖²)，比只看 e² 更能说明辨识的是真实路径。",
              "<strong>收敛迭代数</strong>：曲线首次跌破 −15 dB 的分块序号，可随 μ 与激励类型复算。",
              "<strong>ERLE</strong>：把收敛后的 W 变回时域 ŵ，用 fft_convolve 重算回声并相减，核对能量比。"]),
          p("本实验用<strong>逐 bin 最小二乘递推</strong>代替带 μ 的梯度步：Sxxₚ[k] 累加 |Xₚ[k]|²、"
            "Sxyₚ[k] 累加 Dₚ[k]·Xₚ*[k]，则 Wₚ[k] = Sxyₚ[k]/(Sxxₚ[k]+δ)。它没有步长发散风险，"
            "正好把『逐 bin 归一化』单独放大，便于与时域 NLMS 对照。"),
          eq("W[k] = Sxy[k] / (Sxx[k] + δ)　，Sxx[k] = Σₚ|Xₚ[k]|²　，Sxy[k] = Σₚ Dₚ[k]·Xₚ*[k]"))),
  ],
  demos=[mk_demo(
      "code/06-fdaf.py", "实验 6-1 · 分块频域辨识 vs 时域 NLMS：收敛、bin 功率与 ERLE",
      "在有色激励下对照频域逐 bin 最小二乘辨识与时域 NLMS 的收敛，输出权重误差、收敛块号与 ERLE。",
      """N = 4096                  # 约 0.25 s @ 16 kHz
NF, L, B = 128, 64, 64     # FFT 长度 / 滤波器抽头 / 每块新样本，满足 NF ≥ B+L−1
NB = N // B                # 分块数
MU = 0.45                  # 时域对照 NLMS 步长
DELTA = 0.02               # 频域分母正则项（过大会拖慢收敛）
OBS_NOISE = 0.02           # 频域观测扰动（模拟近端/量化噪声）""",
      """rng = random.Random(7)
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
      (erle_db(echo, residual), rms(residual) / (rms(echo) + 1e-9)))""",
      figs=[("fig/06-convergence.svg", "频域与时域自适应滤波的权重误差收敛对比"),
            ("fig/06-bins.svg", "有色激励的逐 bin 功率分布")],
      audio=[("audio/06-far.wav", "远端参考信号（有色合成语音）"),
             ("audio/06-echo.wav", "经房间路径卷积后的回声"),
             ("audio/06-residual.wav", "收敛后的频域滤波器抵消残差")],
      steps="先对照两条收敛曲线与 −15 dB 线；再听 06-echo.wav 与 06-residual.wav；把 MU 调小看时域曲线如何变慢。",
      expect="两条分支使用同样的观测噪声；频域逐 bin 归一化在有色激励下第 2 块就跌破 −15 dB，"
             "时域 NLMS 要到第 8 块，末块权重误差相差约 28 dB。ERLE 为正（本例约 58 dB）且随权重误差下降而升高。",
      tweak="把 DELTA 调大两个数量级，两个算法的收敛都会变慢；把 far 换成纯 white_noise，时域 NLMS 的差距会缩小。")],
  commands=[shell("本机自查 FFT/滤波工具与官方入口",
                  "python3 -c 'import sys; print(sys.version)' && ffmpeg -hide_banner -filters | grep -E 'afftdn|aresample'",
                  "命令只做本机能力自查；ffmpeg 滤镜是否可用、参数名与引入版本以 https://ffmpeg.org/ffmpeg-filters.html 与本机 ffmpeg -filters 输出为准，本书不假定任何特定版本。"),
            shell("查 WebRTC AEC3 分块频域源码入口",
                  "git ls-remote https://webrtc.googlesource.com/src HEAD",
                  "只检查仓库可达性；AEC3 分块 MDF 结构以 https://webrtc.googlesource.com/src/+/refs/heads/main/modules/audio_processing/aec3/ 官方源码为准，本书不假定任何特定版本。")],
  highlights=[("ccrma", "分块频域滤波与 overlap-save 的免费教材"),
              ("scipy-signal", "fftconvolve / stft 的工业级对照实现"),
              ("webrtc-aec3", "分块频域自适应滤波的现代工业结构"),
              ("numpy", "把逐 bin 更新向量化后的迁移目标")],
  repos=[REPOS[0], REPOS[1], REPOS[9]],
  analogy="时域 NLMS 是对长度 L 的数组做逐元素梯度下降；FDAF 先 FFT 到近似对角的坐标系，"
          "再对每个坐标单独设学习率——等价于给优化器加了一层预条件器。"
          "<strong>块长 B 就是流式系统的 batch size，也是算法延迟的下界。</strong>",
  bridge="{{ch:04}} 给出固定系数的分块卷积，{{ch:05}} 给出时域 NLMS，本章把两者合并；"
         "{{ch:07}} 处理双讲与时延漂移，{{ch:09}} 起把它装进完整 AEC。",
  pitfalls=["FFT 长度不满足 N ≥ B+L−1，圆周卷积绕回造成时域混叠。",
            "频域更新后不做时域抽头约束，滤波器长度悄悄增长。",
            "逐 bin 分母用全局功率而非 P[k]，白化优势消失。",
            "把整块 FFT 的 N 样本延迟当成 1 样本，实时预算算错。"],
  exercises=["推导 N ≥ B+L−1，并说明 MDF 把 L 切成 P 段后单块 FFT 长度如何变化。",
             "解释为什么有色激励下时域 NLMS 收敛慢，而逐 bin 归一化能加速。",
             "把块长 B 减半，估算 FFT 次数、算法延迟与收敛块数的变化。"],
  further=["{{ch:10}} 用 NLMS 实现完整可验证的 AEC；{{ch:11}} AEC3 的两级残余抑制结构。"]),

# ==================================================================== 07
C("07", "p1", "part1/07-doubletalk", "双讲检测、时延漂移与路径突变",
  "自适应滤波器最怕的三件事：标签被污染、延迟在走、真值突然换了。",
  hours="3 学时",
  goals=["能说明双讲为何让 NLMS 的梯度混入不相关近端语音。",
         "能用归一化互相关构造双讲检测量并给出帧级检测率与虚警率。",
         "能解释时钟漂移与路径突变对已收敛滤波器的不同破坏方式。",
         "能运行实验，对照冻结与不冻结更新时的权重误差与可听残差。"],
  points=["双讲与近端语音", "Geigel / NCC 检测量", "检测阈值与驻留时间", "系数冻结与阴影滤波器",
          "时延漂移 ppm", "互相关峰值跟踪", "路径突变与重收敛", "检测率与虚警率"],
  sections=[
      ("7.1", "双讲不是噪声变大，是标签被污染", sec(
          eq("e[n] = d[n] + h*x[n] + v[n] − ŷ[n]　；单讲时 d[n]≈0，双讲时 d[n] 与 x[n] 不相关"),
          p("NLMS 把 <code>e[n]</code> 当成『回声没抵消干净的部分』去修正 w。双讲时 <code>e[n]</code> 里主要是近端语音，"
            "它与参考 <code>x[n]</code> 统计独立，于是梯度 <code>e·x</code> 变成零均值大方差噪声：系数被推离 h，"
            "双讲结束后 ERLE 塌陷，需要几十到几百毫秒重收敛。"),
          table(["场景", "误差 e[n] 主要成分", "与 x 相关吗", "该不该更新 w"], [
              ["远端单讲", "h−ŵ 造成的残余回声", "强相关", "更新（正是要学的时候）"],
              ["近端单讲", "近端语音 + 噪声", "不相关", "冻结"],
              ["双讲", "残余回声 + 近端语音", "混合", "冻结或大幅降 μ"],
              ["双方静音", "量化 / 环境噪声", "不相关", "冻结（输入能量不足）"],
          ], ["18%", "30%", "22%", "30%"]),
          note("工业做法", "WebRTC AEC3 用『主滤波器 + 阴影滤波器』：阴影滤波器一直自由更新，"
               "只有明显优于主滤波器时才替换，避免一次误判毁掉已收敛的 h。本章实验用理想检测上界演示冻结的作用。"))),
      ("7.2", "一个可用的检测量：归一化互相关", sec(
          eq("ρ = Σ ŷ[i]·y[i] / √(Σ ŷ[i]² · Σ y[i]²)　，逐帧计算；ρ < τ 判双讲"),
          p("<code>ŷ</code> 是线性滤波器预测的回声。单讲时 <code>y ≈ ŷ</code>，ρ 接近 1；双讲时 <code>y = ŷ + d</code>，"
            "分母多出近端能量而分子几乎不变，ρ 明显下降。阈值 τ 决定检测率与虚警率的折中；工程上还要加"
            "<strong>驻留时间（hangover）</strong>，避免音节间隙把一次双讲切成几十段。"),
          eq("若近端与预测回声功率比为 q，则 ρ ≈ 1 / √(1+q)　（可手算校核阈值）"),
          p("本实验 q≈1.5 时 ρ≈0.63，取 τ=0.80 即可把双讲帧与单讲帧干净分开；把近端调小到 q≈0.2，"
            "ρ≈0.91 就会漏检——<strong>阈值必须跟着电平标定</strong>。"))),
      ("7.3", "另外两种『路径变了』", sec(
          ul(["<strong>时延漂移</strong>：播放与采集用不同晶振，ppm 级采样率偏差让缓冲对齐缓慢滑移；"
              "表现为互相关峰值逐帧平移，而不是 h 的形状改变。对策是周期性重估延迟 + 重采样 / 缓冲对齐。",
              "<strong>路径突变</strong>：有人挪动笔记本、手掌挡住麦克风，h 在几十毫秒内整体改变；"
              "表现为 ‖w−h‖ 突然跳大、ERLE 断崖。对策是突变检测后提高 μ 或重置阴影滤波器。",
              "<strong>非线性失真</strong>：扬声器削波让回声不再是 x 的线性卷积，"
              "线性滤波器无解，只能交给 {{ch:11}} 的残余抑制。"]))),
  ],
  demos=[mk_demo(
      "code/07-doubletalk.py", "实验 7-1 · NCC 双讲检测、冻结更新与互相关时延跟踪",
      "逐帧计算归一化互相关做双讲判决，对照冻结/不冻结的权重误差，并用互相关峰值估计时延漂移。",
      """N, L, FRAME = 4096, 64, 256
DT0, DT1 = 1536, 2560       # 双讲区间（样本）
THRESH = 0.90               # NCC 双讲阈值（实测单讲 ρ≈1、双讲 ρ≈0.82~0.87）
NEAR_GAIN = 1.8             # 近端语音电平
MU = 0.50                   # NLMS 步长
DRIFT = 8                   # 模拟时延漂移（样本）""",
      """rng = random.Random(7)
far = synthetic_speech(rng, N)
near_raw = synthetic_speech(rng, N)
near = [NEAR_GAIN * near_raw[i] if DT0 <= i < DT1 else 0.0 for i in range(N)]
h = rir(rng, L, decay=0.004, direct_delay=12)
echo = fft_convolve(far, h)[:N]
noise = white_noise(rng, N, 0.003)
mic = [echo[i] + near[i] + noise[i] for i in range(N)]
echo_hat = fft_convolve(far, h)[:N]

NFR = N // FRAME
rho, flags, truth = [], [], []
for f in range(NFR):
    s = f * FRAME
    num = sum(echo_hat[s + i] * mic[s + i] for i in range(FRAME))
    da = math.sqrt(sum(echo_hat[s + i] ** 2 for i in range(FRAME)))
    db = math.sqrt(sum(mic[s + i] ** 2 for i in range(FRAME)))
    r = num / (da * db + 1e-12)
    rho.append(r)
    flags.append(r < THRESH)
    truth.append(DT0 <= s < DT1)
tp = sum(1 for a, b in zip(flags, truth) if a and b)
fp = sum(1 for a, b in zip(flags, truth) if a and not b)
fn = sum(1 for a, b in zip(flags, truth) if not a and b)
tn = sum(1 for a, b in zip(flags, truth) if not a and not b)

w_frozen, w_free = h[:], h[:]
out_frozen, out_free = [0.0] * N, [0.0] * N
curve_frozen, curve_free = [], []
den_h = sum(v * v for v in h)
for n in range(L, N):
    xv = [far[n - i] for i in range(L)]
    f = min(n // FRAME, NFR - 1)
    is_dt = flags[f]
    y_f = sum(w_frozen[i] * xv[i] for i in range(L))
    y_u = sum(w_free[i] * xv[i] for i in range(L))
    e_f, e_u = mic[n] - y_f, mic[n] - y_u
    out_frozen[n], out_free[n] = e_f, e_u
    p = sum(v * v for v in xv) + 1e-3
    for i in range(L):
        w_free[i] += MU * e_u * xv[i] / p
        if not is_dt:
            w_frozen[i] += MU * e_f * xv[i] / p
    if n % FRAME == 0:
        curve_frozen.append(10 * math.log10(
            sum((w_frozen[i] - h[i]) ** 2 for i in range(L)) / (den_h + 1e-12) + 1e-12))
        curve_free.append(10 * math.log10(
            sum((w_free[i] - h[i]) ** 2 for i in range(L)) / (den_h + 1e-12) + 1e-12))

probe = white_noise(rng, 2048, 0.35)
h_a = rir(rng, 64, decay=0.004, direct_delay=12)
h_b = rir(rng, 64, decay=0.004, direct_delay=12 + DRIFT)
ya, yb = fft_convolve(probe, h_a)[:2048], fft_convolve(probe, h_b)[:2048]

def peak_lag(y):
    best, bp = -1.0, 0
    for lag in range(60):
        num = sum(probe[i] * y[i + lag] for i in range(1024))
        da = math.sqrt(sum(probe[i] ** 2 for i in range(1024)))
        db = math.sqrt(sum(y[i + lag] ** 2 for i in range(1024)))
        r = num / (da * db + 1e-12)
        if r > best:
            best, bp = r, lag
    return bp, best

la, pa = peak_lag(ya)
lb, pb = peak_lag(yb)
jump = sum((h_b[i] - h_a[i]) ** 2 for i in range(64)) / (sum(v * v for v in h_a) + 1e-12)

c = Chart(FIG / "07-ncc.svg", "逐帧归一化互相关与双讲判决", xlabel="帧 t", ylabel="ρ")
c.line(range(NFR), rho, BLUE, label="NCC ρ")
c.hline(THRESH, RED, label="判决阈值 τ")
c.vline(DT0 // FRAME, GREEN, label="双讲起")
c.vline(DT1 // FRAME, GREEN, label="双讲止")
print("检测图:", c.save())
d = Chart(FIG / "07-weight-error.svg", "双讲期间冻结 vs 不冻结的权重误差",
          xlabel="帧 t", ylabel="‖w−h‖²/‖h‖² (dB)")
d.line(range(len(curve_frozen)), curve_frozen, GREEN, label="检测到双讲即冻结")
d.line(range(len(curve_free)), curve_free, RED, label="全程照常更新")
print("权重图:", d.save())
write_wav(AUDIO / "07-mic.wav", normalize_peak(mic))
write_wav(AUDIO / "07-frozen.wav", normalize_peak(out_frozen))
write_wav(AUDIO / "07-unfrozen.wav", normalize_peak(out_free))
print("采样率=%d Hz 帧数=%d 帧长=%d 阈值=%.2f 双讲区间=[%d,%d)" %
      (SAMPLE_RATE, NFR, FRAME, THRESH, DT0, DT1))
print("双讲检测 TP=%d FP=%d FN=%d TN=%d | 检测率=%.3f 虚警率=%.3f 帧准确率=%.3f" %
      (tp, fp, fn, tn, tp / max(tp + fn, 1), fp / max(fp + tn, 1), (tp + tn) / NFR))
print("互相关峰值 lag 原=%d 漂移后=%d 估计漂移=%d 真值=%d 峰值ρ=%.3f" % (la, lb, lb - la, DRIFT, pb))
print("末帧权重误差 冻结=%.2f dB 不冻结=%.2f dB | 路径突变 ‖h_b−h_a‖²/‖h_a‖²=%.3f" %
      (curve_frozen[-1], curve_free[-1], jump))""",
      figs=[("fig/07-ncc.svg", "逐帧 NCC 曲线、阈值与双讲真值区间"),
            ("fig/07-weight-error.svg", "冻结与不冻结更新的权重误差对比")],
      audio=[("audio/07-mic.wav", "含双讲段的麦克风信号"),
             ("audio/07-frozen.wav", "双讲期间冻结系数后的残差"),
             ("audio/07-unfrozen.wav", "双讲期间照常更新的残差")],
      steps="先看 ρ 曲线在双讲区间是否跌破阈值；再对照两条权重误差曲线与两个残差 WAV；把 NEAR_GAIN 调到 0.4 观察漏检。",
      expect="单讲帧 ρ 接近 1、双讲帧降到 0.82～0.87，阈值 0.90 可把 4 个双讲帧全部检出且零虚警；"
             "冻结曲线在双讲后回到约 −24 dB，不冻结曲线停在约 −15 dB。检测率与虚警率可由 TP/FP/FN/TN 逐项复算。",
      tweak="把 THRESH 调到 0.95 会提高检测率但增大虚警；把 DRIFT 改成 16，互相关估计漂移应同步翻倍。")],
  commands=[shell("本机自查回声/双讲测试素材与 G.168 官方入口",
                  "ffmpeg -hide_banner -filters | grep -E 'aecho|silencedetect|astats'",
                  "只做本机滤镜能力自查；双讲与 ERLE 的测试信号口径以 ITU-T G.168 https://www.itu.int/rec/T-REC-G.168/en 为准，滤镜可用性以 https://ffmpeg.org/ffmpeg-filters.html 与本机输出为准，本书不假定任何特定版本。")],
  highlights=[("itu-g168", "回声消除器测试信号与双讲测试规范"),
              ("aec-challenge", "真实双讲与非线性失真录音，验证检测器必备"),
              ("webrtc-aec3", "主/阴影滤波器与双讲逻辑的工业实现"),
              ("wiki-aec", "双讲问题与自适应滤波概述")],
  repos=[REPOS[4], REPOS[0], REPOS[1]],
  analogy="双讲检测是给在线训练加一个 <code>if label_is_clean:</code> 守卫；时延漂移是数据管道的两个时钟域没做 CDC；"
          "路径突变则是训练集分布突然换了。<strong>三者都不是『调小学习率』能解决的。</strong>",
  bridge="{{ch:06}} 让滤波器在频域收敛，本章保护它不被带跑；"
         "{{ch:09}} 把检测与线性滤波装进 AEC 总体结构，{{ch:11}} 用 AEC3 结构收口。",
  pitfalls=["用近端能量绝对值做判决，电平一变就整片误检。",
            "双讲结束后立刻恢复更新，残留尾音仍会把系数推偏。",
            "把时延漂移当成 h 变化而重置滤波器，付出无谓的重收敛代价。",
            "只在单讲数据上调阈值，双讲检测率报出来虚高。"],
  exercises=["由 ρ ≈ 1/√(1+q) 推导 q=1.5 时的 ρ，并给出 τ=0.80 的可检测 q 下限。",
             "解释主/阴影滤波器为何能降低一次误判的代价。",
             "设计一组覆盖 ppm 级时钟漂移与手掌遮挡的测试序列。"],
  further=["{{ch:09}} AEC 总体结构中的双讲逻辑；{{ch:11}} AEC3 的残余回声估计；{{ch:27}} 流式状态下的因果约束。"]),

# ==================================================================== 08
C("08", "p1", "part1/08-noise-estimation", "VAD 与噪声功率谱估计（MCRA 思路）",
  "没有干净参考，只能靠『噪声比语音更稳』这条统计假设把噪声谱跟出来。",
  hours="3 学时",
  goals=["能说明 VAD 与噪声功率谱估计为何互为前提。",
         "能写出 MCRA 的时频平滑、最小值跟踪与条件更新三步。",
         "能量化非平稳噪声下固定估计与跟踪估计的谱误差。",
         "能运行实验，用检测率、谱误差与 segSNR 核对谱减效果。"],
  points=["语音活动检测 VAD", "噪声功率谱 N[k,t]", "时频平滑", "最小值跟踪",
          "语音存在概率", "MCRA 条件更新", "非平稳噪声阶跃", "谱减与音乐噪声"],
  sections=[
      ("8.1", "两个互相依赖的估计量", sec(
          eq("Y[k,t] = S[k,t] + N[k,t]　，目标：从 |Y|² 里分离出 λ_n[k,t] = E{|N|²}"),
          p("VAD 需要噪声底才能判断『这一帧是不是语音』，噪声估计又只该在『没有语音的帧』更新——"
            "这是典型的鸡生蛋问题。MCRA（Minima Controlled Recursive Averaging）的解法是"
            "<strong>不硬判 VAD，而是用功率谱的最小值统计间接找噪声底</strong>：语音出现时功率上冲，"
            "静音/语音间隙回落到噪声底，滑动窗最小值就把这个底抓出来。"),
          table(["步骤", "递推式 / 操作", "作用"], [
              ["频域平滑", "S_f[k,t] = Σ_{j=−1..1} b_j · |Y[k+j,t]|²", "抹掉谱峰的随机尖刺"],
              ["时间平滑", "S[k,t] = α_s·S[k,t−1] + (1−α_s)·S_f[k,t]", "抑制帧间抖动"],
              ["最小值跟踪", "S_min[k,t] = min{S[k,t−W..t]}", "得到噪声底的保守估计"],
              ["条件更新", "若 S/S_min < δ 则 λ_n ← α_n·λ_n + (1−α_n)·|Y|²", "只在疑似无语音时更新噪声"],
          ], ["18%", "46%", "36%"]),
          note("与 AEC 的对称性", "AEC 有参考信号 x，是监督式辨识；ANS 没有参考，只能靠平稳性假设。"
               "所以 {{ch:03}} 强调：噪声估计错了，后面 {{ch:12}} 谱减与 {{ch:13}} 维纳增益一起错。"))),
      ("8.2", "语音存在概率与更新闸门", sec(
          eq("S_r[k,t] = S[k,t] / S_min[k,t]　，p̂[k,t] ≈ 1 当 S_r > δ，否则按 S_r 插值"),
          p("实践中不必显式算概率，直接用比值做闸门：<code>S_r &lt; δ</code>（本实验 δ=2.2，约 3.4 dB）"
            "就认为该 bin 当前由噪声主导，允许更新 <code>λ_n</code>；否则冻结。"
            "<code>α_n</code> 决定跟踪速度：太大跟不上噪声阶跃，太小会把语音低谷误当噪声。"),
          eq("增益（谱减形式）：G[k,t] = max(G_floor, 1 − β·√λ_n[k,t] / |Y[k,t]|)"),
          warn("音乐噪声", "逐 bin 独立相减会留下孤立的随机谱峰，听感像鸟叫/水声。设增益下限 G_floor "
               "并对相邻 bin 做平滑，是 {{ch:12}} 要解决的第一件事。"))),
      ("8.3", "实验怎么判『跟上噪声了』", sec(
          ul(["<strong>谱误差</strong>：逐 bin 算 10log₁₀(λ̂_n/λ_n) 的绝对均值（dB），固定估计与 MCRA 对比。",
              "<strong>跟踪曲线</strong>：噪声幅度在样本中段由 0.012 阶跃到 0.045，MCRA 曲线应跟着抬升。",
              "<strong>VAD 帧准确率</strong>：由后验 SNR 与阈值判决，与合成门控真值逐帧比对。",
              "<strong>segSNR</strong>：用两套噪声估计分别谱减，比较输出的分段 SNR。"]))),
  ],
  demos=[mk_demo(
      "code/08-noise-estimation.py", "实验 8-1 · MCRA 噪声跟踪、VAD 判决与谱减对照",
      "合成带静音段的语音与非平稳噪声，实现最小值控制的递推平均，打印检测率、谱误差与 segSNR。",
      """N, NF, HOP = 8000, 256, 128
ALPHA_S, ALPHA_N = 0.50, 0.90    # 时间平滑 / 噪声更新平滑
WIN = 12                         # 最小值跟踪窗（帧）
RATIO_TH = 2.2                   # S/S_min 更新闸门
VAD_TH_DB = 3.0                  # 帧级后验 SNR 阈值
SUB_FACTOR, FLOOR = 1.0, 0.15    # 谱减过减因子与增益下限""",
      """rng = random.Random(7)
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
      (seg_snr_db(speech, noisy), seg_snr_db(speech, out_fix), seg_snr_db(speech, out_mcra)))""",
      figs=[("fig/08-noise-track.svg", "MCRA 噪声功率跟踪与固定估计对照"),
            ("fig/08-vad.svg", "逐帧后验 SNR、阈值与 VAD 判决")],
      audio=[("audio/08-noisy.wav", "带非平稳噪声的语音"),
             ("audio/08-fixed.wav", "固定噪声估计谱减输出"),
             ("audio/08-mcra.wav", "MCRA 跟踪噪声谱减输出")],
      steps="观察噪声幅度阶跃后 MCRA 曲线是否抬升；对照 VAD 判决与真值门控；试听两个谱减 WAV 的残余噪声。",
      expect="固定估计停留在前 4 帧的低电平，MCRA 随阶跃跟踪到新噪声底，谱误差从 10.06 dB 降到 1.91 dB；"
             "但 MCRA 谱减的分段 SNR（7.93 dB）反而低于固定谱减（12.10 dB）——"
             "<strong>噪声谱估得准不等于输出质量高，过跟踪会连语音一起压掉</strong>。"
             "VAD 帧准确率 0.587、虚警率 0.630，说明阈值仍需按场景整定，可由 TP/FP/FN/TN 逐项复算。",
      tweak="把 ALPHA_N 调到 0.99，跟踪变慢但更稳；把 WIN 缩到 4 帧，最小值会被语音谷值污染。")],
  commands=[shell("本机自查 VAD/降噪滤镜与官方文档",
                  "ffmpeg -hide_banner -filters | grep -E 'silencedetect|afftdn|arnndn|astats'",
                  "只做本机能力自查；滤镜参数与引入版本以 https://ffmpeg.org/ffmpeg-filters.html 及本机 ffmpeg -filters 输出为准，本书不假定任何特定版本。")],
  highlights=[("wiki-vad", "VAD 的能量/统计/学习方法概览"),
              ("wiki-wiener", "噪声功率估计下游的最优滤波"),
              ("ffmpeg-silencedetect", "离线粗粒度 VAD 的现成入口"),
              ("dsprelated", "噪声跟踪与递推平均的工程文章")],
  repos=[REPOS[3], REPOS[2], REPOS[0]],
  analogy="MCRA 是一个带滞回的监控指标：滑动窗最小值是 P99 基线的反向版本（取的是下包络），"
          "比值闸门是告警条件，α_n 是指数移动平均的半衰期。"
          "<strong>它不判断『有没有语音』，只判断『这一刻能不能安全地更新基线』。</strong>",
  bridge="{{ch:03}} 给评价指标，本章给出 ANS 的第一个估计量；"
         "{{ch:12}} 用 λ_n 做谱减，{{ch:13}} 把它升级为先验 SNR 与 MMSE 增益。",
  pitfalls=["用有声段直接平均当噪声谱，语音一停就过减。",
            "最小值窗太短，语音音节间隙被当成噪声底。",
            "α_n 太大跟不上非平稳噪声，太小又把语音低谷吸进噪声估计。",
            "谱减不设增益下限，产生音乐噪声。"],
  exercises=["说明 VAD 与噪声估计为何互为前提，MCRA 用什么假设打破循环。",
             "推导 α_n=0.9 时噪声估计的时间常数（帧数与毫秒）。",
             "把噪声阶跃改成缓慢爬升，预测固定估计与 MCRA 的谱误差差距如何变化。"],
  further=["{{ch:12}} 谱减与音乐噪声；{{ch:13}} 维纳/MMSE 与先验 SNR；{{ch:09}} AEC 链路里 ANS 的位置。"]),

# ==================================================================== 09
C("09", "p2", "part2/09-aec-architecture", "AEC 总体结构：参考信号、线性滤波与残余抑制",
  "一条完整回声消除链路只有三类信号，却要同时管住线性、非线性与双讲。",
  hours="3 学时",
  goals=["能画出 AEC 三级结构并标出每个信号的可观测性。",
         "能说明参考信号为什么必须取自播放前的原始缓冲。",
         "能写出线性级与残余抑制级各自的输入、输出与失效模式。",
         "能运行实验，用 ERLE、segSNR 与 SI-SDR 逐级核对收益。"],
  points=["远端参考 x[n]", "麦克风 y[n]", "线性自适应滤波", "误差信号 e[n]",
          "残余回声估计", "频域后滤波增益", "双讲透明度", "非线性回声与削波"],
  sections=[
      ("9.1", "三级结构，逐级收紧", sec(
          eq("y[n] = h*x[n] + d[n] + v[n]　→　e[n] = y[n] − ŵ*x[n]　→　z[n] = G·e[n]"),
          p("<code>x[n]</code> 是<strong>送给扬声器之前</strong>的参考样本，<code>y[n]</code> 是麦克风采集，"
            "两者共享同一时钟域与同一份 PCM 数据。第一级用 {{ch:05}}/{{ch:06}} 的自适应滤波"
            "预测并减去线性回声；第二级估计剩下的<strong>残余回声功率谱</strong>，用逐 bin 增益压掉它；"
            "第三级（本书 {{ch:11}}、{{ch:24}}）处理非线性与双讲透明度的折中。"),
          table(["级", "输入", "输出", "能解决", "不能解决"], [
              ["时延对齐", "x, y", "对齐后的 x", "播放/采集缓冲偏移", "房间混响形状"],
              ["线性 AEC", "x, y", "e[n]", "线性卷积回声", "扬声器削波、路径突变瞬间"],
              ["残余抑制", "e, ŷ", "z[n]", "泄漏与非线性残余", "强双讲下的近端失真"],
          ], ["16%", "14%", "14%", "28%", "28%"]),
          warn("参考信号不能碰", "参考必须取自 AGC / 均衡 / 限幅<strong>之前</strong>的播放缓冲。"
               "任何对 x 的非线性处理都会破坏 y 与 x 之间的线性卷积假设，"
               "让自适应滤波器去追一个不存在的 h（{{ch:16}} 讲级联顺序时会再算一次这笔账）。"))),
      ("9.2", "残余抑制是一个功率谱上的 Wiener 型增益", sec(
          eq("P̂_res[k,t] = γ·|Ŷ[k,t]|²　，G[k,t] = max(G_floor, 1 − β·P̂_res[k,t] / P_e[k,t])"),
          p("<code>Ŷ</code> 是线性滤波器输出的预测回声谱。<strong>关键洞察</strong>：即使线性级已经把回声减掉了，"
            "Ŷ 仍携带『此刻应该有多少回声』的信息，把它按泄漏系数 γ 缩放就是残余回声功率的廉价估计——"
            "这正是 WebRTC AEC3 用线性滤波器输出做残余回声估计的思想。增益逐 bin、逐帧作用，不改相位。"),
          note("两级为什么都要", "线性级负责能量主体（ERLE 的大头），残余级负责尾巴与非线性。"
               "只靠一级把增益做狠，双讲时近端语音会被一起压掉——可懂度换 ERLE 是亏本买卖。"))),
      ("9.3", "用三个指标逐级验收", sec(
          ul(["<strong>ERLE</strong>：以真实回声 e[n] 与残余回声（输出减去已知近端与噪声）算能量比，"
              "分别报线性级与最终输出。",
              "<strong>segSNR</strong>：以近端语音为参考，看每级是否让语音更干净。",
              "<strong>SI-SDR</strong>：尺度不变，避免增益变化把结论带偏（{{ch:03}} 的尺度对齐要求）。"]),
          p("本实验刻意把近端语音放在后 40%（双讲），前段留出单讲让 NLMS 先收敛；"
            "这样打印的每个数值都对应一个明确的链路阶段，可逐项复算。"))),
  ],
  demos=[mk_demo(
      "code/09-aec-architecture.py", "实验 9-1 · 搭一条三级 AEC：线性 NLMS + 残差谱增益",
      "合成参考/近端/回声并跑完线性级与残余抑制级，打印各级 ERLE、segSNR 与 SI-SDR，输出可试听 WAV。",
      """N, L, NF, HOP = 4096, 64, 256, 128
MU = 0.60                  # 线性级 NLMS 步长
LEAK = 0.12                # 残余回声功率泄漏系数 γ
BETA = 1.00                # 残余抑制强度 β
FLOOR = 0.18               # 谱增益下限""",
      """rng = random.Random(7)
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
      (s0, s1, s2, si0, si2))""",
      figs=[("fig/09-stages.svg", "参考、线性预测、误差与最终输出的波形"),
            ("fig/09-metrics.svg", "逐级 ERLE 与分段 SNR 对照")],
      audio=[("audio/09-mic.wav", "麦克风信号：回声 + 后段双讲近端语音"),
             ("audio/09-linear.wav", "仅线性 AEC 后的误差信号"),
             ("audio/09-final.wav", "加残余回声抑制后的最终输出")],
      steps="先听 09-mic.wav → 09-linear.wav → 09-final.wav；再对照柱状图里 ERLE 与 segSNR 是否同向变好。",
      expect="线性级拿走 ERLE 的主体（约 21 dB），简化残余抑制在远端单讲段再抬升不到 1 dB；"
             "但因为它没有双讲检测，后 40% 双讲段的近端语音被一起压掉，segSNR 触到 −10 dB 下限、SI-SDR 明显下降。"
             "<strong>这条负面结果正是 {{ch:24}} 引入条件化神经后处理的原因</strong>：ERLE 单点变好不等于全链路变好。",
      tweak="把 BETA 调到 2.0，ERLE 会继续升高但双讲段近端语音变闷；把 LEAK 调到 0.0，残余抑制级退化为旁路。")],
  commands=[shell("本机自查音频滤镜与 AEC 测试标准入口",
                  "ffmpeg -hide_banner -filters | grep -E 'aecho|aresample|astats'",
                  "只做本机滤镜能力自查；回声消除器测试信号与 ERLE 口径以 https://www.itu.int/rec/T-REC-G.168/en 为准，滤镜可用性以 https://ffmpeg.org/ffmpeg-filters.html 与本机输出为准，本书不假定任何特定版本。")],
  highlights=[("wiki-aec", "回声消除问题定义与自适应滤波概述"),
              ("webrtc-aec3", "线性滤波 + 残余回声估计的现代结构"),
              ("speex", "经典开源 AEC，结构最易读"),
              ("itu-g168", "ERLE 与双讲测试信号的规范来源")],
  repos=[REPOS[0], REPOS[1], REPOS[4]],
  analogy="AEC 是一条带旁路输入的流式 pipeline：<code>x</code> 是旁路特征、<code>y</code> 是主数据流、"
          "线性级是回归模型、残余级是按特征功率调制的逐 bin 门控。"
          "<strong>参考信号一旦被 AGC 改过，就等于特征和标签不在同一分布里。</strong>",
  bridge="{{ch:06}} 给出频域线性滤波器、{{ch:07}} 给出双讲保护，本章把它们装进完整链路；"
         "{{ch:10}} 用 NLMS 做可验证实现，{{ch:11}} 升级为 AEC3 结构。",
  pitfalls=["参考信号取自 AGC/均衡之后，线性卷积假设被破坏。",
            "忽略播放与采集缓冲延迟，直接让滤波器硬追。",
            "只报总 ERLE，不区分线性级与残余抑制级各自的贡献。",
            "把残余增益下限设成 0，双讲时近端语音被整片压掉。"],
  exercises=["画出三级 AEC 框图，标出每级输入、输出与可观测信号。",
             "推导 G[k,t] 在 P̂_res ≫ P_e 与 P̂_res ≪ P_e 两种极限下的取值。",
             "解释为什么参考信号必须取自播放前而非播放后的缓冲。"],
  further=["{{ch:10}} 用 NLMS 实现可验证 AEC；{{ch:11}} AEC3 与残余抑制；{{ch:16}} 3A 级联顺序。"]),

# ==================================================================== 10
C("10", "p2", "part2/10-nlms-aec", "用 NLMS 实现一个可验证的 AEC",
  "把步长、阶数、正则、冻结条件全部摊开，让每个 ERLE 数字都能复算。",
  hours="3 学时",
  goals=["能实现一个逐样本 NLMS 回声消除器并画出滑动 ERLE 曲线。",
         "能量化步长 μ、阶数 L、正则 δ 对收敛速度与稳态 ERLE 的影响。",
         "能说明双讲冻结与滤波器阶数不足各自的失效表现。",
         "能运行实验，用收敛迭代数、权重误差与稳态 ERLE 交叉验证。"],
  points=["逐样本 NLMS", "滑动窗 ERLE", "收敛迭代数", "稳态失调",
          "步长扫描", "阶数不足与欠建模", "正则 δ", "双讲冻结上界"],
  sections=[
      ("10.1", "最小可用实现只有五行", sec(
          eq("x⃗[n] = (x[n], x[n−1], …, x[n−L+1])　，ŷ[n] = wᵀx⃗[n]　，e[n] = y[n] − ŷ[n]"),
          eq("w ← w + μ·e[n]·x⃗[n] / (x⃗[n]ᵀx⃗[n] + δ)　，0 < μ < 2"),
          p("AEC 与 {{ch:05}} 的系统辨识只差一件事：观测里多了近端语音 <code>d[n]</code> 和环境噪声。"
            "因此工程实现必须补三样东西：<strong>时延对齐</strong>（{{ch:01}}）、"
            "<strong>双讲冻结</strong>（{{ch:07}}）、<strong>输出残差的可听核对</strong>。"
            "本实验用已知双讲区间作为检测上界，把注意力集中在 μ / L / δ 上。"),
          table(["参数", "影响", "调小的后果", "调大的后果"], [
              ["μ 步长", "收敛速度 / 稳态失调", "收敛慢，路径突变追不上", "收敛快但稳态 ERLE 低、易发散"],
              ["L 阶数", "能覆盖的混响尾", "欠建模，残余回声压不下去", "算力线性增长、收敛变慢"],
              ["δ 正则", "静音段数值稳定", "输入能量趋零时步长爆炸", "等效缩小 μ，收敛变慢"],
          ], ["16%", "28%", "28%", "28%"]))),
      ("10.2", "怎样算『可验证』", sec(
          ul(["<strong>滑动窗 ERLE</strong>：每 256 样本算一次 10log₁₀(Σe²_echo/Σe²_res)，"
              "曲线拐点就是收敛时刻，比只报一个全局数更可核对。",
              "<strong>权重误差</strong>：‖w−h‖ 直接检查辨识的是真实路径，而不是碰巧拟合了当前样本。",
              "<strong>阶数扫描</strong>：真值 h 有 128 抽头，L=32 时稳态 ERLE 应明显偏低，"
              "这是欠建模（under-modeling）而非算法不收敛。",
              "<strong>双讲段</strong>：单独报一段 segSNR / SI-SDR，防止『整体 ERLE 高但近端被压掉』。"]),
          note("口径", "ERLE 只在单讲区间统计。把双讲段的近端语音算进分子分母，"
               "会得到虚高或虚低的数字，这是 {{ch:03}} 反复强调的评测陷阱。"))),
  ],
  demos=[mk_demo(
      "code/10-nlms-aec.py", "实验 10-1 · NLMS AEC 的步长扫描、阶数扫描与收敛核对",
      "实现带双讲冻结的逐样本 NLMS，扫描三个步长与三个阶数，打印滑动 ERLE、收敛迭代数、权重误差与稳态 ERLE。",
      """N, L = 3072, 64
MUS = (0.15, 0.50, 1.10)   # 步长扫描
LENS = (32, 64, 128)       # 阶数扫描
DELTA = 1e-3               # 正则项
DT_START = int(0.70 * N)   # 双讲起点（理想检测上界）
H_WIN = 256                # 滑动 ERLE 窗长""",
      """rng = random.Random(7)
sp = synthetic_speech(rng, N)
far = [0.78 * a + 0.22 * b for a, b in zip(sp, white_noise(rng, N, 0.18))]
h = rir(rng, 128, decay=0.006, direct_delay=20)
echo = fft_convolve(far, h)[:N]
near_raw = synthetic_speech(rng, N)
near = [0.65 * near_raw[i] if i >= DT_START else 0.0 for i in range(N)]
noise = white_noise(rng, N, 0.004)
mic = [echo[i] + near[i] + noise[i] for i in range(N)]

def run_nlms(mu, length):
    w = [0.0] * length
    err = [0.0] * N
    for n in range(length, N):
        xv = [far[n - i] for i in range(length)]
        y = sum(w[i] * xv[i] for i in range(length))
        e = mic[n] - y
        err[n] = e
        if n < DT_START:
            p = sum(v * v for v in xv) + DELTA
            for i in range(length):
                w[i] += mu * e * xv[i] / p
    curve = []
    for s in range(length, DT_START - H_WIN, H_WIN):
        curve.append(erle_db(echo[s:s + H_WIN], err[s:s + H_WIN]))
    werr = math.sqrt(sum((w[i] - h[i]) ** 2 for i in range(length)))
    steady = erle_db(echo[N // 2:DT_START], err[N // 2:DT_START])
    return curve, steady, werr, err

curves, steadies, werrs = [], [], []
best_err = None
for mu in MUS:
    cv, st, we, err = run_nlms(mu, L)
    curves.append(cv)
    steadies.append(st)
    werrs.append(we)
    if mu == 0.50:
        best_err = err
len_steadies = []
for ln in LENS:
    _cv, st, _we, _err = run_nlms(0.50, ln)
    len_steadies.append(st)

c = Chart(FIG / "10-learning.svg", "不同步长的滑动窗 ERLE 曲线", xlabel="窗序号", ylabel="ERLE (dB)")
for mu, cv, col in zip(MUS, curves, (BLUE, GREEN, RED)):
    c.line(range(len(cv)), cv, col, label="mu=%.2f" % mu)
c.hline(10.0, AMBER, label="10 dB 收敛线")
print("学习图:", c.save())
d = Chart(FIG / "10-erle-lens.svg", "滤波器阶数对稳态 ERLE 的影响", xlabel="抽头数 L", ylabel="ERLE (dB)",
          xticks=[(i, "L=%d" % ln) for i, ln in enumerate(LENS)])
d.bars(range(len(LENS)), len_steadies, BLUE, label="稳态 ERLE")
print("阶数图:", d.save())
write_wav(AUDIO / "10-mic.wav", normalize_peak(mic))
write_wav(AUDIO / "10-echo.wav", normalize_peak(echo))
write_wav(AUDIO / "10-error.wav", normalize_peak(best_err))
print("采样率=%d Hz 样本=%d 真值h=128抽头 双讲起点=%d 冻结=是 真值延迟=20" %
      (SAMPLE_RATE, N, DT_START))
for mu, st, we, cv in zip(MUS, steadies, werrs, curves):
    hit = next((i + 1 for i, v in enumerate(cv) if v >= 10.0), -1)
    print("mu=%.2f 稳态ERLE=%.2f dB 权重误差=%.4f 首次10dB窗=%d 约=%d样本" %
          (mu, st, we, hit, L + hit * H_WIN if hit > 0 else -1))
print("阶数扫描 稳态ERLE: " + " ".join("L=%d→%.2fdB" % (ln, s)
                                   for ln, s in zip(LENS, len_steadies)))
print("双讲段 segSNR=%.2f dB SI-SDR=%.2f dB" %
      (seg_snr_db(near[DT_START:], best_err[DT_START:]),
       si_sdr_db(best_err[DT_START:], near[DT_START:])))""",
      figs=[("fig/10-learning.svg", "三个步长的滑动窗 ERLE 学习曲线"),
            ("fig/10-erle-lens.svg", "阶数不足导致的稳态 ERLE 下降")],
      audio=[("audio/10-mic.wav", "含回声与后段双讲的麦克风信号"),
             ("audio/10-echo.wav", "真实回声分量（核对参考）"),
             ("audio/10-error.wav", "mu=0.50 的 NLMS 输出残差")],
      steps="对照三条学习曲线与 10 dB 线；看阶数扫描里 L=32 的 ERLE 缺口；试听 10-echo.wav 与 10-error.wav。",
      expect="本例三个步长的「首次 10 dB 窗」都是第 3 窗，μ=0.50 反而同时拿到最高稳态 ERLE（19.19 dB）与最小权重误差；"
             "μ=1.10 已越过最优值开始变差——<strong>步长与性能不是单调关系，必须扫描</strong>。"
             "阶数扫描则很干净：L=32 欠建模 13.13 dB，L=128 覆盖真值长度后达到 25.27 dB。",
      tweak="把 DELTA 调到 1e-6，静音段会出现数值抖动；把 DT_START 之后的冻结去掉，双讲段 SI-SDR 会明显下降。")],
  commands=[shell("用 ffmpeg 核对本章输出 WAV 的电平（本机自查）",
                  "ffmpeg -hide_banner -i part2/10-nlms-aec/audio/10-error.wav -af volumedetect -f null -",
                  "命令只读取本机已生成文件并做电平自查；滤镜与参数以 https://ffmpeg.org/ffmpeg-filters.html 及本机 ffmpeg -filters 输出为准，本书不假定任何特定版本。")],
  highlights=[("wiki-lms", "LMS/NLMS 更新式与收敛条件"),
              ("speexdsp", "经典 AEC 中 NLMS 的工业实现，可逐行对照"),
              ("webrtc-aec3", "频域分块版本与本章时域实现的对照"),
              ("numpy", "把 x⃗ 与 w 的乘加向量化后的迁移目标")],
  repos=[REPOS[1], REPOS[0], REPOS[12]],
  analogy="这章就是给 {{ch:05}} 的在线 SGD 加了一套单元测试："
          "滑动 ERLE 是训练曲线、权重误差是参数回归测试、阶数扫描是容量不足的消融实验、"
          "双讲冻结是 label 清洗。<strong>四条都过，才敢说 AEC『收敛了』。</strong>",
  bridge="{{ch:05}} 给出 NLMS 更新式、{{ch:09}} 给出 AEC 结构，本章把两者合成为可复算的实现；"
         "{{ch:11}} 处理它消不掉的非线性残余，{{ch:18}} 把 ERLE 放进完整评测。",
  pitfalls=["把双讲段的近端语音算进 ERLE 分子分母，指标失真。",
            "滤波器阶数小于真实混响长度，误判为算法不收敛。",
            "δ 设为 0，静音段输入能量趋零导致系数爆炸。",
            "只报全局 ERLE，不报稳态与收敛迭代数。"],
  exercises=["推导 0 < μ < 2 的稳定性条件，并说明 δ 应如何与输入功率同量级。",
             "解释 L=32 时 ERLE 上不去的物理原因，并估算 16 kHz 下 128 ms 混响所需抽头。",
             "在双讲段取消冻结，预测权重误差与 SI-SDR 曲线的变化。"],
  further=["{{ch:09}} AEC 总体结构；{{ch:11}} 残余回声抑制与 AEC3；{{ch:18}} 经典链路综合评测。"]),

# ==================================================================== 11
C("11", "p2", "part2/11-residual-echo", "残余回声抑制与 WebRTC AEC3 结构",
  "线性滤波器解释不了扬声器削波，最后一段回声要靠功率谱估计来收。",
  hours="3 学时",
  goals=["能说明非线性回声为何让线性 AEC 留下不可消除的残余。",
         "能写出基于线性预测谱的残余回声功率估计与 Wiener 型后滤波增益。",
         "能解释 AEC3 中主/阴影滤波器、延迟估计与残余回声估计的分工。",
         "能运行实验，量化抑制强度 β 与残余 ERLE、双讲保真度的折中。"],
  points=["非线性回声与削波", "残余回声功率谱", "泄漏系数 γ", "Wiener 型后滤波",
          "AEC3 主/阴影滤波器", "延迟估计与缓冲对齐", "双讲透明度", "过抑制与语音失真"],
  sections=[
      ("11.1", "线性模型的天花板", sec(
          eq("e_lin[n] = y[n] − ŵ*x[n] ≈ (h*x)[n] − ŵ*x[n] + f_nl(x[n]) + d[n] + v[n]"),
          p("<code>f_nl</code> 是扬声器饱和、外壳振动、编解码削波引入的非线性项，"
            "它<strong>不能写成 x 的线性卷积</strong>，所以再长的自适应滤波器也无解。"
            "本章实验用 <code>tanh(1.8·u)</code> 人为制造这种饱和，"
            "让线性级刻意留下一段可测量的残余，再交给后滤波。"),
          table(["残余来源", "与 x 的关系", "线性 AEC 能否消除", "对策"], [
              ["混响尾超出 L", "线性但欠建模", "加大 L 可缓解", "分块 MDF 覆盖更长尾"],
              ["路径突变瞬间", "线性但时变", "需重收敛时间", "阴影滤波器 + 快速重估"],
              ["扬声器削波", "非线性 f_nl(x)", "不能", "残余功率估计 + 后滤波"],
              ["时钟漂移", "延迟缓变", "会周期性塌陷", "延迟估计 + 重采样"],
          ], ["20%", "24%", "24%", "32%"]))),
      ("11.2", "AEC3 的四块拼图", sec(
          ul(["<strong>延迟估计</strong>：在参考缓冲里找与 y 最相关的对齐位置，先把 x 与 y 放到同一时间轴。",
              "<strong>主滤波器 + 阴影滤波器</strong>：阴影滤波器持续自由更新、不受双讲保护，"
              "只有稳定优于主滤波器才替换，兼顾快速重收敛与误判鲁棒性。",
              "<strong>残余回声估计</strong>：用线性预测谱 Ŷ 与误差谱 E 的相干性，"
              "估出每个 bin 还漏了多少回声功率。",
              "<strong>残余抑制器</strong>：把估计功率转成逐 bin 增益 G，作用在线性误差上，"
              "并与噪声抑制、AGC 串成完整 3A（{{ch:16}}）。"]),
          eq("P̂_res[k,t] = γ·|Ŷ[k,t]|²　，G[k,t] = max(G_floor, 1 − β·P̂_res[k,t] / P_e[k,t])"),
          note("为什么用 Ŷ 而不是 x", "Ŷ 已经过 ŵ 的整形，刻度与真实回声能量一致；"
               "直接用 |X|² 会把尚未被线性级消掉的那部分也算进去，导致过抑制。"))),
      ("11.3", "一条永远存在的折中曲线", sec(
          eq("β ↑ ⇒ 残余 ERLE ↑　但　双讲段 SI-SDR ↓　（近端语音被当成残余一起压掉）"),
          p("实验扫描 <code>β ∈ {0.4, 1.0, 2.0}</code>，同时打印残余 ERLE、双讲段 segSNR 与 SI-SDR。"
            "工程上不能用『把回声压到零』做目标函数，"
            "必须把<strong>双讲透明度</strong>作为并列约束；这正是 {{ch:03}} 要求同时报失真类与主观/无参考指标的原因。"),
          warn("别把残余抑制当 ANS", "后滤波的模板是回声预测谱 Ŷ，不是噪声谱 λ_n。"
               "两者混淆会在远端静音时把近端语音一起衰减——降噪任务属于 {{ch:12}}～{{ch:13}}。"))),
  ],
  demos=[mk_demo(
      "code/11-residual-echo.py", "实验 11-1 · 非线性回声下的残余抑制与 β 折中扫描",
      "用 tanh 制造非线性回声，跑线性 NLMS 后做逐 bin 后滤波，打印 β 扫描下的残余 ERLE 与双讲保真度。",
      """N, L, NF, HOP = 4096, 64, 256, 128
MU = 0.60                  # 线性级 NLMS 步长
BETAS = (0.4, 1.0, 2.0)   # 残余抑制强度扫描
GAMMA = 0.20               # 残余回声功率泄漏系数
FLOOR = 0.12               # 谱增益下限
DT_START = int(0.55 * N)   # 双讲起点""",
      """rng = random.Random(7)
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
print("抑制前后平均谱能量差=%.2f dB" % (statistics.fmean(s_lin) - statistics.fmean(s_out)))""",
      figs=[("fig/11-tradeoff.svg", "β 扫描下残余 ERLE 与双讲保真度的折中"),
            ("fig/11-spectrum.svg", "残余抑制前后的平均功率谱")],
      audio=[("audio/11-mic.wav", "含非线性回声与双讲的麦克风信号"),
             ("audio/11-linear.wav", "仅线性 AEC 后，仍可听到残余回声"),
             ("audio/11-suppressed.wav", "beta=1.0 残余抑制后的输出")],
      steps="先听 11-linear.wav 里线性级消不掉的残余，再听 11-suppressed.wav；对照折中图判断 β=1.0 是否平衡。",
      expect="β 增大时残余 ERLE 单调上升（22.60→23.14 dB），平均谱整体下移约 1.8 dB；"
             "但双讲段 segSNR 全部触到 −10 dB 下限、SI-SDR 停留在 −46～−36 dB，说明"
             "<strong>这套固定增益后滤波根本没有保住近端语音</strong>。"
             "折中不是「稍微变差」，而是必须先加双讲检测与条件化增益（{{ch:24}}）。",
      tweak="把 GAMMA 调到 0.05，ERLE 提升变小但近端更保真；把 FLOOR 调到 0.5，过抑制消失但残余回声回升。")],
  commands=[shell("本机自查 AEC3 源码入口与官方链接",
                  "git ls-remote https://webrtc.googlesource.com/src HEAD",
                  "只检查仓库可达性；AEC3 残余回声估计与抑制结构以 https://webrtc.googlesource.com/src/+/refs/heads/main/modules/audio_processing/aec3/ 官方文档与源码为准，本书不假定任何特定版本。")],
  highlights=[("webrtc-aec3", "AEC3 分块频域滤波 + 残余回声估计的工业参考"),
              ("aec-challenge", "真实非线性失真与双讲录音，验证后滤波必备"),
              ("itu-g168", "残余回声与双讲透明度的测试口径"),
              ("rnnoise-paper", "混合 DSP/神经后滤波的经典思路")],
  repos=[REPOS[0], REPOS[4], REPOS[2]],
  analogy="线性 AEC 是编译器能静态分析的那部分，残余抑制是运行时兜底的 rate limiter："
          "模板来自预测谱，增益是逐 bin 的限流阀，β 是阈值松紧。"
          "<strong>阈值调得太狠，正常流量（近端语音）也会被限掉。</strong>",
  bridge="{{ch:09}} 给出三级 AEC、{{ch:10}} 给出可验证的线性实现，本章补上非线性残余与 AEC3 结构；"
         "{{ch:12}} 起转入 ANS，{{ch:24}} 会把这段后滤波换成神经模型。",
  pitfalls=["用参考谱 |X|² 而非预测谱 |Ŷ|² 构造残余估计，导致过抑制。",
            "只优化残余 ERLE，把双讲近端语音一起压掉。",
            "把残余抑制与噪声抑制混为一谈，远端静音时误伤语音。",
            "增益下限设为 0，谱洞造成明显音乐噪声与语音发闷。"],
  exercises=["解释 tanh 饱和为什么不能写成 x 的线性卷积。",
             "推导 β→0 与 β→∞ 时 G[k,t] 的极限，并说明折中曲线的两端。",
             "说明主/阴影滤波器如何同时满足快速重收敛与误判鲁棒性。"],
  further=["{{ch:12}} 谱减与音乐噪声；{{ch:24}} 神经 AEC 与联合建模；{{ch:16}} 3A 级联顺序。"]),

]
