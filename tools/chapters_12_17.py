#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 12～17 章：经典 ANS / AGC、阵列、级联顺序与工具链。"""
from __future__ import annotations

from book_schema import C, eq, table
from chapter_kit import mk_demo, shell, p, ul, ol, note, warn, sec


def S(num, title, *parts):
    """构造 (编号, 标题, HTML) 原理小节，避免深层嵌套括号。"""
    return (num, title, sec(*parts))


CH = [

# ==================================================================== 12
C("12", "p2", "part2/12-spectral-subtraction", "谱减、过减因子与音乐噪声",
  "从「减去噪声功率谱」这一行公式出发，把 ANS 的经典基线及其副作用讲透。",
  hours="3 学时",
  goals=["能从加性噪声模型推导功率谱减与幅度谱减的增益式。",
         "能说明过减因子、谱下限与音乐噪声三者的定量关系。",
         "能实现逐帧逐频率箱的谱减器并测量分段 SNR。",
         "能解释为什么「指标变好」不等于「听感变好」。"],
  points=["加性噪声模型", "功率谱减", "幅度谱减", "过减因子", "谱下限与谱底",
          "音乐噪声", "噪声功率谱估计", "分段 SNR 权衡"],
  sections=[
      S("12.1", "一行公式，一个增益矩阵",
        eq("Y[t,k] = S[t,k] + N[t,k]　→　G[t,k] = max(G_floor, 1 − β·P̂_n / |Y[t,k]|²)"),
        p("把 {{ch:02}} 的 STFT 矩阵看成二维表：行是频率箱 <code>k</code>，列是帧 <code>t</code>。"
          "谱减的全部工作就是给每个格子算一个 <code>0 ≤ G ≤ 1</code>，再令 "
          "<code>Ŝ = G·Y</code>。相位保持不变——既低延迟低算力，也是 {{ch:22}} 要讨论的局限。"),
        table(["变体", "增益式", "特点"], [
            ["功率谱减", "G = max(G_floor, 1 − β·P̂_n/|Y|²)", "推导最自然，残余起伏大"],
            ["幅度谱减", "G = max(G_floor, 1 − β·√P̂_n/|Y|)", "对强噪声更温和，仍有孤立谱峰"],
            ["Wiener 型", "G = ξ/(1+ξ)，ξ 为先验 SNR", "见 {{ch:13}}，增益有概率解释"],
        ], ["18%", "44%", "38%"])),
      S("12.2", "音乐噪声：被过度抑制留下的孤立谱峰",
        p("噪声是随机的：某帧某箱恰好噪声很小，增益就被算得很高；相邻箱却可能被压到下限。"
          "这种时频上零星闪现的窄带残响听起来像水滴，称为<strong>音乐噪声</strong>。"
          "缓解手段有三：增大过减因子 <code>β</code>、抬高谱下限 <code>G_floor</code>、对增益做时频平滑。"),
        ul(["<code>β</code> 增大：残余噪声下降，但语音高频一起被削，可懂度变差。",
            "<code>G_floor</code> 增大：谱空洞变少、听感平稳，但降噪量下降。",
            "增益平滑：抹掉孤立深陷，代价是引入时域拖尾。"]),
        note("可检验的判据", "实验统计「增益被压到下限的频率箱比例」作为语音失真与音乐噪声风险的粗略代理量。"
             "它不替代主观听测，但能量化 β 与 G_floor 这一对拉扯的旋钮：降噪越狠，触底箱越多。")),
  ],
  demos=[mk_demo(
      file="code/12-spectral-subtraction.py",
      title="实验 12-1 · 过减因子扫描：分段 SNR 与音乐噪声的拉扯",
      doc="在合成带噪语音上扫描过减因子，测量分段 SNR 与孤立谱洞数量。",
      params="""N = 8000
N_FFT, HOP = 256, 128
NOISE_AMP = 0.035
FACTORS = (0.5, 1.0, 1.5, 2.0, 3.0)
FLOOR = 0.15""",
      body="""rng = random.Random(7)
clean = synthetic_speech(rng, N)
noise = white_noise(rng, N, NOISE_AMP)
noisy = [clean[i] + noise[i] for i in range(N)]
nf = stft(noise, N_FFT, HOP)[:8]
nmag = [sum(math.hypot(re[k], im[k]) for re, im in nf) / len(nf) for k in range(N_FFT)]

def enhance(sub, floor):
    frames = stft(noisy, N_FFT, HOP)
    floored = 0
    for re, im in frames:
        gains = []
        for k in range(N_FFT):
            mag = math.hypot(re[k], im[k])
            g = max(floor, 1.0 - sub * nmag[k] / (mag + 1e-9))
            gains.append(g)
            re[k] *= g
            im[k] *= g
        floored += sum(1 for v in gains if v <= floor + 1e-9)
    return istft(frames, N_FFT, HOP, N), floored / max(1, len(frames) * N_FFT)

scores, clipped = [], []
for f in FACTORS:
    out, h = enhance(f, FLOOR)
    scores.append(seg_snr_db(clean, scale_align(out, clean)))
    clipped.append(h)
best = scores.index(max(scores))
out_best, _ = enhance(FACTORS[best], FLOOR)

c = Chart(FIG / "12-subtraction.svg", "过减因子与分段 SNR", xlabel="过减因子 beta", ylabel="dB",
          xticks=[(i, "%.1f" % f) for i, f in enumerate(FACTORS)])
c.line(range(len(FACTORS)), scores, BLUE, label="分段 SNR (dB)")
c.line(range(len(FACTORS)), [seg_snr_db(clean, noisy)] * len(FACTORS), RED, label="未处理")
print("SNR图:", c.save())
b = Chart(FIG / "12-distortion.svg", "过减因子与谱增益触底比例（语音失真代理量）",
          xlabel="过减因子 beta", ylabel="触底频率箱比例",
          xticks=[(i, "%.1f" % f) for i, f in enumerate(FACTORS)])
b.bars(range(len(FACTORS)), clipped, RED, label="触底比例")
print("失真图:", b.save())
write_wav(AUDIO / "12-noisy.wav", normalize_peak(noisy))
write_wav(AUDIO / "12-enhanced.wav", normalize_peak(out_best))
print("segSNR 未处理=%.2f | 谱减: " % seg_snr_db(clean, noisy) +
      " ".join("b=%.1f->%.2f" % (f, s) for f, s in zip(FACTORS, scores)))
print("触底比例: " + " ".join("b=%.1f->%.3f" % (f, c) for f, c in zip(FACTORS, clipped)))
print("最佳 beta=%.1f | SAMPLE_RATE=%d N_FFT=%d" % (FACTORS[best], SAMPLE_RATE, N_FFT))""",
      figs=[("fig/12-subtraction.svg", "过减因子与分段 SNR"),
            ("fig/12-distortion.svg", "过减因子与谱增益触底比例")],
      audio=[("audio/12-noisy.wav", "带噪输入：均匀白噪声"),
             ("audio/12-enhanced.wav", "谱减输出：注意残留的窄带起伏")],
      steps="对照两条曲线：找出 SNR 最高的因子，再看它对应的触底比例；试听两个 WAV。",
      expect="分段 SNR 随 β 先升后降，而谱增益触底比例单调上升——降噪越狠，被压到下限的频率箱越多，"
             "语音高频与清音一起被削。<strong>最优客观分数与最舒适听感通常不是同一个 β</strong>，"
             "这就是主观评测不可省的原因。",
      tweak="把 FLOOR 从 0.15 改到 0.35，触底比例的分母不变但失真减轻，降噪量也会下降。")],
  commands=[shell("用 ffmpeg afftdn 做一次离线对照",
                  "ffmpeg -hide_banner -i noisy.wav -af afftdn=nt=w:om=o denoised.wav",
                  "afftdn 是 ffmpeg 文档中基于 FFT 的自适应降噪滤镜；参数与可用性以本机 "
                  "`ffmpeg -h filter=afftdn` 与 https://ffmpeg.org/ffmpeg-filters.html 为准，"
                  "本书不假定任何特定版本具备该滤镜。")],
  highlights=[("wiki-spectral-sub", "谱减与音乐噪声的经典定义"),
              ("ffmpeg-afftdn", "命令行里的频域降噪对照"),
              ("wiki-wiener", "从谱减过渡到统计最优滤波"),
              ("rnnoise-paper", "混合 DSP/深度学习如何处理残留噪声")],
  analogy="谱减是对 STFT 矩阵做逐元素 clamp。每个频率箱是一个独立的小控制器，"
          "控制器之间不通信，于是才会出现孤立的谱洞。",
  bridge="{{ch:08}} 解决「噪声有多大」，本章解决「知道了以后怎么减」；"
         "{{ch:13}} 把同一增益换成有统计最优解释的 Wiener 形式。",
  pitfalls=["把噪声功率谱当常数，非平稳噪声下越减越差。",
            "只报 segSNR，忽略音乐噪声与语音失真。",
            "增益下限设为 0，制造深谱洞与明显水滴声。",
            "谱减后不做 WOLA 归一化，边界出现爆音。"],
  exercises=["推导功率谱减与幅度谱减的增益式，说明二者对强噪声的差异。",
             "解释为什么增大 G_floor 能减少音乐噪声却降低降噪量。",
             "设计一个同时报降噪量与语音失真的双指标评测表。"],
  further=["{{ch:13}} Wiener / MMSE；{{ch:23}} 神经噪声抑制；{{ch:19}} 时频掩码视角。"]),

# ==================================================================== 13
C("13", "p2", "part2/13-wiener-mmse", "Wiener 滤波、先验 SNR 与 MMSE-STSA",
  "把「拍脑袋的增益」换成最小均方误差意义下的最优增益，并解释决策导向估计。",
  hours="3 学时",
  goals=["能从 MMSE 准则推导 Wiener 增益 G = ξ/(1+ξ)。",
         "能区分后验 SNR γ 与先验 SNR ξ，说明决策导向递推的作用。",
         "能实现 Wiener 降噪器并量化平滑系数对指标的影响。",
         "能说清 Wiener 与谱减在形式上的联系与差别。"],
  points=["MMSE 估计", "Wiener 增益", "后验 SNR γ", "先验 SNR ξ",
          "决策导向估计", "MMSE-STSA", "增益平滑与拖尾", "噪声功率谱"],
  sections=[
      S("13.1", "从最优估计到一条增益曲线",
        eq("Ŝ = argmin E[(S − Ŝ)²]　→　G = ξ/(1+ξ)　，ξ = E|S|²/σ_n²，γ = |Y|²/σ_n²"),
        p("<code>ξ</code> 是<strong>先验</strong> SNR（观测前对干净谱能量的期望），"
          "<code>γ</code> 是<strong>后验</strong> SNR（这帧实际测到的能量比）。"
          "谱减用 γ 直接代公式，对随机起伏敏感；Wiener 用 ξ，把上一帧估计当先验，天然更平滑。"),
        table(["量", "定义", "在代码里", "作用"], [
            ["γ[t,k]", "|Y|² / σ_n²", "当帧计算", "瞬时证据"],
            ["ξ[t,k]", "a·G²[t−1]·γ[t−1] + (1−a)·max(γ−1,0)", "递推维护", "平滑后的先验"],
            ["a", "0.9～0.99", "参数区", "越大越平滑，也越拖尾"],
            ["G", "ξ/(1+ξ)", "逐箱逐帧", "恒在 [0,1]，无需人为下限"],
        ], ["12%", "44%", "18%", "26%"])),
      S("13.2", "决策导向：用上一帧的输出当这一帧的先验",
        p("上式即 Ephraim–Malah 系列里的<strong>决策导向（decision-directed）</strong>估计。"
          "从程序员视角看，这是一条跨帧的一阶 IIR 状态：<strong>算法从此有了状态，也就有了记忆和延迟</strong>。"),
        ul(["<code>a = 0</code>：完全用瞬时估计，退化为带噪增益，音乐噪声明显。",
            "<code>a → 1</code>：增益几乎不变，输出平稳但语音起音被拖慢。",
            "MMSE-STSA 在增益里进一步引入修正贝塞尔函数，低 SNR 箱压得更彻底，工程上常查表近似。"]),
        note("与上卷其它模块的关系", "这里的状态递推与 {{ch:14}} 的 AGC 包络、"
             "{{ch:08}} 的 MCRA 噪声跟踪是同一种一阶平滑器，只是平滑对象不同：增益、电平、噪声功率。")),
  ],
  demos=[mk_demo(
      file="code/13-wiener-mmse.py",
      title="实验 13-1 · 决策导向 Wiener 增益与平滑系数扫描",
      doc="实现先验 SNR 递推与 Wiener 增益，扫描平滑系数并与未处理信号对照。",
      params="""N = 8000
N_FFT, HOP = 256, 128
NOISE_AMP = 0.035
ALPHAS = (0.0, 0.50, 0.90, 0.98)""",
      body="""rng = random.Random(7)
clean = synthetic_speech(rng, N)
noise = white_noise(rng, N, NOISE_AMP)
noisy = [clean[i] + noise[i] for i in range(N)]
nf = stft(noise, N_FFT, HOP)[:8]
npow = [sum(re[k]**2 + im[k]**2 for re, im in nf) / len(nf) for k in range(N_FFT)]

def wiener(alpha):
    frames = stft(noisy, N_FFT, HOP)
    prev_g, prev_gamma = [1.0] * N_FFT, [1.0] * N_FFT
    first = None
    for re, im in frames:
        new_g, new_gamma = [], []
        for k in range(N_FFT):
            gamma = (re[k]**2 + im[k]**2) / (npow[k] + 1e-12)
            xi = alpha * prev_g[k]**2 * prev_gamma[k] + (1.0 - alpha) * max(gamma - 1.0, 0.0)
            g = xi / (1.0 + xi + 1e-12)
            re[k] *= g
            im[k] *= g
            new_g.append(g)
            new_gamma.append(gamma)
        if first is None:
            first = new_g
        prev_g, prev_gamma = new_g, new_gamma
    return istft(frames, N_FFT, HOP, N), first

scores, outputs = [], []
for a in ALPHAS:
    out, _g = wiener(a)
    outputs.append(out)
    scores.append(seg_snr_db(clean, scale_align(out, clean)))
_, gains = wiener(0.98)
c = Chart(FIG / "13-wiener.svg", "决策导向平滑系数与分段 SNR", xlabel="平滑系数 a", ylabel="dB",
          xticks=[(i, "%.2f" % a) for i, a in enumerate(ALPHAS)])
c.line(range(len(ALPHAS)), scores, BLUE, label="Wiener segSNR (dB)")
c.line(range(len(ALPHAS)), [seg_snr_db(clean, noisy)] * len(ALPHAS), RED, label="未处理")
print("Wiener图:", c.save())
g = Chart(FIG / "13-gains.svg", "a=0.98 时首帧各频率箱的 Wiener 增益", xlabel="频率箱 k", ylabel="增益")
g.line(range(N_FFT // 2), gains[:N_FFT // 2], GREEN, label="G[k]")
print("增益图:", g.save())
write_wav(AUDIO / "13-noisy.wav", normalize_peak(noisy))
write_wav(AUDIO / "13-wiener.wav", normalize_peak(outputs[-1]))
print("未处理 segSNR=%.2f | Wiener: " % seg_snr_db(clean, noisy) +
      " ".join("a=%.2f->%.2f" % (a, s) for a, s in zip(ALPHAS, scores)))
print("SI-SDR 未处理=%.2f -> a=0.98 后=%.2f | SAMPLE_RATE=%d N_FFT=%d" %
      (si_sdr_db(noisy, clean), si_sdr_db(outputs[-1], clean), SAMPLE_RATE, N_FFT))""",
      figs=[("fig/13-wiener.svg", "平滑系数与分段 SNR"),
            ("fig/13-gains.svg", "单帧逐频率箱增益曲线")],
      audio=[("audio/13-noisy.wav", "带噪输入"),
             ("audio/13-wiener.wav", "a=0.98 的 Wiener 输出")],
      steps="对照四个平滑系数的分段 SNR 与增益曲线；试听输出。",
      expect="适度平滑显著提高分段 SNR 并让增益曲线连续；a=0 时增益随噪声随机起伏，"
             "a 过大则语音起音被拖慢。<strong>segSNR 无法反映拖尾，必须配合听测。</strong>",
      tweak="把 NOISE_AMP 提到 0.08，观察高噪声下各平滑系数的排序是否改变。")],
  commands=[shell("用 ffmpeg anlmdn 对照非平稳噪声的处理",
                  "ffmpeg -hide_banner -i noisy.wav -af anlmdn=s=256:p=0.002 out.wav",
                  "anlmdn 是 ffmpeg 文档中的非局部均值降噪滤镜；参数名与可用性以本机 "
                  "`ffmpeg -h filter=anlmdn` 与 https://ffmpeg.org/ffmpeg-filters.html 为准。")],
  highlights=[("wiki-wiener", "Wiener 滤波的最小均方误差推导"),
              ("rnnoise-paper", "混合系统里频带增益的现代版本"),
              ("ffmpeg-anlmdn", "命令行降噪的另一种思路"),
              ("dsprelated", "先验 SNR 与决策导向的工程文章")],
  analogy="决策导向是一条跨帧指数移动平均：<code>state = a*state + (1-a)*evidence</code>，"
          "与监控里平滑 QPS 曲线同构，只是状态维度等于频率箱数。",
  bridge="{{ch:12}} 的谱减是「无状态增益」，本章引入跨帧状态；"
         "{{ch:14}} 用同样的一阶状态平滑 AGC 增益，{{ch:23}} 则让网络自己学这条递推。",
  pitfalls=["把 γ 与 ξ 混用，导致增益在静音帧剧烈跳变。",
            "平滑系数取 1，增益完全不更新，非平稳噪声下失效。",
            "噪声功率谱用全段均值估计，把语音段也算进噪声。",
            "认为 Wiener「最优」就等于主观最好（它只最优均方误差）。"],
  exercises=["从 MMSE 准则推导实增益 G = ξ/(1+ξ)。",
             "解释为什么决策导向会引入一帧量级的瞬态拖尾。",
             "把噪声改成前静后响，观察固定噪声谱的失效。"],
  further=["{{ch:08}} 噪声功率估计；{{ch:19}} 可学习掩码；{{ch:23}} RNNoise 频带增益。"]),

# ==================================================================== 14
C("14", "p2", "part2/14-agc", "AGC：包络跟踪、攻击释放、限幅与响度",
  "AGC 不改内容只改尺度，却是 3A 里最容易破坏评测、也最容易被听出来的模块。",
  hours="3 学时",
  goals=["能区分峰值电平、RMS 电平与响度三种「大小」的定义。",
         "能实现带攻击/释放的 AGC 增益环路并解释增益泵浦。",
         "能说明为什么 AGC 必须放在 AEC 与 ANS 之后。",
         "能解释 AGC 之后评测必须做尺度对齐。"],
  points=["峰值与 RMS 电平", "响度与 LUFS", "包络跟踪", "攻击时间与释放时间",
          "增益泵浦", "限幅与真峰值", "静态增益与动态增益", "尺度对齐"],
  sections=[
      S("14.1", "三种「大小」，三种控制目标",
        eq("g[t] = L_target / L̂[t]　，L̂[t] = (1−a)·L̂[t−1] + a·|x[t]|　（上升慢、下降快）"),
        table(["量", "定义", "反应速度", "典型用途"], [
            ["峰值", "max |x[n]|", "瞬时", "防削波，配 alimiter"],
            ["RMS", "√(mean x²)", "20–400 ms 窗", "传统 AGC 的主控制量"],
            ["响度 LUFS", "K 加权 + 门控（BS.1770）", "400 ms～整段", "广播/流媒体合规"],
        ], ["16%", "34%", "22%", "28%"]),
        p("传统 AGC 用 RMS 包络做<strong>反馈控制</strong>：电平低就慢慢抬增益（释放），"
          "电平突然变高就快速压增益（攻击），避免削波。"
          "注意「攻击/释放」是相对增益而言：增益下降要快，增益上升要慢。")),
      S("14.2", "增益泵浦、限幅与顺序约束",
        p("静音段没有语音，包络降到噪声底，AGC 会把增益一路抬到上限；"
          "下一句语音进来，噪声被一起放大，随后增益又被压下去——"
          "这种背景噪声随语音起伏的现象叫<strong>增益泵浦（pumping）</strong>。"
          "工程上用最大增益钳位、静音段冻结增益（配合 VAD）与输出端限幅器来约束它。"),
        ul(["<strong>限幅</strong>：<code>clip()</code> 是硬削波，会产生谐波；生产用带前瞻的软限幅。",
            "<strong>真峰值</strong>：采样点峰值不等于重建后的模拟峰值，广播按 ITU-R BS.1770 测 True Peak。",
            "<strong>尺度对齐</strong>：{{ch:03}} 已证明，AGC 后直接用干净参考相减会把增益差误判为噪声。"]),
        warn("顺序是硬约束", "AGC 若放在 AEC 之前，麦克风信号被整体缩放而远端参考没有，"
             "线性卷积关系被破坏，自适应滤波器会去追一个不存在的 h。"
             "推荐顺序永远是 <code>AEC → ANS → AGC</code>，{{ch:16}} 给出定量对照。")),
  ],
  demos=[mk_demo(
      file="code/14-agc.py",
      title="实验 14-1 · 电平跳变下的 AGC 环路、泵浦与限幅",
      doc="合成强弱交替的语音段，实现带攻击/释放的 AGC，测量分段 RMS、增益起伏与钳位计数。",
      params="""N = 12000
SEG = 2000
TARGET = 0.16
MAX_GAIN = 8.0
ATTACK = 0.004
RELEASE = 0.030""",
      body="""rng = random.Random(7)
base = synthetic_speech(rng, N)
noise = white_noise(rng, N, 0.002)
level = [0.15 if (i // SEG) % 2 == 0 else 1.0 for i in range(N)]
x = [base[i] * level[i] + noise[i] for i in range(N)]
env = rolling_rms(x, 256)
raw_g = [min(MAX_GAIN, TARGET / (e + 1e-4)) for e in env]
g = smooth(raw_g, ATTACK, RELEASE)
out = clip([x[i] * g[i] for i in range(N)])
before = [rms(x[s:s + SEG]) for s in range(0, N, SEG)]
after = [rms(out[s:s + SEG]) for s in range(0, N, SEG)]
clipped = sum(1 for v in out if abs(v) >= 0.999)
c = Chart(FIG / "14-agc.svg", "输入包络与 AGC 增益轨迹", xlabel="样本 / 200", ylabel="RMS 或归一化增益")
c.line(range(0, N, 200), [env[i] for i in range(0, N, 200)], BLUE, label="输入 RMS 包络")
c.line(range(0, N, 200), [g[i] / MAX_GAIN for i in range(0, N, 200)], RED, label="归一化增益")
print("包络图:", c.save())
b = Chart(FIG / "14-levels.svg", "各段 RMS：处理前 vs 处理后", xlabel="段序号", ylabel="RMS")
b.bars(range(len(before)), before, RED, label="处理前")
b.bars(range(len(after)), after, GREEN, label="处理后")
b.hline(TARGET, BLUE, label="目标 RMS")
print("电平图:", b.save())
write_wav(AUDIO / "14-before.wav", normalize_peak(x))
write_wav(AUDIO / "14-after.wav", out)
print("分段 RMS 前: " + " ".join("%.3f" % v for v in before))
print("分段 RMS 后: " + " ".join("%.3f" % v for v in after))
print("LUFS近似 %.1f -> %.1f | 增益 %.2f~%.2f | 钳位 %d | SAMPLE_RATE=%d" %
      (lufs_approx(x), lufs_approx(out), min(g), max(g), clipped, SAMPLE_RATE))""",
      figs=[("fig/14-agc.svg", "输入包络与增益轨迹"),
            ("fig/14-levels.svg", "各段处理前后 RMS 对照")],
      audio=[("audio/14-before.wav", "强弱交替的输入，需要手动调音量"),
             ("audio/14-after.wav", "AGC 输出：整体等响，注意弱段噪声被抬起")],
      steps="试听两个 WAV，观察处理后各段 RMS 是否收敛到 TARGET。",
      expect="处理后各段 RMS 明显更接近目标值；增益在电平跳变处快速下降、缓慢回升。"
             "<strong>弱段的底噪被一起放大，这就是增益泵浦</strong>；输出峰值被限幅约束。",
      tweak="把 ATTACK 与 RELEASE 对调，观察增益过冲与削波样本数上升。")],
  commands=[shell("用 ffmpeg 做电平与响度核对",
                  "ffmpeg -hide_banner -i out.wav -af volumedetect -f null - 2>&1 | grep mean_volume",
                  "volumedetect 给出 mean_volume / max_volume；更完整的响度测量用 ebur128，"
                  "动态归一化用 dynaudnorm、语音归一化用 speechnorm，均应以本机 "
                  "`ffmpeg -filters` 与 https://ffmpeg.org/ffmpeg-filters.html 为准。"),
            shell("用 ffmpeg 做一次 EBU R128 响度归一化",
                  "ffmpeg -hide_banner -i out.wav -af loudnorm=I=-23:TP=-2:LRA=7 norm.wav",
                  "loudnorm 的目标响度 I、真峰值 TP、响度范围 LRA 与 EBU R128 / ITU-R BS.1770 对应；"
                  "商业链路常用 two-pass，参数以官方文档为准。")],
  highlights=[("wiki-agc", "AGC 环路结构与时间常数的经典定义"),
              ("ffmpeg-loudnorm", "EBU R128 响度归一化的命令行实现"),
              ("ebu-r128", "-23 LUFS 目标与 True Peak 上限的规范"),
              ("ffmpeg-alimiter", "AGC 之后的真峰值保护")],
  analogy="AGC 是带状态的比例控制器：<code>g = target/measured</code>，"
          "攻击/释放是两个不同的低通系数，与限流器、自动扩缩容同属反馈环路。",
  bridge="{{ch:12}} 与 {{ch:13}} 改的是频谱内容，本章只改整体尺度；"
         "{{ch:16}} 用定量实验说明它必须排在最后，{{ch:25}} 讨论可学习的增益律。",
  pitfalls=["把 AGC 放在 AEC 之前，破坏参考与回声的线性关系。",
            "增益上升过快，静音段底噪被抬起形成泵浦。",
            "用硬削波代替限幅，引入明显谐波失真。",
            "AGC 后不做尺度对齐就报告 SNR 提升。"],
  exercises=["推导一阶包络器的时间常数与系数 a 的关系。",
             "解释为什么「增益下降快、上升慢」而非相反。",
             "设计一个 VAD 冻结增益的策略，并说明它带来的新风险。"],
  further=["{{ch:03}} 尺度对齐；{{ch:16}} 级联顺序；{{ch:25}} 神经增益控制。"]),

# ==================================================================== 15
C("15", "p3", "part3/15-beamforming", "麦克风阵列与波束形成：从 delay-and-sum 到 MVDR",
  "多一路空间信息，就能在频域处理之前先把方向性的干扰压掉。",
  hours="3 学时",
  goals=["能写出均匀线阵的到达时间差 TDOA 公式。",
         "能实现 delay-and-sum 波束形成并画出指向性曲线。",
         "能说明空间混叠、近场与通道失配对阵列的限制。",
         "能解释波束形成在 3A 链路中的位置与代价。"],
  points=["均匀线阵 ULA", "到达时间差 TDOA", "远场假设", "delay-and-sum",
          "指向性图", "空间混叠", "MVDR 与自适应波束", "阵列前置与 AEC"],
  sections=[
      S("15.1", "多一只麦克风，就多一个维度",
        eq("τ_m(θ) = m·d·sin(θ)/c　，y_m[n] = s[n − τ_m(θ₀)] + u[n − τ_m(θ_u)] + v_m[n]"),
        p("均匀线阵相邻麦克风间距为 <code>d</code>、声速 <code>c</code>，"
          "来自角度 <code>θ</code> 的平面波在相邻通道之间差 <code>τ</code> 秒。"
          "<strong>delay-and-sum</strong> 按目标方向把各通道重新对齐再求平均："
          "目标方向相干叠加，其它方向因相位不一致而部分抵消。"),
        table(["概念", "公式 / 条件", "工程含义"], [
            ["TDOA", "τ = d·sinθ/c", "θ=0 时各通道无延迟，±90° 时最大"],
            ["空间混叠", "d < c/(2·f_max)", "高频时 d 过大会出现多个指向峰"],
            ["阵增益", "白噪声下约 10log₁₀M dB", "M 路非相干噪声平均后功率降为 1/M"],
            ["近场", "声源距离 < 2d²/λ", "平面波假设失效，需球面波模型"],
        ], ["16%", "38%", "46%"])),
      S("15.2", "固定波束、自适应波束与 3A 的位置",
        p("delay-and-sum 权值与数据无关，稳定、零训练、可解释；"
          "<strong>MVDR</strong> 在「目标方向无失真」约束下最小化输出功率，"
          "需估计多通道协方差矩阵并求逆，能挖出深零陷，但对导向矢量误差与通道失配敏感。"),
        ul(["<strong>位置</strong>：通常放在 AEC 之前减少进入链路的干扰；也有人放在 AEC 之后，"
            "避免自适应滤波器去追一个随波束变化的回声路径。",
            "<strong>代价</strong>：多通道采集、校准、同步与额外算力，端侧未必负担得起。",
            "<strong>互补性</strong>：阵列解决「空间可分」，3A 解决「时间与频率可分」，二者不互相替代。"]),
        note("教学边界", "实验用整数样本延迟与完全校准的合成阵列，"
             "未模拟分数延迟滤波器、通道增益失配与真实房间混响；"
             "真实系统请用 pyroomacoustics 的镜像源模型生成多通道 RIR。")),
  ],
  demos=[mk_demo(
      file="code/15-beamforming.py",
      title="实验 15-1 · 均匀线阵 delay-and-sum 与指向性扫描",
      doc="合成 4 通道阵列信号，按角度扫描固定波束，测量干扰抑制并输出可试听样本。",
      params="""N = 8000
MICS = 4
SPACING = 0.10             # 麦克风间距（米）
SPEED = 340.0              # 声速 m/s
INTERFERER_ANGLE = 65      # 干扰源角度（度）
ANGLES = tuple(range(-80, 81, 20))""",
      body="""rng = random.Random(7)
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
      (best, seg_snr_db(target, scale_align(mics[0], target)), max(scores), SAMPLE_RATE, MICS))""",
      figs=[("fig/15-directivity.svg", "各扫描角的分段 SNR 指向性曲线"),
            ("fig/15-waveform.svg", "单通道与波束输出波形对照")],
      audio=[("audio/15-single.wav", "单通道：目标与单音干扰混在一起"),
             ("audio/15-beam.wav", "波束输出：方向性干扰被部分抵消")],
      steps="对照指向性曲线的峰值角度与真实目标方向 0°，试听两个 WAV。",
      expect="分段 SNR 在目标方向附近出现峰值，说明对齐后目标相干叠加、干扰被部分抵消。"
             "本实验使用整数延迟与理想校准，真实阵列还需处理分数延迟与通道失配。",
      tweak="把 SPACING 改成 0.02（阵孔径变小），指向性曲线会明显变钝。")],
  commands=[shell("用 ffmpeg 检查多通道文件的通道布局",
                  "ffmpeg -hide_banner -i array.wav -af astats=metadata=1 -f null - 2>&1 | grep RMS",
                  "astats 可逐通道给出 RMS 与峰值统计，用于核对多通道采集是否失衡；"
                  "滤镜可用性以本机 `ffmpeg -filters` 与 https://ffmpeg.org/ffmpeg-filters.html 为准。")],
  highlights=[("wiki-beamforming", "delay-and-sum 与 MVDR 的标准定义"),
              ("pyroomacoustics", "生成更真实的多通道 RIR 与阵列仿真"),
              ("ccrma", "阵列信号处理与延迟线讲义"),
              ("speechbrain", "神经波束形成与多通道增强配方")],
  analogy="波束形成就是「按 key 对齐后做 group-by 求平均」："
          "对齐正确的那一路内容相干叠加，未对齐的项在平均中互相抵消。",
  bridge="上卷三大引擎已齐备；{{ch:16}} 讨论它们在链路里的排列顺序，"
         "{{ch:17}} 给出可复现的命令行工具链，下卷 {{ch:26}} 会把阵列与网络合并建模。",
  pitfalls=["忽略 d 与最高频率的关系，高频出现栅瓣与空间混叠。",
            "用整数延迟近似分数延迟，宽带信号下指向性失真。",
            "把波束放在 AEC 之后却不同步更新参考路径，回声模型被破坏。",
            "忽略通道增益/相位失配，MVDR 的零陷落在错误方向。"],
  exercises=["推导 d=0.10 m、16 kHz 下 65° 入射的相邻通道延迟（样本）。",
             "解释为什么 M 路非相干噪声平均后功率降为 1/M。",
             "列举两种会造成 MVDR 导向矢量失配的现实因素。"],
  further=["{{ch:16}} 级联顺序；{{ch:26}} 联合 3A；{{ch:20}} 多通道数据合成。"]),

# ==================================================================== 16
C("16", "p3", "part3/16-cascade-order", "3A 级联顺序与模块间相互干扰",
  "三个模块各自都对，串错顺序却会全盘失效；本章把「顺序」变成可测量的量。",
  hours="3 学时",
  goals=["能写出 AEC / ANS / AGC 三者的输入输出契约与不变量。",
         "能定量说明 AGC 前置为什么会破坏自适应滤波的线性假设。",
         "能定性说明 ANS 前置为什么会把回声谱也一起改掉。",
         "能给出推荐链路及例外条件下的调整方案。"],
  points=["模块接口契约", "参考信号不变量", "AEC → ANS → AGC", "AGC 前置的危害",
          "ANS 前置的危害", "增益与尺度对齐", "混合系统顺序", "端到端可观测性"],
  sections=[
      S("16.1", "顺序不是风格，是不变量",
        eq("y[n] = d[n] + h*x[n] + v[n]　；AEC 要求 y 与 x 之间保持同一个 h"),
        p("AEC 是唯一<strong>有参考信号</strong>的模块，也是唯一依赖「y 与 x 由同一条线性路径联系」的模块。"
          "任何在 AEC 之前对 <code>y</code> 做的非线性或时变处理，都会让这个不变量失效："
          "AGC 改变整体增益，ANS 逐频率箱改变谱形状，二者都等价于把 <code>h</code> 换成了随时间变化的路径。"),
        table(["排列", "破坏的不变量", "可观测后果"], [
            ["AEC → ANS → AGC", "无", "ERLE 高、噪声被压、输出等响"],
            ["AGC → AEC → ANS", "y 与 x 的增益比", "线性抵消不彻底，ERLE 塌陷"],
            ["ANS → AEC → AGC", "y 的谱形状", "预测回声与实际谱不匹配，残余回声上升"],
            ["ANS → AGC → AEC", "增益 + 谱形状", "两项误差叠加，最差"],
        ], ["26%", "30%", "44%"])),
      S("16.2", "推荐链路与两个例外",
        p("教科书顺序是 <code>时延对齐 → AEC 线性级 → 残余回声抑制 → ANS → AGC → 限幅</code>。"
          "WebRTC 的 <code>audio_processing</code> 大体遵循这一顺序，"
          "但把回声/噪声的统计估计与后滤波交织在一起，形成更紧凑的流水线。"),
        ul(["<strong>例外一</strong>：麦克风阵列波束形成若放在 AEC 之前，"
            "必须让参考信号经过同样的波束或重新辨识路径（见 {{ch:15}}）。",
            "<strong>例外二</strong>：神经联合模型（{{ch:26}}）把多个模块合成一个网络，"
            "此时「顺序」变成网络内部的层顺序，但因果性与参考信号不变量仍然成立。",
            "<strong>评测提醒</strong>：AGC 在最后，所以任何质量指标都要先做尺度对齐（{{ch:03}}）。"]),
        note("失效可隔离", "把链路拆成可单独旁路的模块，是定位线上问题的前提："
             "漏回声查 AEC、音乐噪声查 ANS、忽大忽小查 AGC。"
             "端到端黑箱模型在工程上更难做这种归因。")),
  ],
  demos=[mk_demo(
      file="code/16-cascade-order.py",
      title="实验 16-1 · 三种级联排列的 ERLE 与分段 SNR 对照",
      doc="在同一条合成链路上交换 3A 顺序；线性 AEC 用已知 h 加 3% 受控泄漏，量化顺序错误造成的指标塌陷。",
      params="""N = 8000
N_FFT, HOP = 256, 128
ECHO_GAIN = 1.5
NOISE_AMP = 0.020
LEAK = 0.03              # 故意留 3% 线性泄漏，避免「理想相减」得到不真实的无限 ERLE
TARGET = 0.16""",
      body="""rng = random.Random(7)
far = synthetic_speech(rng, N)
near = synthetic_speech(rng, N)
h = rir(rng, 128, decay=0.006)
echo = [ECHO_GAIN * v for v in fft_convolve(far, h)[:N]]
noise = white_noise(rng, N, NOISE_AMP)
clean = [0.5 * v for v in near]
y = [clean[i] + echo[i] + noise[i] for i in range(N)]
nf = stft(noise, N_FFT, HOP)[:8]
nmag = [sum(math.hypot(re[k], im[k]) for re, im in nf) / len(nf) for k in range(N_FFT)]

def aec(sig):
    return [sig[i] - (1.0 - LEAK) * echo[i] for i in range(N)]
def ans(sig):
    frames = stft(sig, N_FFT, HOP)
    for re, im in frames:
        for k in range(N_FFT):
            g = max(0.15, 1.0 - 1.2 * nmag[k] / (math.hypot(re[k], im[k]) + 1e-9))
            re[k] *= g
            im[k] *= g
    return istft(frames, N_FFT, HOP, N)
def agc(sig):
    g = min(6.0, TARGET / (rms(sig) + 1e-6))
    return clip([v * g for v in sig])

a1, a2, a3 = aec(y), None, None
a2, a3 = ans(a1), None
a3 = agc(a2)
b0 = agc(y)
b1, b2 = aec(b0), None
b2 = ans(b1)
c1 = ans(y)
c2 = aec(c1)
c3 = agc(c2)
chains = [("AEC-ANS-AGC", a1, a3), ("AGC-AEC-ANS", b1, b2), ("ANS-AEC-AGC", c2, c3)]
erles, snrs = [], []
for _name, stage1, final in chains:
    residual = [stage1[i] - clean[i] - noise[i] for i in range(N)]
    erles.append(erle_db(echo, residual))
    snrs.append(seg_snr_db(clean, scale_align(final, clean)))
c = Chart(FIG / "16-order.svg", "三种级联排列的 ERLE 与分段 SNR",
          xlabel="排列", ylabel="dB", xticks=[(i, n) for i, (n, _a, _b) in enumerate(chains)])
c.bars(range(3), erles, BLUE, label="ERLE (dB)")
c.bars(range(3), snrs, GREEN, label="分段 SNR (dB)")
print("顺序图:", c.save())
w = Chart(FIG / "16-waveform.svg", "正确顺序与 AGC 前置的输出波形（前 1200 样本）",
          xlabel="样本", ylabel="幅度")
w.line(range(1200), a3[:1200], GREEN, label="AEC-ANS-AGC")
w.line(range(1200), b2[:1200], RED, label="AGC-AEC-ANS")
print("波形图:", w.save())
write_wav(AUDIO / "16-correct.wav", normalize_peak(a3))
write_wav(AUDIO / "16-wrong.wav", normalize_peak(b2))
for (name, _a, _b), e, s in zip(chains, erles, snrs):
    print("%s: ERLE=%.2f dB segSNR=%.2f dB" % (name, e, s))
print("RMS 输入=%.4f 正确输出=%.4f | SAMPLE_RATE=%d N_FFT=%d" %
      (rms(y), rms(a3), SAMPLE_RATE, N_FFT))""",
      figs=[("fig/16-order.svg", "三种排列的 ERLE 与分段 SNR"),
            ("fig/16-waveform.svg", "正确与错误顺序的输出波形")],
      audio=[("audio/16-correct.wav", "推荐顺序的输出"),
             ("audio/16-wrong.wav", "AGC 前置：仍能听到明显残余回声")],
      steps="比较三条柱形；试听两个 WAV，注意错误顺序里残留的远端语音。",
      expect="AGC 或 ANS 前置时，y 与参考回声之间的线性/谱关系被改变，"
             "AEC 减去的是「未被同样处理过的回声」，ERLE 明显低于推荐顺序。"
             "<strong>这就是顺序必须作为架构约束写进接口文档的原因。</strong>",
      tweak="把 ECHO_GAIN 调到 0.2，指标差距会缩小——说明越强的回声越依赖正确顺序。")],
  commands=[shell("用 ffmpeg 滤镜链复现一次「顺序」实验",
                  "ffmpeg -hide_banner -i mic.wav -af afftdn,loudnorm out.wav",
                  "-af 中滤镜按书写顺序串接，交换顺序即可对比；"
                  "注意 ffmpeg 没有内置完整 AEC，这里只演示 ANS 与增益的先后。"
                  "滤镜可用性以本机 `ffmpeg -filters` 与 https://ffmpeg.org/ffmpeg-filters.html 为准。")],
  highlights=[("webrtc-src", "工业 3A 流水线的模块排列参考"),
              ("ffmpeg-afreqshift", "-af 滤镜链的顺序语义"),
              ("wiki-aec", "参考信号与线性路径不变量"),
              ("rfc3550", "端到端延迟预算里各模块的排队位置")],
  analogy="级联顺序是流水线里「谁先读到未经修改的原始数据」的问题："
          "AEC 是唯一需要原始参考的消费者，因此必须排在任何会改写数据的算子之前。",
  bridge="{{ch:09}}～{{ch:14}} 分别实现三个引擎，本章把它们按不变量串起来；"
         "{{ch:17}} 给出命令行工具链，{{ch:18}} 对整条上卷链路做综合验收。",
  pitfalls=["把 AGC 放在 AEC 之前，破坏参考信号与回声的线性关系。",
            "在 AEC 之前做谱减，把回声谱一起改掉。",
            "波束形成放在 AEC 之前却不同步处理参考信号。",
            "顺序调对后就不再做尺度对齐评测。"],
  exercises=["画出三条链路并标出每条链路破坏的不变量。",
             "解释为什么实验里 AGC 前置会同时拉低 ERLE 与分段 SNR。",
             "为联合神经 3A 模型重新表述「顺序」这一约束。"],
  further=["{{ch:17}} 工具链；{{ch:18}} 综合评测；{{ch:26}} 联合建模。"]),

# ==================================================================== 17
C("17", "p3", "part3/17-toolchain", "ffmpeg / WebRTC / SpeexDSP 工具链实操",
  "把书里的公式映射到能在本机敲的命令与能读的源码目录。",
  hours="3 学时",
  goals=["能用 `ffmpeg -filters` 自查本机支持的音频滤镜及版本。",
         "能把 3A 的三类任务映射到具体 ffmpeg 滤镜与参数。",
         "能定位 WebRTC audio_processing 与 SpeexDSP 的源码目录。",
         "能说明离线滤镜链与实时 3A 链路的本质差别。"],
  points=["滤镜自查与版本", "afftdn / anlmdn / arnndn", "loudnorm / dynaudnorm / speechnorm",
          "ebur128 / astats / volumedetect", "WebRTC audio_processing", "AEC3 源码目录",
          "SpeexDSP 接口", "离线与实时链路差异"],
  sections=[
      S("17.1", "先自查，再谈版本",
        p("用户常问「ffmpeg 某版本里有没有某个能力」。可靠的回答方式不是背版本号，"
          "而是给一条<strong>自查命令</strong>：编译选项不同，同一版本号支持的滤镜也可能不同。"
          "本书所有命令都遵循「先用本机输出确认、再查官方文档」的口径。"),
        table(["任务", "常用滤镜 / 入口", "备注"], [
            ["噪声抑制", "afftdn、anlmdn、arnndn", "arnndn 需自备 RNNoise 训练出的模型文件"],
            ["增益 / 响度", "dynaudnorm、speechnorm、loudnorm、acompressor、alimiter",
             "loudnorm 对应 EBU R128；alimiter 做真峰值保护"],
            ["测量", "volumedetect、astats、ebur128、silencedetect", "ebur128 输出 I / LRA / True Peak"],
            ["造测试数据", "aecho、aresample、anoisesrc", "aecho 可叠加延迟衰减副本"],
            ["工业 3A", "WebRTC modules/audio_processing", "AEC3 / NS / AGC2 的参考实现"],
        ], ["16%", "44%", "40%"])),
      S("17.2", "离线滤镜链 ≠ 实时 3A",
        eq("ffmpeg: 文件 → -af 滤镜链 → 文件　；WebRTC: 10 ms 帧 → 有状态处理 → 10 ms 帧"),
        ul(["<strong>参考信号</strong>：ffmpeg 的滤镜链没有 AEC 所需的第二路输入；"
            "真正做回声消除要用带参考的实现（WebRTC AEC3、SpeexDSP）。",
            "<strong>状态</strong>：实时模块必须逐帧携带状态（滤波器权重、噪声功率、增益包络），"
            "离线滤镜可以读全文件做 two-pass。",
            "<strong>延迟</strong>：实时链路按 10 ms 帧预算，任何「看未来」的归一化都要删掉或改成因果版本。"]),
        note("版本口径", "ffmpeg 各滤镜的引入版本、参数名与默认值可能随版本变化。"
             "请以 <code>ffmpeg -version</code>、<code>ffmpeg -filters</code>、"
             "<code>ffmpeg -h filter=NAME</code> 与 https://ffmpeg.org/ffmpeg-filters.html 为准；"
             "本书与这些项目无从属关系，也不构成产品推荐。")),
  ],
  demos=[mk_demo(
      file="code/17-toolchain.py",
      title="实验 17-1 · 用 Python 复刻一条离线滤镜链的电平报告",
      doc="模拟 volumedetect/astats → dynaudnorm → loudnorm 三阶段，打印可核对的电平报告。",
      params="""N = 8000
WIN = 800
TARGET_LUFS = -23.0
MAX_GAIN = 4.0
MAX_DYN_GAIN = 80.0     # 动态归一化增益上限：太小则弱段抬不动
ATK, REL = 0.20, 0.20    # 增益平滑的攻击/释放系数""",
      body="""rng = random.Random(7)
base = synthetic_speech(rng, N)
level = [0.25 if i < N // 2 else 1.0 for i in range(N)]
x = [0.35 * base[i] * level[i] for i in range(N)]
peak = max(abs(v) for v in x)
mean_db = 20 * math.log10(rms(x) + 1e-12)
peak_db = 20 * math.log10(peak + 1e-12)
blocks = [rms(x[s:s + WIN]) for s in range(0, N, WIN)]
g_block = [min(MAX_DYN_GAIN, 0.16 / (b + 1e-6)) for b in blocks]
raw_g = [g_block[min(i // WIN, len(g_block) - 1)] for i in range(N)]
g = smooth(raw_g, ATK, REL)
dyn = clip([x[i] * g[i] for i in range(N)])
l0 = lufs_approx(dyn)
gain = min(MAX_GAIN, 10 ** ((TARGET_LUFS - l0) / 20.0))
norm = clip([v * gain for v in dyn])
l1 = lufs_approx(norm)
blocks_after = [rms(norm[s:s + WIN]) for s in range(0, N, WIN)]
c = Chart(FIG / "17-levels.svg", "逐块 RMS：输入 / dynaudnorm 阶段 / loudnorm 阶段",
          xlabel="块序号 / 800 样本", ylabel="RMS")
c.line(range(len(blocks)), blocks, "#9aa6b2", label="输入")
c.line(range(len(blocks)), [rms(dyn[s:s + WIN]) for s in range(0, N, WIN)], BLUE, label="动态归一化")
c.line(range(len(blocks_after)), blocks_after, GREEN, label="响度归一化")
print("电平图:", c.save())
b = Chart(FIG / "17-gain.svg", "动态归一化阶段的增益轨迹", xlabel="样本 / 200", ylabel="增益")
b.line(range(0, N, 200), [g[i] for i in range(0, N, 200)], RED, label="g[n]")
print("增益图:", b.save())
write_wav(AUDIO / "17-input.wav", normalize_peak(x))
write_wav(AUDIO / "17-normalized.wav", norm)
print("volumedetect 口径: mean_volume=%.2f dB max_volume=%.2f dB" % (mean_db, peak_db))
print("astats 口径: 分块 RMS 前 %.4f~%.4f (%.1f×) 后 %.4f~%.4f (%.1f×)" %
      (min(blocks), max(blocks), max(blocks) / max(min(blocks), 1e-9),
       min(blocks_after), max(blocks_after), max(blocks_after) / max(min(blocks_after), 1e-9)))
print("ebur128 口径(教学近似): LUFS %.2f -> %.2f | 二遍增益=%.3f | SAMPLE_RATE=%d" %
      (l0, l1, gain, SAMPLE_RATE))""",
      figs=[("fig/17-levels.svg", "三阶段逐块 RMS 对照"),
            ("fig/17-gain.svg", "动态归一化阶段的增益轨迹")],
      audio=[("audio/17-input.wav", "前半轻后半响的输入"),
             ("audio/17-normalized.wav", "两级归一化后的输出")],
      steps="对照打印的 mean_volume / max_volume / LUFS 与图上曲线；把结果作为 ffmpeg 命令的预期值。",
      expect="动态归一化先压平块间电平，响度归一化再整体平移到目标响度附近。"
             "<strong>本书 lufs_approx() 只是教学近似，不能代替合规的 ebur128 测量。</strong>",
      tweak="把 TARGET_LUFS 改成 -16，观察二遍增益与最终电平如何变化。")],
  commands=[shell("自查本机 ffmpeg 版本与 3A 相关滤镜",
                  "ffmpeg -hide_banner -version | head -3 && ffmpeg -hide_banner -filters | grep -E 'afftdn|anlmdn|arnndn|loudnorm|dynaudnorm|speechnorm|ebur128|astats|volumedetect|aecho|aresample|acompressor|alimiter'",
                  "是否列出某滤镜取决于本机版本与编译选项；本书不假定任何特定版本。"
                  "参数细节用 `ffmpeg -h filter=NAME`，权威说明见 https://ffmpeg.org/ffmpeg-filters.html 。"),
            shell("离线三阶段滤镜链（对照实验 17-1 的 Python 版本）",
                  "ffmpeg -hide_banner -i input.wav -af volumedetect -f null - 2>&1 | grep -E 'mean_volume|max_volume' && ffmpeg -hide_banner -i input.wav -af dynaudnorm,ebur128=peak=true -f null - 2>&1 | tail -12",
                  "第一条给电平报告，第二条做动态归一化并输出响度测量；"
                  "滤镜可用性以本机 `ffmpeg -filters` 与官方 Filters 文档为准。"),
            shell("定位 WebRTC 的 3A 源码入口",
                  "git clone --depth 1 https://webrtc.googlesource.com/src webrtc-src && ls webrtc-src/modules/audio_processing/",
                  "audio_processing 下含 aec3、ns、agc2 等子目录；"
                  "也可直接在 https://webrtc.googlesource.com/src/+/refs/heads/main/modules/audio_processing/ 在线浏览。")],
  highlights=[("ffmpeg-filters", "全部音频滤镜的权威说明页"),
              ("ffmpeg-arnndn", "加载 RNNoise 模型的神经降噪滤镜"),
              ("webrtc-src", "AEC3 / NS / AGC2 的工业参考实现"),
              ("speexdsp", "最易读的经典 AEC / 预处理源码")],
  analogy="ffmpeg 的 <code>-af</code> 是一条 shell 管道，WebRTC 是一个有状态的流处理器："
          "前者处理文件，后者处理 10 ms 一帧的无限流，二者的数据结构与延迟约束完全不同。",
  bridge="{{ch:16}} 定下链路顺序，本章把每个模块落到可敲的命令与可读的源码；"
         "{{ch:18}} 用统一指标对整条上卷链路做综合验收。",
  pitfalls=["照抄网上命令，不先查本机是否编译了对应滤镜。",
            "把 ffmpeg 的离线归一化结果当成实时 AGC 可用。",
            "以为 ffmpeg 内置完整 AEC（它需要远端参考，不是单路滤镜）。",
            "用 lufs_approx 之类的近似值做播出合规判定。"],
  exercises=["写出三条自查命令，判断本机能否运行 arnndn 与 loudnorm。",
             "解释为什么 AEC 不能写成单输入 -af 滤镜。",
             "把实验 17-1 的三阶段映射到具体 ffmpeg 滤镜名。"],
  further=["{{ch:18}} 上卷综合评测；{{ch:23}} RNNoise 与 arnndn；{{ch:28}} 实时延迟预算。"]),

]
