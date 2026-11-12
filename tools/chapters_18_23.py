#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 18～23 章：上卷综合评测与下卷学习基础（掩码、数据、骨架、相位、神经降噪）。"""
from __future__ import annotations

from book_schema import C, eq, table
from chapter_kit import mk_demo, shell, p, ul, ol, note, warn, sec


def S(num, title, *parts):
    """构造 (编号, 标题, HTML) 原理小节。"""
    return (num, title, sec(*parts))


CH = [

# ==================================================================== 18
C("18", "p3", "part3/18-classic-eval", "上卷综合实验：完整传统 3A 链路与评测",
  "把前十余章的模块装进一条链路，用统一的场景矩阵与指标表做一次验收。",
  hours="4 学时",
  goals=["能把 AEC / ANS / AGC 串成一条可运行的完整链路。",
         "能设计覆盖单讲、双讲、强噪声与路径突变的场景矩阵。",
         "能同时报失真类、回声类与响度类指标，并解释彼此冲突。",
         "能说明上卷方法的失效边界以及下卷要替换的环节。"],
  points=["链路规格", "场景矩阵", "ERLE 与双讲", "分段 SNR 与 SI-SDR",
          "响度与真峰值", "路径突变与重收敛", "上卷能力上界", "下卷接口"],
  sections=[
      S("18.1", "一条链路，一份规格说明书",
        eq("x[n] → h → 回声　；y[n] = d[n] + e[n] + v[n]　；ŷ = AGC(ANS(RES(AEC(y, x)))) → 编码器"),
        p("验收前先把接口写死：所有模块都在 16 kHz、10 ms 帧上工作；"
          "AEC 用未经任何加工的 <code>x</code>；ANS 只吃误差信号；AGC 只改整体尺度；"
          "评测前对输出做尺度对齐。<strong>接口不变量比某个模块的参数更重要</strong>。"),
        table(["阶段", "输入", "输出", "验收指标"], [
            ["线性 AEC", "y, x", "误差信号 e", "ERLE、双讲透明度"],
            ["残余抑制", "e, 预测回声谱", "z", "残余 ERLE、语音失真"],
            ["ANS", "z", "增强语音", "segSNR、STOI、DNSMOS"],
            ["AGC / 限幅", "增强语音", "送编码信号", "LUFS、True Peak、增益泵浦"],
        ], ["18%", "22%", "20%", "40%"])),
      S("18.2", "场景矩阵：一张表暴露所有短板",
        ul(["<strong>远端单讲</strong>：近端安静，ERLE 最好测，也最容易刷出漂亮数字。",
            "<strong>双讲</strong>：近端与远端同时说话，考察系数冻结与残余抑制是否误伤近端。",
            "<strong>强噪声 / 非平稳噪声</strong>：考察噪声功率跟踪，固定谱减会明显退化。",
            "<strong>路径突变</strong>：中途换一条 RIR，考察重收敛速度；线性模型在切换瞬间必然留残差。",
            "<strong>非线性回声</strong>：扬声器削波，线性 AEC 无能为力，只能靠残余抑制或神经后处理。"]),
        note("上卷的结论", "模型驱动方法在「线性、平稳、可辨识」条件下几乎最优：低算力、低延迟、可证明收敛。"
             "但它把非线性失真、强混响与分布外噪声都推给了残余抑制模块——"
             "这正是下卷 {{ch:19}} 起把估计器换成可学习函数的动机。")),
  ],
  demos=[mk_demo(
      file="code/18-classic-eval.py",
      title="实验 18-1 · 四类场景下的完整传统 3A 链路指标矩阵",
      doc="在单讲、双讲、强噪声、路径突变四种场景下运行同一条链路，输出指标热力图。",
      params="""N = 8000
N_FFT, HOP = 256, 128
LEAK = 0.03
NOISE_AMP = 0.020
TARGET = 0.16""",
      body="""rng = random.Random(7)
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
print("SAMPLE_RATE=%d | 场景数=%d | 链路: AEC -> ANS -> AGC" % (SAMPLE_RATE, len(SCENARIOS)))""",
      figs=[("fig/18-scenarios.svg", "四类场景处理前后分段 SNR"),
            ("fig/18-matrix.svg", "完整指标矩阵热力图")],
      audio=[("audio/18-doubletalk-mic.wav", "双讲场景的麦克风信号"),
             ("audio/18-doubletalk-out.wav", "双讲场景的 3A 输出")],
      steps="对照四类场景的 ERLE 与 SI-SDR；试听双讲场景，注意近端语音是否被误伤。",
      expect="单讲基准 ERLE 最高；强双讲与强噪声因为自适应更新受扰、噪声估计变差而回落；"
             "路径突变时线性滤波器仍用旧路径抵消，ERLE 与 SI-SDR 塌陷最明显。"
             "<strong>单讲条件下的高分不能代表真实通话质量</strong>。",
      tweak="把 LEAK 改成 0.15，观察四类场景的 ERLE 同时下降。")],
  commands=[shell("用 ffmpeg 对输出做一次综合电平验收",
                  "ffmpeg -hide_banner -i out.wav -af astats=metadata=1:reset=0 -f null - 2>&1 | grep -E 'RMS|Peak'",
                  "astats 的 RMS / Peak 与本书 LUFS 近似相互印证；合规测量请用 ebur128，"
                  "以本机 `ffmpeg -filters` 与 https://ffmpeg.org/ffmpeg-filters.html 为准。")],
  highlights=[("itu-p862", "有参考感知质量的经典标准"),
              ("ffmpeg-ebur128", "响度与真峰值的命令行测量"),
              ("webrtc", "工业 3A 链路的整体参照"),
              ("dns-challenge", "更大规模评测集的构造方式")],
  analogy="综合评测就是一次端到端集成测试：单模块单元测试全绿，"
          "不代表双讲、路径突变这些「集成场景」能过。",
  bridge="上卷到此收束。{{ch:19}} 起把同一条链路里的增益估计器换成可学习函数，"
         "但接口、因果约束与这张场景矩阵完全不变。",
  pitfalls=["只报远端单讲的 ERLE 就宣称系统达标。",
            "场景之间共用随机种子却以为互相独立。",
            "用测试集挑完阈值再报告该测试集分数。",
            "把合成信号上的指标量级当成产品性能数据。"],
  exercises=["为实时通话 App 设计至少 6 个场景的评测矩阵与验收阈值。",
             "解释为什么路径突变场景的 ERLE 会低于远端单讲。",
             "指出上卷方法最难处理的三类退化，并对应到下卷章节。"],
  further=["{{ch:19}} 时频掩码；{{ch:30}} 评测陷阱；{{ch:31}} 结课项目。"]),

# ==================================================================== 19
C("19", "p4", "part4/19-tf-mask", "时频掩码：IBM / IRM / CRM 与监督学习形式化",
  "下卷的入口：把「算一个增益」改写成「学一个函数」，链路结构一点没变。",
  hours="3 学时",
  goals=["能把 3A 的增益估计写成监督学习的输入—输出映射。",
         "能推导并计算 IBM、IRM 等理想掩码，说明它们的 oracle 性质。",
         "能量化 oracle 掩码的性能上界与可学习性之间的差距。",
         "能解释为什么掩码学习仍需遵守因果性与 WOLA 约束。"],
  points=["监督学习形式化", "STFT 特征与标签", "理想二值掩码 IBM", "理想比值掩码 IRM",
          "复数掩码 CRM", "oracle 上界", "相位保持不变", "掩码与谱减的统一"],
  sections=[
      S("19.1", "同一个位置，换一种求法",
        eq("传统: G[t,k] = f_手工(P̂_n, P̂_s)　；学习: G[t,k] = f_θ(Y[t−τ:t+τ, ·])"),
        p("把 {{ch:12}} 的谱减、{{ch:13}} 的 Wiener 增益统一记成 <code>G[t,k]</code>，"
          "上卷用物理假设手工推导 <code>f</code>，下卷用数据拟合 <code>f_θ</code>。"
          "<strong>输入、输出、指标、链路位置全都不变，变的只是 f 从公式变成网络</strong>。"),
        table(["掩码", "定义", "标签可得吗", "特点"], [
            ["IBM", "1 if |S| > |N| else 0", "需要干净/噪声分离", "二值，硬判决，易产生音乐噪声"],
            ["IRM", "|S| / (|S| + |N|)", "需要干净/噪声分离", "软增益，最常作为训练目标"],
            ["PSM", "|S|·cos(Δφ) / |Y|", "需要相位差", "开始利用相位信息"],
            ["CRM", "S / Y（复数除法）", "需要复数干净谱", "幅度与相位一起估计，见 {{ch:22}}"],
        ], ["12%", "34%", "24%", "30%"])),
      S("19.2", "oracle 不是模型，是上界",
        p("上述掩码都要在训练时拿到干净谱，因此只能作为<strong>oracle 上界</strong>或训练标签。"
          "在测试时网络只能看到 <code>Y</code>，性能必然低于 oracle。"
          "把 oracle 与可部署模型的差距单独报出来，是论文与工程报告里最有用的一行数字。"),
        ul(["<strong>特征</strong>：对数幅度谱、邻近帧上下文、远端参考谱（AEC 场景）。",
            "<strong>损失</strong>：掩码 MSE、SI-SNR、谱幅度距离或感知加权组合（{{ch:26}}）。",
            "<strong>约束</strong>：因果模型只能用 <code>t−τ:t</code>；用了未来帧就是离线结果，不能叫实时。",
            "<strong>重建</strong>：掩码作用在 STFT 上，仍要靠 WOLA 无失真重建（{{ch:02}}）。"]),
        note("别把 oracle 当成绩", "报告里若出现「IRM 提升了 20 dB」，务必注明它是 oracle。"
             "常见错误是把 oracle 结果与可部署模型放在同一张表里比较而不加标注。")),
  ],
  demos=[mk_demo(
      file="code/19-tf-mask.py",
      title="实验 19-1 · IBM / IRM oracle 掩码的性能上界与掩码热力图",
      doc="计算理想二值掩码与理想比值掩码，量化它们的 oracle 上界并画出时频掩码。",
      params="""N = 8000
N_FFT, HOP = 256, 128
NOISE_AMP = 0.040""",
      body="""rng = random.Random(7)
clean = synthetic_speech(rng, N)
noise = white_noise(rng, N, NOISE_AMP)
noisy = [clean[i] + noise[i] for i in range(N)]
fs, fn = stft(clean, N_FFT, HOP), stft(noise, N_FFT, HOP)

def apply_mask(kind):
    frames = stft(noisy, N_FFT, HOP)
    rows = []
    for idx, (ry, iy) in enumerate(frames):
        rs, is_ = fs[idx]
        rn, in_ = fn[idx]
        gains = []
        for k in range(N_FFT):
            ms = math.hypot(rs[k], is_[k])
            mn = math.hypot(rn[k], in_[k])
            g = (1.0 if ms > mn else 0.0) if kind == "IBM" else ms / (ms + mn + 1e-9)
            ry[k] *= g
            iy[k] *= g
            gains.append(g)
        rows.append(gains[::8])
    return istft(frames, N_FFT, HOP, N), rows

ibm, _ = apply_mask("IBM")
irm, mask_rows = apply_mask("IRM")
methods = ("未处理", "IBM oracle", "IRM oracle")
signals = (noisy, ibm, irm)
s_snr = [seg_snr_db(clean, scale_align(s, clean)) for s in signals]
s_sdr = [si_sdr_db(s, clean) for s in signals]
c = Chart(FIG / "19-masks.svg", "三种情形的分段 SNR 与 SI-SDR", xlabel="方法", ylabel="dB",
          xticks=[(i, m) for i, m in enumerate(methods)])
c.bars(range(3), s_snr, BLUE, label="分段 SNR (dB)")
c.bars(range(3), s_sdr, GREEN, label="SI-SDR (dB)")
print("掩码对比图:", c.save())
mat = mask_rows[::4]
heatmap(FIG / "19-irm.svg", mat,
        ["frame%d" % (i * 4) for i in range(len(mat))],
        ["f%d" % (k * 8) for k in range(len(mat[0]))],
        title="IRM 理想掩码（降采样显示）", vmin=0.0, vmax=1.0, annotate=False)
print("掩码热力图:", str(FIG / "19-irm.svg"))
write_wav(AUDIO / "19-noisy.wav", normalize_peak(noisy))
write_wav(AUDIO / "19-irm.wav", normalize_peak(irm))
for m, a, b in zip(methods, s_snr, s_sdr):
    print("%s: segSNR=%.2f dB SI-SDR=%.2f dB" % (m, a, b))
print("IRM 相对未处理提升=%.2f dB | SAMPLE_RATE=%d N_FFT=%d HOP=%d" %
      (s_snr[2] - s_snr[0], SAMPLE_RATE, N_FFT, HOP))""",
      figs=[("fig/19-masks.svg", "未处理、IBM、IRM 的指标对照"),
            ("fig/19-irm.svg", "理想比值掩码的时频热力图")],
      audio=[("audio/19-noisy.wav", "带噪输入"),
             ("audio/19-irm.wav", "IRM oracle 输出（可部署模型的上界）")],
      steps="对照三个方法的指标；注意 IRM 需要干净谱，测试时不可能直接得到。",
      expect="两种 oracle 掩码都比未处理高约 9～10 dB；本例中硬判决 IBM 的分段 SNR 与 IRM 接近甚至略高，"
             "但 IRM 是连续增益，听感上音乐噪声更轻——<strong>客观分数接近不代表主观等价</strong>。"
             "两者都用到了测试时拿不到的干净谱，是上界而不是模型成绩；"
             "{{ch:21}} 与 {{ch:31}} 会用可训练的小模型去逼近它。",
      tweak="把 NOISE_AMP 提到 0.10，oracle 与未处理的差距会进一步拉大。")],
  commands=[shell("查看 PyTorch 语音工具箱里的 STFT / 掩码接口",
                  "python3 -c \"import torchaudio; print(torchaudio.__version__)\"",
                  "本机未必安装 torchaudio；这是进阶路径的自查命令，本书实验不依赖它。"
                  "接口说明见 https://docs.pytorch.org/audio/stable/index.html 。")],
  highlights=[("wiki-mask", "时频分析与掩码学习范式的背景"),
              ("dns-challenge", "大规模掩码/映射训练数据与基线"),
              ("rnnoise-paper", "从谱增益到可学习频带增益的工业案例"),
              ("speechbrain", "掩码估计器的开源训练配方")],
  analogy="把 <code>G[t,k]</code> 当成一张待预测的二维表：上卷写死一个函数生成它，"
          "下卷训练一个模型生成它。表的形状、下游的逐元素乘法、ISTFT 全都原封不动。",
  bridge="下卷开篇。{{ch:20}} 解决「训练数据从哪来」，{{ch:21}} 解决「用什么样的 f_θ」，"
         "{{ch:22}} 讨论相位，{{ch:23}} 回到降噪任务本身。",
  pitfalls=["把 oracle 掩码分数当成可部署模型的成绩。",
            "掩码只作用于前半频谱，破坏共轭对称性。",
            "特征里用了未来帧却宣称实时。",
            "忘记 WOLA 归一化，ISTFT 边界出现爆音。"],
  exercises=["推导 IRM 与 Wiener 增益在何种假设下等价。",
             "解释为什么 IBM 比 IRM 更容易产生音乐噪声。",
             "写出一个因果掩码模型的输入张量形状与时间跨度。"],
  further=["{{ch:13}} Wiener 增益；{{ch:20}} 数据合成；{{ch:22}} 复数掩码。"]),

# ==================================================================== 20
C("20", "p4", "part4/20-data-synthesis", "训练数据合成：RIR、噪声、SNR 配比与数据泄漏",
  "模型能力的一半来自数据；把「造数据」写成可复现、可审计的生成脚本。",
  hours="3 学时",
  goals=["能把 3A 训练对写成 clean / RIR / noise / SNR 的生成式模型。",
         "能设计训练、验证、测试的划分规则并说明泄漏的来源。",
         "能量化「测试集里出现训练集噪声」造成的分数虚高。",
         "能列出至少四个数据增强轴与对应的评测维度。"],
  points=["配对语料生成", "RIR 与卷积", "噪声库与 SNR 配比", "数据增强轴",
          "训练/验证/测试划分", "说话人与房间解耦", "数据泄漏", "可复现脚本"],
  sections=[
      S("20.1", "一条生成式模型，四个随机源",
        eq("y = s + h_far * x_far + v　，v ~ Noise(seed)　，SNR = 10log₁₀(Σs² / Σv²)"),
        p("合成一对训练样本需要四个独立随机源：干净语音 <code>s</code>、远端语音 "
          "<code>x_far</code>、房间冲激响应 <code>h</code>、噪声 <code>v</code>。"
          "每个源都要有<strong>独立的种子空间</strong>：如果测试集与训练集共用同一批 RIR 或同一段噪声，"
          "模型等于见过答案，分数会虚高。"),
        table(["增强轴", "取值范围示例", "对应的评测维度"], [
            ["SNR", "-5 ~ 20 dB", "低信噪比鲁棒性"],
            ["房间 T60", "0.1 ~ 0.8 s", "混响泛化"],
            ["噪声类型", "平稳 / 键盘 / 音乐 / 街道", "分布外泛化"],
            ["电平与削波", "-30 ~ 0 dBFS，含非线性失真", "AGC 与非线性回声"],
            ["设备响应", "不同的麦克/扬声频响", "跨设备泛化"],
        ], ["18%", "36%", "46%"])),
      S("20.2", "泄漏比模型结构更致命",
        ul(["<strong>噪声泄漏</strong>：同一段噪声录音切两半分别放进训练与测试。",
            "<strong>房间泄漏</strong>：同一条 RIR 出现在两个集合里，模型记住了混响尾。",
            "<strong>说话人泄漏</strong>：同一说话人的不同句子被拆到两边，音色特征被记住。",
            "<strong>时间泄漏</strong>： utterance 之间重叠，或按帧而不是按文件划分。"]),
        p("正确的划分单位是<strong>源文件 / 房间 / 说话人</strong>，而不是样本或帧。"
          "Microsoft DNS-Challenge 与 AEC-Challenge 的合成脚本都提供了可借鉴的划分协议；"
          "真实录音（DEMAND、MUSAN、LibriSpeech）与仿真 RIR 应分别管理清单。"),
        note("本实验的口径", "用带 seed 依赖谱峰的合成噪声模拟「噪声类型」这一维度："
             "泄漏测试集复用一条训练噪声，独立测试集使用完全不同 seed 的噪声。"
             "固定噪声谱估计器在泄漏集上占便宜，从而量化虚高幅度。")),
  ],
  demos=[mk_demo(
      file="code/20-data-synthesis.py",
      title="实验 20-1 · 数据泄漏导致的分数虚高与谱峰对照",
      doc="合成带 seed 依赖谱峰的训练/测试集，量化噪声泄漏对固定噪声谱估计器的影响。",
      params="""N = 2000
N_FFT, HOP = 128, 64
N_TRAIN, N_TEST = 12, 6
SEED_TRAIN, SEED_LEAK, SEED_OOD = 1000, 1000, 2000""",
      body="""def make_noise(seed):
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
print("SAMPLE_RATE=%d N_FFT=%d HOP=%d | 划分单位: seed 而非帧" % (SAMPLE_RATE, N_FFT, HOP))""",
      figs=[("fig/20-split.svg", "三个集合上的分段 SNR"),
            ("fig/20-noise-spectrum.svg", "训练集平均噪声幅度谱")],
      audio=[("audio/20-train.wav", "训练集中的一条带噪样本"),
             ("audio/20-ood.wav", "独立测试集的一条带噪样本")],
      steps="对照泄漏测试与独立测试的分数；观察训练集噪声谱的尖峰位置。",
      expect="泄漏测试集复用训练噪声，固定噪声谱估计器能精准压住它的谱峰，分数高于独立测试集。"
             "<strong>这部分差距不是模型能力，是数据泄漏</strong>；{{ch:30}} 会系统展开。",
      tweak="把 SEED_LEAK 改成 2000（与 OOD 同源），泄漏虚高会消失。")],
  commands=[shell("查看 DNS-Challenge 的合成脚本入口",
                  "git clone --depth 1 https://github.com/microsoft/DNS-Challenge && ls DNS-Challenge/",
                  "该仓库提供大规模语音/噪声混合脚本与基线；请以其 README 与许可为准，"
                  "本书实验不下载任何外部语料。")],
  highlights=[("dns-challenge", "大规模合成数据脚本与基线协议"),
              ("librispeech", "常用干净语音语料"),
              ("musan", "噪声/音乐/语音增强源"),
              ("asteroid", "数据划分与 SI-SNR 损失的参考实现")],
  analogy="造训练数据就是写 property-based test 的生成器："
          "每个随机源是独立的 generator，划分必须按 generator 的 id 而不是按样本下标。",
  bridge="{{ch:19}} 定义了要学的映射，本章定义它的数据分布；"
         "{{ch:21}} 给出拟合这个映射的网络骨架，{{ch:30}} 把泄漏问题收进评测协议。",
  pitfalls=["按帧随机划分，相邻帧落进训练与测试两边。",
            "训练与测试共用同一批 RIR 或同一段噪声录音。",
            "只在合成数据上评测就宣称泛化。",
            "用测试集统计信息标定 SNR 或阈值。"],
  exercises=["写出一个包含 5 个独立 seed 空间的合成脚本签名。",
             "解释为什么「按文件划分」比「按帧划分」更安全。",
             "设计一组能暴露 RIR 泄漏的对照实验。"],
  further=["{{ch:21}} 网络骨架；{{ch:30}} 泛化与数据泄漏；{{ch:31}} 结课项目。"]),

# ==================================================================== 21
C("21", "p4", "part4/21-network-backbones", "网络骨架：DNN / CRN / U-Net / TCN / Conformer",
  "骨架的选择，本质上是选择「上下文怎么取」与「归纳偏置放在哪」。",
  hours="4 学时",
  goals=["能把主流语音增强骨架按上下文建模方式分类。",
         "能估算参数量、感受野与每帧算力，并比较实时可行性。",
         "能用纯标准库训练一个可解释的小型掩码估计器。",
         "能说明骨架选择与因果性、延迟之间的硬约束。"],
  points=["帧级 DNN", "卷积循环网络 CRN", "U-Net 编解码", "时间卷积网络 TCN",
          "Conformer 与注意力", "感受野与状态缓存", "参数量与 MACs", "骨架与延迟"],
  sections=[
      S("21.1", "五种骨架，五种取上下文的方式",
        table(["骨架", "上下文来源", "优势", "实时代价"], [
            ["DNN / MLP", "拼接相邻若干帧", "最简单、易量化", "参数量大、无长时依赖"],
            ["CRN", "CNN 提特征 + RNN 沿时间", "参数省、序列建模强", "RNN 状态逐帧依赖，难并行"],
            ["U-Net", "编码器下采样 + 跳连", "多尺度时频特征", "非因果卷积易引入未来帧"],
            ["TCN", "膨胀因果卷积", "并行、感受野可控", "需缓存历史，深栈有延迟"],
            ["Conformer", "卷积 + 自注意力", "长时依赖与局部特征兼得", "注意力开销与缓存最大"],
        ], ["14%", "30%", "28%", "28%"]),
        p("它们的输出形状完全一样：<code>G[t,k]</code> 或 <code>Ŝ[t,k]</code>。"
          "差别只在于<strong>为了算出第 t 帧，允许看多少过去、多少未来、多少频率邻域</strong>。"
          "实时 3A 只允许看过去，因此 TCN 与因果 CRN 最常见。")),
      S("21.2", "把骨架换算成三笔账",
        eq("感受野 ≈ (K−1)·Σ_t d_t + 1　；参数量 ≈ Σ_l C_in·C_out·K_l　；RTF = T_计算 / T_帧长"),
        ul(["<strong>感受野</strong>：膨胀因果卷积用 <code>d = 1,2,4,8,...</code> 指数扩张，"
            "几十层就能覆盖一秒上下文，但状态缓存必须保存每层历史。",
            "<strong>参数量</strong>：逐帧全连接把上下文帧数直接乘进输入维度，最容易膨胀；"
            "深度可分离卷积能把 MACs 降一个量级。",
            "<strong>延迟</strong>：算法延迟 = 帧长 + 前瞻 + 分块缓存；"
            "非因果 U-Net 的前瞻在实时链路里必须显式扣除（{{ch:28}}）。"]),
        note("本章的小模型", "实验用纯标准库训练一个 3 参数的 sigmoid 线性掩码估计器。"
             "它不是深度网络，但完整包含「特征 → 参数 → 损失 → 梯度 → 掩码 → ISTFT」这条闭环，"
             "用来把骨架的作用看清楚：更复杂的骨架只是把特征与 f_θ 换得更强。")),
  ],
  demos=[mk_demo(
      file="code/21-network-backbones.py",
      title="实验 21-1 · 训练一个 3 参数的掩码估计器并估算骨架开销",
      doc="用 SGD 训练小型 sigmoid 掩码估计器，打印损失曲线、测试集指标与主流骨架参数量估算。",
      params="""N = 4000
N_FFT, HOP = 128, 64
NOISE_AMP = 0.035
EPOCHS, LR = 14, 0.20
CONTEXT_FRAMES, HIDDEN, LAYERS = 5, 128, 3""",
      body="""tr_s = synthetic_speech(random.Random(11), N)
tr_n = white_noise(random.Random(12), N, NOISE_AMP)
te_s = synthetic_speech(random.Random(21), N)
te_n = white_noise(random.Random(22), N, NOISE_AMP)
tr_y = [tr_s[i] + tr_n[i] for i in range(N)]
te_y = [te_s[i] + te_n[i] for i in range(N)]
fy, fs, fn = stft(tr_y, N_FFT, HOP), stft(tr_s, N_FFT, HOP), stft(tr_n, N_FFT, HOP)

def feats(mag, avg):
    l, la = math.log10(mag + 1e-6), math.log10(avg + 1e-6)
    return [1.0, max(-2.0, min(1.0, l + 2.0)), max(-2.0, min(2.0, la - l))]
def predict(fv, w):
    z = max(-20.0, min(20.0, sum(w[j] * fv[j] for j in range(3))))
    return 1.0 / (1.0 + math.exp(-z))

train_set = []
for idx, (ry, iy) in enumerate(fy):
    rs, is_ = fs[idx]
    rn, in_ = fn[idx]
    mags = [math.hypot(ry[k], iy[k]) for k in range(N_FFT)]
    avg = sum(mags) / N_FFT
    for k in range(N_FFT):
        ms, mn = math.hypot(rs[k], is_[k]), math.hypot(rn[k], in_[k])
        train_set.append((feats(mags[k], avg), ms / (ms + mn + 1e-9)))
w, losses = [0.0, 0.0, 0.0], []
for ep in range(EPOCHS):
    total = 0.0
    for fv, t in train_set:
        p = predict(fv, w)
        err = p - t
        total += err * err
        d = err * p * (1.0 - p)
        for j in range(3):
            w[j] -= LR * d * fv[j]
    losses.append(total / len(train_set))

def apply_model(signal, gain_fn):
    frames = stft(signal, N_FFT, HOP)
    for ry, iy in frames:
        mags = [math.hypot(ry[k], iy[k]) for k in range(N_FFT)]
        avg = sum(mags) / N_FFT
        for k in range(N_FFT):
            g = gain_fn(feats(mags[k], avg))
            ry[k] *= g
            iy[k] *= g
    return istft(frames, N_FFT, HOP, N)
learned = apply_model(te_y, lambda fv: predict(fv, w))
ts, tn = stft(te_s, N_FFT, HOP), stft(te_n, N_FFT, HOP)
def oracle(idx, k):
    rs, is_ = ts[idx]
    rn, in_ = tn[idx]
    ms, mn = math.hypot(rs[k], is_[k]), math.hypot(rn[k], in_[k])
    return ms / (ms + mn + 1e-9)
frames = stft(te_y, N_FFT, HOP)
for idx, (ry, iy) in enumerate(frames):
    for k in range(N_FFT):
        g = oracle(idx, k)
        ry[k] *= g
        iy[k] *= g
irm = istft(frames, N_FFT, HOP, N)
scores = [seg_snr_db(te_s, scale_align(s, te_s)) for s in (te_y, learned, irm)]
c = Chart(FIG / "21-training.svg", "掩码估计器的训练损失（MSE）", xlabel="epoch", ylabel="MSE")
c.line(range(EPOCHS), losses, BLUE, label="训练 MSE")
print("训练图:", c.save())
b = Chart(FIG / "21-models.svg", "测试集：未处理 / 学习掩码 / IRM oracle", xlabel="方法", ylabel="dB",
          xticks=[(0, "未处理"), (1, "学习掩码"), (2, "IRM oracle")])
b.bars(range(3), scores, GREEN, label="分段 SNR (dB)")
print("模型图:", b.save())
dnn_params = (N_FFT // 2) * CONTEXT_FRAMES * HIDDEN + (LAYERS - 1) * HIDDEN * HIDDEN + HIDDEN * (N_FFT // 2)
write_wav(AUDIO / "21-test-noisy.wav", normalize_peak(te_y))
write_wav(AUDIO / "21-test-learned.wav", normalize_peak(learned))
print("训练 MSE 首=%.5f 末=%.5f | 学得权重 w=%s" %
      (losses[0], losses[-1], "[" + ", ".join("%.3f" % v for v in w) + "]"))
print("测试 segSNR 未处理=%.2f 学习掩码=%.2f IRM oracle=%.2f dB" % tuple(scores))
print("参数量估算: 本实验=3 | 帧级DNN(C=%d,L=%d,ctx=%d)≈%d | SAMPLE_RATE=%d" %
      (HIDDEN, LAYERS, CONTEXT_FRAMES, dnn_params, SAMPLE_RATE))""",
      figs=[("fig/21-training.svg", "小型掩码估计器的训练损失"),
            ("fig/21-models.svg", "未处理、学习掩码与 oracle 的指标对照")],
      audio=[("audio/21-test-noisy.wav", "测试集带噪输入"),
             ("audio/21-test-learned.wav", "3 参数学习掩码的输出")],
      steps="观察训练 MSE 是否单调下降；比较学习掩码与 oracle 的差距。",
      expect="训练 MSE 明显下降，学习掩码的分段 SNR 高于未处理但低于 IRM oracle。"
             "<strong>差距来自特征与模型容量</strong>：更强的骨架正是为了缩小这段距离，"
             "而不是改变链路或指标。",
      tweak="把 EPOCHS 改成 2，观察欠拟合；把 NOISE_AMP 提到 0.10，观察差距拉大。")],
  commands=[shell("查看 SpeechBrain 的语音增强配方目录",
                  "git clone --depth 1 https://github.com/speechbrain/speechbrain && ls speechbrain/recipes/",
                  "recipes 下按数据集组织的增强/分离训练脚本是当前骨架的工业参照；"
                  "请以其 README 与许可为准，本书实验不依赖 PyTorch。")],
  highlights=[("speechbrain", "主流增强骨架的开源训练配方"),
              ("asteroid", "TCN / Conv-TasNet 与 SI-SNR 损失实现"),
              ("torchaudio", "STFT 与流式推理的工业接口"),
              ("clearervoice", "FRCRN / MossFormer 等复数域骨架")],
  repos=[("SpeechBrain", "https://github.com/speechbrain/speechbrain",
          "语音任务配方齐全，适合复现掩码估计与损失函数", "AI · 框架"),
         ("Asteroid", "https://github.com/asteroid-team/asteroid",
          "TCN / Conv-TasNet 与 SI-SNR 损失的研究型框架", "AI · 框架")],
  analogy="骨架是「读多少上下文」的策略模式：DNN 拼帧、TCN 膨胀卷积、"
          "Conformer 用注意力。输出接口都是 <code>G[t,k]</code>，可以互换而不动下游。",
  bridge="{{ch:19}} 定义了标签，{{ch:20}} 定义了分布，本章定义 f_θ 的结构；"
         "{{ch:22}} 讨论它能否连相位一起学，{{ch:23}} 回到具体任务。",
  pitfalls=["用非因果卷积的前瞻做实时指标，忘了扣算法延迟。",
            "只比较参数量，忽略逐帧 MACs 与内存带宽。",
            "把骨架的论文分数直接迁移到自己的数据分布上。",
            "忽略 RNN/TCN 的状态缓存开销（{{ch:27}}）。"],
  exercises=["估算 3 层膨胀 TCN 的感受野与状态缓存大小。",
             "解释为什么实时 3A 偏爱因果 TCN 而非双向 U-Net。",
             "为本实验的小模型增加两个特征，说明它们为什么有用。"],
  further=["{{ch:22}} 复数域；{{ch:27}} 流式状态；{{ch:28}} 延迟预算。"]),

# ==================================================================== 22
C("22", "p4", "part4/22-complex-phase", "复数域与相位：DCCRN、深度滤波与时域模型",
  "只改幅度不改相位，是一条容易走到头的路；本章说明为什么以及下一步怎么走。",
  hours="3 学时",
  goals=["能说明幅度掩码在相位上的固有误差上界。",
         "能推导复数比值掩码 CRM 并解释它为何能同时修正幅度与相位。",
         "能对比谱域复数网络与时域编码器—解码器两条路线。",
         "能量化相位误差随信噪比的变化。"],
  points=["相位不变假设", "相位误差上界", "复数比值掩码 CRM", "DCCRN 与复数卷积",
          "深度滤波 DeepFilter", "时域 Conv-TasNet", "复数损失与 SI-SDR", "相位与可懂度"],
  sections=[
      S("22.1", "幅度掩码没有碰过的那半个信息",
        eq("Y = |Y|·e^{jφ_y}　，Ŝ = G·|Y|·e^{jφ_y}　→　相位误差 Δφ = φ_s − φ_y 完全保留"),
        p("{{ch:19}} 的 IRM 把相位原样留给了带噪信号。低 SNR 时 <code>φ_y</code> 与 "
          "<code>φ_s</code> 可能相差很大，此时无论幅度估得多准，重建波形都会与干净信号错开。"
          "这解释了为什么纯幅度掩码在高噪声下会出现「听起来闷、指标却不错」的现象。"),
        table(["路线", "输出", "能修相位吗", "代价"], [
            ["幅度掩码", "G[t,k] ∈ [0,1]", "不能", "最省算力，低 SNR 受限"],
            ["复数掩码", "M[t,k] ∈ ℂ，Ŝ = M·Y", "能", "需复数网络或实部/虚部双通道"],
            ["复数谱映射", "直接回归 Ŝ 的实部虚部", "能", "输出动态范围大，训练更难"],
            ["时域模型", "一维卷积直接输出波形", "隐式能", "无需 STFT，但感受野与算力要求高"],
        ], ["18%", "30%", "18%", "34%"])),
      S("22.2", "CRM、DCCRN 与深度滤波",
        eq("M = S / Y = (S·Y*) / (|Y|² + ε)　→　Re(M) = (S_r Y_r + S_i Y_i)/(|Y|²+ε)"),
        p("复数比值掩码就是一次复数除法：把它乘回 <code>Y</code> 能精确还原 <code>S</code>（oracle 情形）。"
          "DCCRN 用复数卷积网络去预测这个 <code>M</code>；DeepFilterNet 在低频用深度复数滤波、"
          "高频用传统增益，以极低算力换取相位修正；Conv-TasNet 则干脆绕开 STFT，"
          "用时域编码器学习一组可学习的「滤波器组」。"),
        ul(["<strong>相位与可懂度</strong>：STOI 等可懂度指标对相位误差不如对幅度敏感，"
            "但听感与下游 ASR 仍会受影响。",
            "<strong>损失</strong>：复数 MSE、幅度 + 相位加权、或直接 SI-SDR（{{ch:26}}）。",
            "<strong>实时性</strong>：复数网络参数量约为实数版的两倍，量化前要重算预算（{{ch:29}}）。"]),
        note("oracle 提醒", "实验里的 CRM 需要干净谱 <code>S</code>，与 IRM 一样是上界；"
             "为得到有限可比的数值，代码给它加了与网络预测误差同量级的扰动。"
             "真正部署时必须由网络预测 M，性能还会再下降。")),
  ],
  demos=[mk_demo(
      file="code/22-complex-phase.py",
      title="实验 22-1 · 幅度掩码、复数掩码与相位误差分布",
      doc="计算 IRM 与 oracle CRM，比较二者的 SI-SDR，并画出干净谱与带噪谱的相位误差直方图。",
      params="""N = 8000
N_FFT, HOP = 256, 128
NOISE_AMP = 0.040
MASK_NOISE = 0.06       # 模拟网络预测误差，避免 oracle 精确重建
BINS = 12""",
      body="""rng = random.Random(7)
clean = synthetic_speech(rng, N)
noise = white_noise(rng, N, NOISE_AMP)
noisy = [clean[i] + noise[i] for i in range(N)]
fs, fn = stft(clean, N_FFT, HOP), stft(noise, N_FFT, HOP)
hist = [0] * BINS
phase_vals = []
for idx, (ry, iy) in enumerate(stft(noisy, N_FFT, HOP)):
    rs, is_ = fs[idx]
    rn, in_ = fn[idx]
    for k in range(1, N_FFT // 2):
        d = (math.atan2(is_[k], rs[k]) - math.atan2(iy[k], ry[k]) + math.pi) % (2 * math.pi) - math.pi
        phase_vals.append(abs(d))
        b = min(BINS - 1, int(abs(d) / math.pi * BINS))
        hist[b] += 1

def masked(kind):
    frames = stft(noisy, N_FFT, HOP)
    for idx, (ry, iy) in enumerate(frames):
        rs, is_ = fs[idx]
        rn, in_ = fn[idx]
        for k in range(N_FFT):
            ms, mn = math.hypot(rs[k], is_[k]), math.hypot(rn[k], in_[k])
            if kind == "IRM":
                g = ms / (ms + mn + 1e-9)
                ry[k] *= g
                iy[k] *= g
            else:
                y2 = ry[k] ** 2 + iy[k] ** 2 + 1e-12
                cr = (rs[k] * ry[k] + is_[k] * iy[k]) / y2
                ci = (is_[k] * ry[k] - rs[k] * iy[k]) / y2
                cr += rng.gauss(0, MASK_NOISE)
                ci += rng.gauss(0, MASK_NOISE)
                ry[k], iy[k] = cr * ry[k] - ci * iy[k], cr * iy[k] + ci * ry[k]
    return istft(frames, N_FFT, HOP, N)

irm, crm = masked("IRM"), masked("CRM")
labels = ("未处理", "IRM oracle", "CRM+预测误差")
signals = (noisy, irm, crm)
snrs = [seg_snr_db(clean, scale_align(s, clean)) for s in signals]
sdrs = [si_sdr_db(s, clean) for s in signals]
c = Chart(FIG / "22-masks.svg", "三种情形的分段 SNR 与 SI-SDR", xlabel="方法", ylabel="dB",
          xticks=[(i, m) for i, m in enumerate(labels)])
c.bars(range(3), snrs, BLUE, label="分段 SNR (dB)")
c.bars(range(3), sdrs, GREEN, label="SI-SDR (dB)")
print("掩码图:", c.save())
h = Chart(FIG / "22-phase.svg", "干净谱与带噪谱的相位误差分布", xlabel="|Δφ| 区间 / π", ylabel="频点计数")
h.bars(range(BINS), hist, RED, label="相位误差")
print("相位图:", h.save())
write_wav(AUDIO / "22-noisy.wav", normalize_peak(noisy))
write_wav(AUDIO / "22-irm.wav", normalize_peak(irm))
write_wav(AUDIO / "22-crm.wav", normalize_peak(crm))
for m, a, b in zip(labels, snrs, sdrs):
    print("%s: segSNR=%.2f dB SI-SDR=%.2f dB" % (m, a, b))
print("平均 |Δφ|=%.3f rad | IRM→CRM SI-SDR 增益=%.2f dB | SAMPLE_RATE=%d N_FFT=%d" %
      (sum(phase_vals) / len(phase_vals), sdrs[2] - sdrs[1], SAMPLE_RATE, N_FFT))""",
      figs=[("fig/22-masks.svg", "幅度掩码与复数掩码的指标对照"),
            ("fig/22-phase.svg", "相位误差分布直方图")],
      audio=[("audio/22-noisy.wav", "带噪输入"),
             ("audio/22-irm.wav", "IRM：只改幅度"),
             ("audio/22-crm.wav", "带预测误差的 CRM：幅度与相位一起修正")],
      steps="对照 IRM 与 CRM 的 SI-SDR；观察相位误差直方图是否集中在零附近。",
      expect="给 oracle CRM 加上与网络预测误差同量级的扰动后，它仍能同时修正幅度与相位，"
             "SI-SDR 高于 IRM。<strong>说明幅度掩码留下的那部分误差确实来自相位</strong>；"
             "若把 MASK_NOISE 设为 0，CRM 会精确重建干净谱，SI-SDR 趋于无穷——那只是 oracle 上界。",
      tweak="把 NOISE_AMP 提到 0.12，相位误差分布右移，IRM 与 CRM 的差距进一步拉大。")],
  commands=[shell("查看 DeepFilterNet 的推理入口",
                  "git clone --depth 1 https://github.com/Rikorose/DeepFilterNet && ls DeepFilterNet/",
                  "该工程以低算力复数深度滤波做实时增强；请以其 README 与许可为准，"
                  "本书实验不依赖 PyTorch。")],
  highlights=[("deepfilternet", "复数深度滤波与低算力实时增强"),
              ("torchaudio", "复数 STFT 与 ISTFT 的工业实现"),
              ("wiki-mask", "时频掩码与相位分析的背景"),
              ("asteroid", "时域 Conv-TasNet 与 SI-SDR 实现")],
  repos=[("DeepFilterNet", "https://github.com/Rikorose/DeepFilterNet",
          "复数域深度滤波，低算力实时增强的代表工程", "AI · 实时"),
         ("Asteroid", "https://github.com/asteroid-team/asteroid",
          "时域分离/增强网络与 SI-SDR 损失实现", "AI · 框架")],
  analogy="只改幅度相当于给复数只缩放不旋转；复数掩码允许同时旋转，"
          "因此能补回 <code>φ_s − φ_y</code> 这一半信息。",
  bridge="{{ch:21}} 讨论「读多少上下文」，本章讨论「输出什么域」；"
         "{{ch:23}} 回到具体任务，{{ch:24}} 把参考信号也接进网络。",
  pitfalls=["把 oracle CRM 的分数当成可部署模型成绩。",
            "复数掩码只作用于前半频谱，破坏共轭对称性。",
            "认为相位对可懂度没影响就不必建模。",
            "忽略复数网络带来的参数量与量化误差翻倍。"],
  exercises=["推导 M = S/Y 的实部与虚部表达式。",
             "解释为什么低 SNR 时相位误差分布会变宽。",
             "比较复数谱映射与时域模型在延迟上的差别。"],
  further=["{{ch:19}} 时频掩码；{{ch:23}} 神经降噪；{{ch:29}} 量化。"]),

# ==================================================================== 23
C("23", "p5", "part5/23-neural-ns", "神经噪声抑制：从 RNNoise 到 DNS Challenge",
  "把降噪器压缩到几个频带增益，是「神经方法能跑在端侧」的关键一步。",
  hours="3 学时",
  goals=["能说明混合 DSP / 神经网络降噪的分工方式。",
         "能解释频带增益相比全分辨率掩码的算力与精度折中。",
         "能实现频带增益估计并扫描频带数量的影响。",
         "能说清 DNS Challenge 的评测协议与常见指标。"],
  points=["混合 DSP / DNN 架构", "RNNoise 频带增益", "Bark / 梅尔频带", "逐帧 GRU 与状态",
          "DNS Challenge", "DNSMOS 无参考评分", "频带数与失真", "实时算力预算"],
  sections=[
      S("23.1", "RNNoise 的「小」是设计出来的",
        p("RNNoise 不预测几百个频率箱的掩码，只预测约 22 个 Bark 频带的增益，"
          "再用传统 FFT 滤波器组执行。网络只负责「每个频带此刻该压多少」这一低维决策，"
          "特征提取、频带划分与合成仍由 DSP 完成。"
          "因此它能在很小的算力下实时运行，并成为 ffmpeg <code>arnndn</code> 的模型来源。"),
        table(["层", "由谁做", "维度", "原因"], [
            ["特征", "DSP", "频带能量 + 差分 + 音高特征", "手工特征稳、便宜"],
            ["决策", "GRU / 小型网络", "约 22 个增益", "让网络只学最难的部分"],
            ["执行", "DSP 滤波器组", "全分辨率谱", "避免网络逐 bin 输出"],
            ["平滑", "一阶 IIR", "跨帧增益", "抑制音乐噪声"],
        ], ["12%", "26%", "30%", "32%"])),
      S("23.2", "DNS Challenge 把问题规模化",
        eq("Score = w₁·语音质量 + w₂·噪声抑制 + w₃·可懂度　（P.835 三维主观 / DNSMOS 代理）"),
        ul(["<strong>数据</strong>：大规模干净语音 + 噪声 + RIR 合成，覆盖多种 SNR 与混响（{{ch:20}}）。",
            "<strong>约束</strong>：赛道通常限定因果、最大延迟与实时因子，离线模型不能参赛。",
            "<strong>评测</strong>：ITU-T P.835 的语音/噪声/总体三维主观分，"
            "配合 DNSMOS 等无参考模型做快速迭代。",
            "<strong>陷阱</strong>：只优化 DNSMOS 容易奖励过度降噪；必须同时看语音失真与可懂度。"]),
        note("与本书实验的关系", "实验用 oracle 频带增益（由干净/带噪谱能量算出）扫描频带数，"
             "目的是量化「降维带来的信息损失」这一条，而不是复现任何具体模型的分数。")),
  ],
  demos=[mk_demo(
      file="code/23-neural-ns.py",
      title="实验 23-1 · 频带数量对降噪精度的影响与频带增益热力图",
      doc="用 oracle 频带增益扫描 4～64 个频带，比较分段 SNR 与全分辨率 IRM 上界。",
      params="""N = 8000
N_FFT, HOP = 256, 128
NOISE_AMP = 0.035
BANDS = (4, 8, 16, 22, 32, 64)
FLOOR = 0.10""",
      body="""rng = random.Random(7)
clean = synthetic_speech(rng, N)
noise = white_noise(rng, N, NOISE_AMP)
noisy = [clean[i] + noise[i] for i in range(N)]
fs, fn = stft(clean, N_FFT, HOP), stft(noise, N_FFT, HOP)
HALF = N_FFT // 2
def band_index(k, B):
    kk = k if k <= HALF else N_FFT - k
    return min(B - 1, kk * B // HALF)
def enhance(B, record=False):
    frames = stft(noisy, N_FFT, HOP)
    rows = []
    for idx, (ry, iy) in enumerate(frames):
        rs, is_ = fs[idx]
        rn, in_ = fn[idx]
        ps, py = [0.0] * B, [0.0] * B
        for k in range(N_FFT):
            b = band_index(k, B)
            ps[b] += rs[k] ** 2 + is_[k] ** 2
            py[b] += ry[k] ** 2 + iy[k] ** 2
        gains = [max(FLOOR, min(1.0, math.sqrt(ps[b] / (py[b] + 1e-12)))) for b in range(B)]
        for k in range(N_FFT):
            g = gains[band_index(k, B)]
            ry[k] *= g
            iy[k] *= g
        if record:
            rows.append(gains)
    return istft(frames, N_FFT, HOP, N), rows
scores, outputs = [], []
for B in BANDS:
    out, _ = enhance(B)
    outputs.append(out)
    scores.append(seg_snr_db(clean, scale_align(out, clean)))
full_frames = stft(noisy, N_FFT, HOP)
for idx, (ry, iy) in enumerate(full_frames):
    rs, is_ = fs[idx]
    rn, in_ = fn[idx]
    for k in range(N_FFT):
        g = math.hypot(rs[k], is_[k]) / (math.hypot(rs[k], is_[k]) + math.hypot(rn[k], in_[k]) + 1e-9)
        ry[k] *= g
        iy[k] *= g
irm = istft(full_frames, N_FFT, HOP, N)
irm_score = seg_snr_db(clean, scale_align(irm, clean))
_, rows22 = enhance(22, record=True)
c = Chart(FIG / "23-bands.svg", "频带数量与分段 SNR（oracle 增益）", xlabel="频带数", ylabel="dB",
          xticks=[(i, "%d" % B) for i, B in enumerate(BANDS)])
c.line(range(len(BANDS)), scores, BLUE, label="频带增益 segSNR")
c.line(range(len(BANDS)), [irm_score] * len(BANDS), RED, label="全分辨率 IRM 上界")
print("频带图:", c.save())
mat = rows22[::4]
heatmap(FIG / "23-gains.svg", mat,
        ["frame%d" % (i * 4) for i in range(len(mat))],
        ["b%d" % j for j in range(22)],
        title="22 频带 oracle 增益（降采样显示）", vmin=0.0, vmax=1.0, annotate=False)
print("增益热力图:", str(FIG / "23-gains.svg"))
write_wav(AUDIO / "23-noisy.wav", normalize_peak(noisy))
write_wav(AUDIO / "23-22band.wav", normalize_peak(outputs[3]))
print("频带数→segSNR: " + " ".join("%d=%.2f" % (B, s) for B, s in zip(BANDS, scores)))
print("全分辨率 IRM=%.2f dB | 22 频带相对上界差=%.2f dB | SAMPLE_RATE=%d" %
      (irm_score, irm_score - scores[3], SAMPLE_RATE))""",
      figs=[("fig/23-bands.svg", "频带数量与分段 SNR 的关系"),
            ("fig/23-gains.svg", "22 频带增益的时频热力图")],
      audio=[("audio/23-noisy.wav", "带噪输入"),
             ("audio/23-22band.wav", "22 频带 oracle 增益的输出")],
      steps="对照频带数曲线与全分辨率上界；观察增益热力图里哪些频带长期被压低。",
      expect="频带数越多越接近全分辨率 IRM，但增益维度、网络输出与算力同步上升。"
             "<strong>RNNoise 选择约 22 个频带，正是在这条曲线上取的一个工程折中</strong>。",
      tweak="把 FLOOR 从 0.10 改成 0.30，低 SNR 频带不再被深压，指标与听感同时变化。")],
  commands=[shell("自查本机 arnndn 是否可用（RNNoise 模型需自备）",
                  "ffmpeg -hide_banner -filters | grep arnndn && ffmpeg -hide_banner -h filter=arnndn | head -20",
                  "arnndn 加载 RNNoise 训练出的 .rnnn 模型；是否编译进本机、参数名与模型格式"
                  "请以本机输出与 https://ffmpeg.org/ffmpeg-filters.html#arnndn 为准。"),
            shell("定位 DNSMOS 评测脚本",
                  "git clone --depth 1 https://github.com/microsoft/DNS-Challenge && ls DNS-Challenge/DNSMOS/",
                  "DNSMOS 是无参考神经 MOS 评分；请以其 README 与许可为准，"
                  "本书实验不下载模型权重。")],
  highlights=[("dns-challenge", "大规模数据、赛道约束与评测协议"),
              ("dnsmos", "无参考神经 MOS 评分"),
              ("rnnoise", "混合 DSP/GRU 的代表工程"),
              ("wiki-spectral-sub", "频带增益与谱减的历史联系")],
  repos=[("RNNoise", "https://github.com/xiph/rnnoise",
          "混合 DSP/深度学习的实时降噪，ffmpeg arnndn 的模型来源", "AI · C"),
         ("Microsoft DNS-Challenge", "https://github.com/microsoft/DNS-Challenge",
          "大规模合成数据、基线模型与评测协议", "数据集 · 基线")],
  analogy="把几百个频率箱聚成 22 个频带，等于把回归输出从 256 维降到 22 维："
          "模型更小、更快，但丢掉了带内细节——一条典型的容量—精度折中曲线。",
  bridge="{{ch:19}}～{{ch:22}} 给出掩码、数据与骨架，本章把它们落回 ANS 任务；"
         "{{ch:24}} 把远端参考接进网络做神经 AEC，{{ch:26}} 再合并三个任务。",
  pitfalls=["把 oracle 频带增益的分数当成 RNNoise 的实测成绩。",
            "只优化 DNSMOS，忽略语音失真与可懂度。",
            "忽略跨帧状态，逐帧独立决策会产生增益抖动。",
            "把离线两遍处理的结果当作实时赛道成绩。"],
  exercises=["估算 B 个频带增益相对全分辨率掩码节省了多少输出维度。",
             "解释为什么频带划分常按 Bark / 梅尔尺度而非等宽。",
             "设计一个同时报质量、可懂度与噪声抑制的评测表。"],
  further=["{{ch:24}} 神经 AEC；{{ch:26}} 联合 3A；{{ch:30}} 泛化与评测陷阱。"]),

]
