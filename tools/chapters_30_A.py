#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 30～31 章与附录 A：泛化与评测陷阱、结课项目、全书速查。"""
from __future__ import annotations

from book_schema import C, eq, table
from chapter_kit import mk_demo, shell, p, ul, ol, note, warn, sec

CH = [

# ==================================================================== 30
C("30", "p6", "part6/30-generalization", "泛化、鲁棒性与评测陷阱",
  "把「分数很高」和「真的好用」分开：数据划分、分布外测试与指标组合才决定结论的边界。",
  hours="3 学时",
  goals=[
      "能把一次评测拆成训练集、验证集、测试集与盲测集，并说明各自允许的操作。",
      "能复现「在测试集上扫阈值」造成的分数虚高，并量化虚高幅度。",
      "能构造分布外退化轴（噪声、房间、电平、设备），报告同分布与分布外的落差。",
      "能写出一份可复核的评测协议，指出至少四种常见陷阱。",
  ],
  points=["训练/验证/测试划分", "数据泄漏", "测试集调参", "样本内与样本外",
          "分布外 OOD", "鲁棒性与退化轴", "指标组合与 Goodhart", "可复现评测协议"],
  sections=[
      ("30.1", "从「分数」到「结论」：样本内与样本外", sec(
          p("{{ch:03}} 给出指标怎么算，{{ch:18}} 给出经典链路怎么测；本章处理更前置的问题："
            "<strong>这份分数在回答哪个问题，它的有效范围到哪里为止</strong>。"
            "把评测当成程序里的回归测试：训练集是开发时跑的用例，验证集是 CI 里调参用的用例，"
            "测试集是发版前只跑一次、跑完就冻结的用例。"),
          eq("D = D_train ∪ D_val ∪ D_test　，三者两两不交　，θ* = argmax_θ Score(D_val ; θ)"),
          p("任何在 <code>D_test</code> 上做的选择——挑阈值、挑 checkpoint、挑噪声类型、"
            "甚至「看了坏样本之后决定加一条后处理」——都会把测试集变成验证集，"
            "于是报告出来的分数不再是样本外成绩。"),
          table(["集合", "允许做什么", "不允许做什么", "对应工程动作"], [
              ["D_train", "拟合权重、设计数据增强与损失", "接触测试标签", "训练循环"],
              ["D_val", "选超参、早停、选 checkpoint", "再拿它报最终分数", "CI 调参 / 模型选择"],
              ["D_test", "只跑一次前向并报告均值", "按结果改任何参数", "发版冻结的回归集"],
              ["D_blind", "结项时跑一次，附失败样本", "开发全程不可见", "盲测归档"],
          ], ["12%", "30%", "28%", "30%"]))),
      ("30.2", "四类最常见的评测陷阱", sec(
          ol([
              "<strong>泄漏（leakage）</strong>：同一段录音、同一说话人、同一房间或同一噪声片段"
              "被切到两个集合。语音帧高度相关，按帧随机切分等于把样本内成绩当样本外报；"
              "分组必须按<strong>录音 ID / 说话人 / 房间</strong>做。",
              "<strong>测试集调参</strong>：在 D_test 上扫候选并报告最大值。"
              "候选越多，这个最大值越像极值统计而不是泛化能力。",
              "<strong>指标单一与 Goodhart 化</strong>：只优化 segSNR 会奖励「把一切都压成静音」；"
              "必须同时报失真类、可懂度类与主观/无参考类指标（见 {{ch:03}}）。",
              "<strong>尺度与口径漂移</strong>：AGC 改变整体增益后不做尺度对齐，"
              "或基线与模型用了不同窗长、采样率、VAD 口径，分数不可比。",
          ]),
          warn("把「看过」当成「没看过」",
               "读完测试集里的坏样本再改代码，即使没有把测试样本喂进梯度，结论也已被条件化。"
               "工程做法是另开一个<strong>最终盲测集</strong>：开发全程不可见，只在结项时跑一次。"),
          p("{{ch:27}} 的流式化、{{ch:29}} 的量化之后，模型已经不是同一个函数；"
            "任何部署改动都应把盲测集再跑一遍，而不是沿用浮点离线分数。"))),
      ("30.3", "分布外与鲁棒性：把「没见过」写成可测集合", sec(
          p("鲁棒性不是形容词，而是一张<strong>退化类型 × 强度</strong>的二维表。"
            "训练分布里见过的轴叫同分布（ID），没见过的轴叫分布外（OOD）。"),
          table(["轴", "训练内示例", "分布外示例", "应观察的量"], [
              ["噪声", "平稳高斯白噪声", "低频嗡鸣、周期性突发、键盘敲击", "分数落差与残余噪声可听度"],
              ["房间", "T60 约 0.2 s 的合成 RIR", "强混响、路径突变、扬声器削波", "ERLE 是否塌陷、双讲是否漏回声"],
              ["电平", "固定 RMS 区间", "极低电平 + AGC 大增益、削波", "LUFS 与真峰值、噪声被一起放大"],
              ["设备", "16 kHz 合成语音", "重采样、编解码、时钟漂移", "缓冲对齐后的稳定性"],
          ], ["12%", "26%", "32%", "30%"]),
          eq("Gap_OOD(θ*) = Score(D_ID ; θ*) − Score(D_OOD ; θ*)　，θ* 只由 D_val 决定"),
          p("注意 <code>Gap_OOD</code> 与「虚高」是两件事：前者是<strong>分布漂移</strong>带来的真实落差，"
            "后者是<strong>评测口径错误</strong>带来的假象。本章实验把两者分别打印，"
            "读者可改噪声配方观察哪一项先恶化。"))),
      ("30.4", "一份可复核的评测协议与进阶路径", sec(
          ol([
              "先写死划分：按录音 ID 分组，固定随机种子 <code>random.seed(7)</code>，把分组清单落到文件。",
              "写死口径：采样率、窗长、帧移、是否尺度对齐、指标实现、盲测集路径。",
              "先跑三行基线：无处理、经典 3A（{{ch:18}}）、待评模型，同表输出。",
              "再做消融：每次只改一个变量，记录它在 D_val 与 D_test 上的收益差。",
              "最后跑盲测：一次前向，输出均值、离散度与失败样本归档。",
          ]),
          note("与结课项目的接口",
               "{{ch:31}} 把上述五步写成验收清单；本章实验只用一个可解释阈值掩码做载体，"
               "换成 PyTorch 模型后协议一字不改。"),
          p("进阶路径：把本实验的阈值增益换成 "
            "<a href='https://github.com/speechbrain/speechbrain' target='_blank' rel='noopener noreferrer'>SpeechBrain ↗</a>"
            " 的增强配方，用 "
            "<a href='https://github.com/microsoft/DNS-Challenge' target='_blank' rel='noopener noreferrer'>DNS-Challenge ↗</a>"
            " 的真实噪声替换合成噪声，再用 "
            "<a href='https://github.com/microsoft/DNS-Challenge/tree/master/DNSMOS' target='_blank' rel='noopener noreferrer'>DNSMOS ↗</a>"
            " 补一个无参考分数；训练循环参考 "
            "<a href='https://pytorch.org/docs/stable/index.html' target='_blank' rel='noopener noreferrer'>PyTorch 文档 ↗</a>。"))),
  ],
  demos=[mk_demo(
      "code/30-generalization.py", "实验 30-1 · 测试集调参的虚高与分布外噪声下的落差",
      "用纯标准库合成四组数据，扫描可解释阈值掩码的超参，分别打印泄漏虚高与 OOD 落差。",
      """N = 4096                    # 每条样本 0.256 s @ 16 kHz
N_FFT, HOP = 256, 128
THETAS = (0.20, 0.35, 0.50, 0.65, 0.80, 0.95, 1.20, 1.50, 2.00)
NOISE_AMP = 0.035           # 训练与同分布测试的高斯噪声幅度
FLOOR = 0.12                # 掩码增益下限""",
      """rng = random.Random(7)

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
      (inflate, gap_ood, SAMPLE_RATE, len(THETAS)))""",
      [("fig/30-leak.svg", "验证集与测试集的 theta 扫描曲线"),
       ("fig/30-ood.svg", "泄漏虚高与分布外落差的柱状对照")],
      [("audio/30-clean.wav", "干净参考语音"),
       ("audio/30-id-noisy.wav", "同分布白噪声退化样本"),
       ("audio/30-id-masked.wav", "同分布样本经阈值掩码处理"),
       ("audio/30-ood-noisy.wav", "分布外：低频嗡鸣与周期性突发"),
       ("audio/30-ood-masked.wav", "分布外样本经同一 theta 处理")],
      steps="先对照 <code>30-leak.svg</code> 的两条曲线，再听 <code>30-ood-noisy.wav</code> 与 "
            "<code>30-ood-masked.wav</code>；把 <code>NOISE_AMP</code> 调大后重跑。",
      expect="本例验证集与测试集的最优点恰好相同（<code>theta*=1.50</code>），虚高为 0.00 dB——"
             "<strong>流程仍然是错的，只是这一次没被数字抓到</strong>；换数据划分或更细网格就可能出现虚高。"
             "同一 <code>theta*</code> 挪到分布外嗡鸣噪声上，落差约 4.7 dB，这部分是真实的泛化损失。"
             "脚本打印的每一行都是本机实测值，请直接以打印结果为准，不预设任何目标分数。",
      tweak="把 <code>THETAS</code> 改成更细的非均匀网格，或换几条测试噪声，观察虚高是否出现；"
            "把 <code>noise_of</code> 的嗡鸣频率改成训练见过的白噪声，落差会缩小。")],
  commands=[
      shell("本机自查可用滤镜，再对照官方文档",
            "ffmpeg -hide_banner -filters | grep -E 'afftdn|arnndn|astats|volumedetect|silencedetect'",
            "滤镜清单随版本与编译选项变化；以本机输出与 https://ffmpeg.org/ffmpeg-filters.html 官方说明为准，不写死版本。"),
      shell("核对评测样本的时长与格式口径",
            "ffprobe -v error -show_entries stream=sample_rate,channels -of default=noprint_wrappers=1 test.wav",
            "比较指标前先确认测试集采样率与声道数一致；不同口径的分数不可直接比较。"),
  ],
  highlights=[("dnsmos", "无参考神经 MOS，适合没有干净参考时的补充评估"),
              ("aec-challenge", "真实双讲与非线性失真，检验评测集是否覆盖 OOD"),
              ("demand", "多环境真实噪声，构造分布外噪声轴"),
              ("dns-challenge", "大规模合成脚本与官方评测协议，对照数据划分方式")],
  repos=[
      ("Microsoft DNS-Challenge", "https://github.com/microsoft/DNS-Challenge",
       "大规模语音/噪声合成脚本、基线模型与评测协议", "数据集 · 基线"),
      ("DNSMOS", "https://github.com/microsoft/DNS-Challenge/tree/master/DNSMOS",
       "无参考神经 MOS，用于没有干净参考时的快速评估", "评测"),
      ("Microsoft AEC-Challenge", "https://github.com/microsoft/AEC-Challenge",
       "真实双讲、非线性失真与远端单讲录音，AEC 必测", "数据集 · 基线"),
  ],
  analogy="评测集是发版门禁：验证集是 CI 里可以反复调参的用例，测试集是冻结的回归集，"
          "盲测集是生产灰度。<strong>把回归集当成调参脚本的输入，等于把单元测试的答案写进了代码。</strong>",
  bridge="承接 {{ch:29}} 的量化部署改动：模型换了实现就要重测；"
         "{{ch:31}} 把本章协议落成结课项目的验收清单，附录 A 汇总指标与命令速查。",
  pitfalls=["按帧而不是按录音/说话人/房间随机切分，造成同源泄漏。",
            "在测试集上扫阈值或选 checkpoint，还把最大值当样本外成绩汇报。",
            "只报一个 segSNR，忽略了「全压成静音」也能刷分的策略。",
            "AGC 或量化后不做尺度对齐、不重跑盲测，沿用旧的浮点离线分数。"],
  exercises=["设计一份按录音 ID 分组的切分脚本，说明它如何避免同源泄漏。",
             "推导「候选数增加时测试集最大值单调不降」，并解释这与泛化无关。",
             "为实时通话 App 列一张含噪声、房间、电平、设备四轴的 OOD 测试表。"],
  further=["{{ch:31}} 结课项目的验收清单；{{ch:03}} 指标定义与 {{ch:18}} 经典评测链路。",
           "{{ch:29}} 量化后再测；{{ch:23}} 神经降噪的训练分布设计。"]),

# ==================================================================== 31
C("31", "p6", "part6/31-capstone", "结课项目：小型掩码估计器与全链路验证",
  "把全书收束成一个可交付项目：合成数据、可解释掩码、消融矩阵、验收清单与复现脚本。",
  hours="4 学时",
  goals=[
      "能写出结课项目的输入、输出、因果约束与不可变口径。",
      "能实现一个零第三方依赖的 STFT 阈值掩码估计器并跑通消融矩阵。",
      "能计算理想比率掩码 oracle 上界，说明它与可解释模型的差距来源。",
      "能按验收清单报告数据、指标、消融、复现命令与失败样本。",
  ],
  points=["结课项目规格", "合成数据配方", "STFT 与 WOLA", "理想比率掩码 IRM",
          "可解释阈值掩码", "消融矩阵", "因果与延迟约束", "验收清单与复现"],
  sections=[
      ("31.1", "项目规格：一条可交付的 3A 链路", sec(
          p("目标不是刷新分数，而是交付一份<strong>别人能重跑、能改、能判对错</strong>的工程。"
            "输入是麦克风信号 <code>y[n]</code>，输出是增强后的 <code>ŝ[n]</code>；"
            "中间只允许一个逐时频单元的增益 <code>G[t,k]</code>，"
            "这样整条链路仍可放进 {{ch:28}} 的延迟预算里。"),
          eq("ŝ = ISTFT( G ⊙ STFT(y) )　，G ∈ [0,1]^{T×F}　，G[t,·] 只依赖第 t 帧及之前的帧"),
          table(["项", "规格", "不可变约束"], [
              ["采样率 / 位深", "16 kHz / 16-bit 单声道 PCM", "全书统一，write_wav() 写出"],
              ["帧 / 窗", "N=256 或 512，hop=N/2，Hann", "修改频谱后必须 WOLA 归一化"],
              ["模型", "可解释阈值掩码（本实验）+ 可选神经掩码", "零第三方依赖版必须只含标准库"],
              ["因果性", "不使用未来帧，不依赖整段统计", "见 {{ch:27}} 的流式状态缓存"],
              ["产物", "fig/*.svg、audio/*.wav、终端数值", "由脚本一次性生成，不手工改图"],
          ], ["16%", "42%", "42%"]),
          note("规格边界", "本实验的全部语音与噪声均为 <code>tools/dsp.py</code> 合成信号，"
               "不是真实录音，也不是任何产品的性能数据；结论只用于说明机制与量级。"))),
      ("31.2", "数据：合成配方与三组划分", sec(
          p("用 <code>synthetic_speech()</code> 生成具备谐波结构、音节包络与少量清音的类语音，"
            "叠加 <code>white_noise()</code>、低频音调与房间冲激响应；"
            "每条样本带唯一的录音 ID，按 ID 分组切分，避免 {{ch:30}} 说的同源泄漏。"),
          table(["集合", "用途", "配方", "可否调参"], [
              ["D_train", "估计噪声谱先验、拟合阈值", "干净语音 + 白噪声 / 色调噪声", "可以"],
              ["D_val", "选阈值、下限、平滑系数", "与训练同分布，独立样本", "可以"],
              ["D_test", "报告最终指标", "同分布 + OOD 两个子集", "不可以"],
              ["D_blind", "结项一次前向", "固定种子、全程不可见", "不可以"],
          ], ["12%", "26%", "38%", "24%"]),
          eq("y[n] = s[n] + v[n]　，v 可由 white_noise / tone / chirp / rir 组合；分组键 = 录音 ID"))),
      ("31.3", "指标、消融与验收清单", sec(
          p("指标必须成组报告：尺度对齐后的分段 SNR、尺度不变的 SI-SDR、响度近似 LUFS，"
            "再补一个无参考分数（DNSMOS 或主观听测）。" 
            "消融每次只改一个变量，记录它在 D_val 与 D_test 上的收益差。"),
          table(["编号", "变体", "改了什么", "要回答的问题"], [
              ["v0", "无处理", "基线", "退化有多严重"],
              ["v1", "纯阈值", "只加 1 − θ·N̂/|Y|", "阈值本身贡献多少"],
              ["v2", "加增益下限", "再加 FLOOR", "音乐噪声是否被压住"],
              ["v3", "加帧间平滑", "再加一阶递归", "增益抖动是否下降"],
              ["oracle", "理想 IRM", "用真实 |S|、|N| 构造", "可解释模型的上界在哪"],
          ], ["10%", "20%", "34%", "36%"]),
          ol([
              "交付 <code>code/*.py</code> 一份，参数集中在参数区，固定 <code>random.seed(7)</code> 与 <code>rng = random.Random(7)</code>。",
              "报告每个变体的 segSNR、SI-SDR、LUFS 三列数值，并注明是否做尺度对齐。",
              "报告 oracle 与 v3 的差值，说明差距来自噪声谱估计误差还是掩码函数形式。",
              "报告因果性检查：逐帧处理时是否存在未来帧依赖；给出单帧算法延迟估计。",
              "报告复现命令、产物清单（SVG / WAV 文件名与数量）与至少两个失败样本。",
              "附上 {{ch:30}} 的划分与泄漏自查表，确认没有用测试集选任何参数。",
          ]),
          warn("不要预写结论", "规格里不填任何「达到 X dB」的目标值；"
               "所有分数由脚本在读者本机打印，报告只记录实测值与口径。"
               "替换成真实语料或 PyTorch 模型后，同一份验收清单原样复用。"))),
      ("31.4", "从标准库原型到 PyTorch 工程", sec(
          ul([
              "把 <code>masked()</code> 换成可训练掩码网络："
              "<a href='https://pytorch.org/docs/stable/index.html' target='_blank' rel='noopener noreferrer'>PyTorch ↗</a>"
              " 负责张量与自动微分，"
              "<a href='https://docs.pytorch.org/audio/stable/index.html' target='_blank' rel='noopener noreferrer'>torchaudio ↗</a>"
              " 负责 STFT/ISTFT 与流式推理。",
              "训练框架与损失函数配方："
              "<a href='https://github.com/speechbrain/speechbrain' target='_blank' rel='noopener noreferrer'>SpeechBrain ↗</a>、"
              "<a href='https://github.com/asteroid-team/asteroid' target='_blank' rel='noopener noreferrer'>Asteroid ↗</a>"
              "（含 SI-SNR 损失），数据用 "
              "<a href='https://github.com/microsoft/DNS-Challenge' target='_blank' rel='noopener noreferrer'>DNS-Challenge ↗</a>。",
              "一体化增强/分离框架："
              "<a href='https://github.com/modelscope/ClearerVoice-Studio' target='_blank' rel='noopener noreferrer'>ClearerVoice-Studio ↗</a>；"
              "部署对照 "
              "<a href='https://onnxruntime.ai/' target='_blank' rel='noopener noreferrer'>ONNX Runtime ↗</a> 与 {{ch:29}} 的量化。",
              "离线链路核对用 ffmpeg 的 afftdn / arnndn / loudnorm；"
              "是否可用以本机 <code>ffmpeg -filters</code> 与官方 Filters 文档为准。",
          ]),
          note("迁移时不变的东西", "信号模型、因果约束、指标口径、数据划分、验收清单。"
               "换掉的只是 <code>G</code> 从手写阈值变成网络输出——"
               "这正是全书从 {{ch:00}} 到 {{ch:30}} 一直保持的骨架。"))),
  ],
  demos=[mk_demo(
      "code/31-capstone.py", "实验 31-1 · 理想掩码 oracle 与小型阈值掩码的消融对照",
      "用纯标准库构造 IRM 上界与四个可解释变体，打印指标三列、画出消融图与掩码热力图。",
      """N = 4096                    # 0.256 s @ 16 kHz
N_FFT, HOP = 256, 128
NOISE_AMP = 0.040
THETA = 0.65                # 阈值掩码的过减系数
FLOOR = 0.12                # 消融项 B：增益下限
SMOOTH_A = 0.55             # 消融项 C：帧间平滑系数
ORACLE_FLOOR = 0.02""",
      """rng = random.Random(7)
clean = synthetic_speech(rng, N)
wn = white_noise(rng, N, NOISE_AMP)
nz = [wn[i] + 0.35 * NOISE_AMP * math.sin(2 * math.pi * 137 * i / SAMPLE_RATE)
      for i in range(N)]
noisy = [clean[i] + nz[i] for i in range(N)]

frames_y = stft(noisy, N_FFT, HOP)
frames_s = stft(clean, N_FFT, HOP)
frames_n = stft(nz, N_FFT, HOP)
half = N_FFT // 2
ns = [sum(math.hypot(re[k], im[k]) for re, im in frames_n) / len(frames_n)
      for k in range(N_FFT)]

# oracle：用真实干净谱与噪声谱构造理想比率掩码，只作为上界
oracle_frames = []
for (ry, iy), (rs, is_), (rn, in_) in zip(frames_y, frames_s, frames_n):
    rr, ii = list(ry), list(iy)
    for k in range(N_FFT):
        ms = math.hypot(rs[k], is_[k])
        mn = math.hypot(rn[k], in_[k])
        g = max(ORACLE_FLOOR, ms / (ms + mn + 1e-9))
        rr[k] *= g
        ii[k] *= g
    oracle_frames.append((rr, ii))


def masked(theta, floor, smoothing):
    out_frames, prev = [], [0.0] * N_FFT
    for re, im in frames_y:
        rr, ii = list(re), list(im)
        for k in range(N_FFT):
            mag = math.hypot(rr[k], ii[k])
            raw = max(floor, 1.0 - theta * ns[k] / (mag + 1e-9))
            g = smoothing * prev[k] + (1.0 - smoothing) * raw if smoothing > 0.0 else raw
            prev[k] = g
            rr[k] *= g
            ii[k] *= g
        out_frames.append((rr, ii))
    return istft(out_frames, N_FFT, HOP, N)


def metrics(est):
    aligned = scale_align(est, clean)
    return seg_snr_db(clean, aligned), si_sdr_db(est, clean), lufs_approx(est)


variants = [("v0 无处理", noisy),
            ("v1 纯阈值", masked(THETA, 0.0, 0.0)),
            ("v2 加下限", masked(THETA, FLOOR, 0.0)),
            ("v3 加平滑", masked(THETA, FLOOR, SMOOTH_A)),
            ("oracle IRM", istft(oracle_frames, N_FFT, HOP, N))]
scores = [metrics(v[1]) for v in variants]

c = Chart(FIG / "31-ablation.svg", "小型掩码估计器的消融对照", xlabel="变体", ylabel="dB",
          xticks=[(i, v[0]) for i, v in enumerate(variants)])
c.bars(range(len(variants)), [s[0] for s in scores], BLUE, label="分段 SNR (尺度对齐)")
c.bars(range(len(variants)), [s[1] for s in scores], GREEN, label="SI-SDR")
c.hline(0.0, "#9aa6b2")
print("消融图:", c.save())

# 掩码热力图：行是降采样后的频率箱，列是帧
grid, prev = [], [0.0] * half
for re, im in frames_y:
    row = []
    for k in range(0, half, 8):
        mag = math.hypot(re[k], im[k])
        raw = max(FLOOR, 1.0 - THETA * ns[k] / (mag + 1e-9))
        g = SMOOTH_A * prev[k] + (1.0 - SMOOTH_A) * raw
        prev[k] = g
        row.append(round(g, 3))
    grid.append(row)
matrix = [list(col) for col in zip(*grid)]
heatmap(FIG / "31-mask.svg", matrix,
        ["%d Hz" % int(k * SAMPLE_RATE / N_FFT) for k in range(0, half, 8)],
        ["t%d" % i for i in range(len(matrix[0]))],
        title="可解释阈值掩码（行=频率箱，列=帧）", vmin=0.0, vmax=1.0)
print("掩码图:", str(FIG / "31-mask.svg"))

write_wav(AUDIO / "31-clean.wav", normalize_peak(clean))
write_wav(AUDIO / "31-noisy.wav", normalize_peak(noisy))
write_wav(AUDIO / "31-threshold.wav", normalize_peak(variants[3][1]))
write_wav(AUDIO / "31-oracle.wav", normalize_peak(variants[4][1]))
print("WAV: %d 帧 / %d Hz / %.2f s / %d 字节" % wav_info(AUDIO / "31-noisy.wav"))
for name, sc in zip([v[0] for v in variants], scores):
    print("%s: segSNR=%.2f dB SI-SDR=%.2f dB LUFS≈%.1f" % (name, sc[0], sc[1], sc[2]))
print("oracle 与阈值掩码 segSNR 差=%.2f dB | 下限增益=%.2f dB | 平滑增益=%.2f dB | SAMPLE_RATE=%d Hz" %
      (scores[4][0] - scores[3][0], scores[2][0] - scores[1][0],
       scores[3][0] - scores[2][0], SAMPLE_RATE))""",
      [("fig/31-ablation.svg", "五个变体的分段 SNR 与 SI-SDR 消融对照"),
       ("fig/31-mask.svg", "可解释阈值掩码的频率—帧热力图")],
      [("audio/31-clean.wav", "干净参考语音"),
       ("audio/31-noisy.wav", "带噪输入"),
       ("audio/31-threshold.wav", "v3 阈值掩码输出"),
       ("audio/31-oracle.wav", "理想 IRM 上界输出")],
      steps="先跑脚本看打印的五行指标，再对照 <code>31-ablation.svg</code>；"
            "依次试听 clean / noisy / threshold / oracle 四个 WAV。",
      expect="五个变体的三列指标会逐行打印；oracle 是用真实谱构造的上界，"
             "与可解释阈值掩码之间存在可观察的差距（本例约 3 dB）；增益下限与帧间平滑各自的贡献会单独打印，"
             "下限在本例略为负值，说明阈值掩码很少触底。"
             "全部数值以本机运行输出为准，不在规格里预设目标分。",
      tweak="把 <code>FLOOR</code> 设为 0、<code>SMOOTH_A</code> 设为 0，观察 v1 与 v3 的差别；"
            "把 <code>N_FFT</code> 改成 512，观察时频分辨率与耗时的变化。")],
  commands=[
      shell("本机自查 ffmpeg 滤镜清单再对照官方文档",
            "ffmpeg -hide_banner -filters | grep -E 'afftdn|arnndn|loudnorm|dynaudnorm|astats'",
            "滤镜可用性与参数以本机输出和 https://ffmpeg.org/ffmpeg-filters.html 为准，不写死版本。"),
      shell("用 Python 标准库做语法自检并运行结课脚本",
            "python3 -m compileall -q tools part6/31-capstone/code && python3 part6/31-capstone/code/31-capstone.py",
            "两条都是单行命令；先编译检查，再实跑生成 fig 与 audio 产物并打印数值。"),
  ],
  highlights=[("speechbrain", "把阈值掩码换成可训练网络的现成配方"),
              ("dns-challenge", "真实噪声与官方评测协议，替换合成数据"),
              ("ffmpeg-filters", "离线全链路核对与滤镜自查入口"),
              ("python-docs", "标准库 wave / math / random 的权威说明")],
  repos=[
      ("SpeechBrain", "https://github.com/speechbrain/speechbrain",
       "语音任务配方齐全，适合复现 SE / 掩码 / 损失函数", "AI · 框架"),
      ("Asteroid", "https://github.com/asteroid-team/asteroid",
       "语音分离与 SI-SNR 损失的研究型框架", "AI · 框架"),
      ("FFmpeg", "https://ffmpeg.org/ffmpeg-filters.html",
       "afftdn / arnndn / loudnorm / dynaudnorm 等滤镜的离线验证工具", "工具"),
  ],
  analogy="结课项目是一个带 CI 的小服务：<code>stft → 掩码 → istft</code> 是处理管线，"
          "五个变体是 feature flag 的逐级打开，oracle 是 mock 掉依赖后的理想返回值，"
          "验收清单就是合并请求模板。<strong>先让流水线可复现，再谈模型多大。</strong>",
  bridge="承接 {{ch:30}} 的评测协议，收束 {{ch:19}} 的时频掩码、{{ch:26}} 的联合 3A、"
         "{{ch:28}} 的延迟预算；附录 A 提供公式、术语、命令与复现约定的总表。",
  pitfalls=["用真实干净谱构造 oracle 后，把它当成可部署模型的分数汇报。",
            "频谱改完不做 WOLA 归一化，边界出现爆音。",
            "消融时一次改多个变量，无法把收益归因到具体项。",
            "在测试集上选阈值或改后处理，还把结果写成最终成绩。"],
  exercises=["补齐验收清单里的因果性检查：说明本实验的掩码是否只依赖当前帧及之前帧。",
             "推导 IRM 与维纳增益的关系，解释 oracle 为什么只是上界。",
             "把 v3 换成一节小型 PyTorch 掩码网络，列出需要保持不变的五项口径。"],
  further=["{{ch:30}} 评测陷阱与数据泄漏；{{ch:18}} 经典 3A 全链路基线。",
           "{{ch:19}} 时频掩码；{{ch:26}} 联合 3A；{{ch:28}} 延迟预算。"]),

# ==================================================================== A
C("A", "pa", "appendix", "附录 A · 公式、术语、命令与资源速查",
  "把全书的符号、公式、中英术语、命令与复现约定压成四张速查表；A.5～A.7 由生成器自动追加。",
  hours="1 学时",
  goals=[
      "能按主题查到全书核心公式并说明每个符号的含义。",
      "能读懂 AEC / ANS / AGC / RIR / ERLE / DNSMOS / WOLA 等中英术语。",
      "能用本机命令自查 ffmpeg 滤镜与音频电平，而不依赖书里写死的版本。",
      "能按复现约定批量运行全书实验并核对 fig / audio 产物。",
  ],
  points=["符号与公式速查", "信号模型", "NLMS 与 ERLE", "SI-SDR 与 Wiener 增益",
          "中英术语对照", "ffmpeg / WebRTC 命令", "实验环境与复现", "fig / audio 产物"],
  sections=[
      ("A.1", "全书符号与公式速查", sec(
          p("按「信号模型 → 自适应 → 指标 → 掩码与重建 → 电平」排列；"
            "公式是便于记忆的教学写法，工程实现请以 <code>tools/dsp.py</code> 与对应标准原文为准。"),
          eq("信号模型：y[n] = d[n] + (h * x)[n] + v[n] = d[n] + Σ_k h[k] x[n−k] + v[n]"),
          eq("NLMS：e[n] = d[n] − wᵀ[n] x[n]　，w[n+1] = w[n] + μ e[n] x[n] / (‖x[n]‖² + δ)"),
          eq("ERLE = 10 log₁₀( Σ e²[n] / Σ r²[n] )　，segSNR = mean_t 10 log₁₀( Σ d² / Σ (d−d̂)² )"),
          eq("SI-SDR：α = ⟨ŝ,s⟩ / ‖s‖²　，SI-SDR = 10 log₁₀( ‖α s‖² / ‖ŝ − α s‖² )"),
          eq("Wiener / IRM 增益：G[t,k] = ξ/(1+ξ) ≈ |S[t,k]|² / ( |S[t,k]|² + |N[t,k]|² )"),
          eq("WOLA 重建：x̂[n] = Σ_f X̂_f[n] w[n−fH] / Σ_f w²[n−fH]　，H = N/2"),
          eq("量化 SNR ≈ 6.02 B + 1.76 dB　，LUFS 为 K 加权加门控的响度（本书 lufs_approx 是教学近似）"),
          table(["符号", "含义", "首次出现"], [
              ["x, y, d, v", "远端参考 / 麦克风 / 近端干净语音 / 加性噪声", "{{ch:00}}"],
              ["h, w, L", "房间冲激响应 / 自适应权重 / 滤波器阶数", "{{ch:01}}"],
              ["N, H, w[·]", "FFT 长度 / 帧移 / 窗函数（Hann）", "{{ch:02}}"],
              ["μ, δ, e", "NLMS 步长 / 正则项 / 误差信号", "{{ch:05}}"],
              ["G, ξ, IRM", "时频增益 / 先验 SNR / 理想比率掩码", "{{ch:13}}、{{ch:19}}"],
              ["α, ŝ, s", "最小二乘投影系数 / 估计语音 / 目标语音", "{{ch:03}}"],
              ["B, LUFS, TP", "量化位深 / 响度单位 / 真峰值", "{{ch:02}}、{{ch:14}}"],
          ], ["18%", "58%", "24%"]))),
      ("A.2", "中英术语对照表", sec(
          p("同一概念在论文、源码与标准里常有不同写法；下表给出本书采用的中文名与英文全称。"),
          table(["缩写 / 中文", "英文全称 / 常用写法", "一句话释义"], [
              ["AEC 回声消除", "Acoustic Echo Cancellation", "用远端参考 x 预测并减去声学回声"],
              ["ANS 噪声抑制", "Acoustic Noise Suppression / Speech Enhancement", "在时频域估计增益压低加性噪声"],
              ["AGC 自动增益控制", "Automatic Gain Control", "按包络平滑调整整体电平"],
              ["RIR 房间冲激响应", "Room Impulse Response", "扬声器到麦克风的 LTI 通道 h"],
              ["ERLE", "Echo Return Loss Enhancement", "处理前后回声能量比，AEC 主指标"],
              ["DNSMOS", "Deep Noise Suppression MOS", "无需干净参考的神经语音质量分"],
              ["WOLA", "Weighted Overlap-Add", "加权重叠相加，改谱后无失真重建"],
              ["双讲", "Double-talk", "近端与远端同时说话，AEC 需冻结更新"],
              ["STFT / ISTFT", "Short-Time Fourier Transform / Inverse", "一维流与二维时频矩阵互转"],
              ["SI-SDR", "Scale-Invariant Signal-to-Distortion Ratio", "尺度不变的失真比"],
              ["NLMS", "Normalized Least Mean Squares", "按输入能量归一化步长的 LMS"],
              ["VAD", "Voice Activity Detection", "判断当前帧是否有语音"],
              ["LUFS / LKFS", "Loudness Units relative to Full Scale", "ITU-R BS.1770 响度单位"],
              ["PESQ / POLQA", "Perceptual Evaluation of Speech Quality", "有参考感知质量（P.862 / P.863）"],
              ["FDAF / MDF", "Frequency-Domain / Multi-Delay Adaptive Filter", "分块频域自适应滤波"],
              ["OOD", "Out-of-Distribution", "训练分布之外的数据，见 {{ch:30}}"],
          ], ["22%", "40%", "38%"]))),
      ("A.3", "ffmpeg / WebRTC 命令速查", sec(
          p("所有滤镜名称、参数与引入版本都以<strong>本机 <code>ffmpeg -filters</code> / "
            "<code>ffmpeg -version</code> 实际输出</strong>和 "
            "<a href='https://ffmpeg.org/ffmpeg-filters.html' target='_blank' rel='noopener noreferrer'>FFmpeg Filters 官方文档 ↗</a>"
            " 为准；本书不假定任何特定版本，也不写死版本号。"),
          table(["用途", "单行命令 / 滤镜", "自查与说明"], [
              ["列出本机滤镜", "<code>ffmpeg -hide_banner -filters | grep afftdn</code>",
               "先确认滤镜存在，再谈参数；不同编译选项结果不同"],
              ["自适应降噪", "<code>afftdn</code> / <code>anlmdn</code>",
               "FFT 自适应降噪 / 非局部均值，见官方 Filters 文档对应锚点"],
              ["神经降噪", "<code>arnndn</code>",
               "加载自备 RNNoise 模型文件，模型来源见 "
               "<a href='https://github.com/xiph/rnnoise' target='_blank' rel='noopener noreferrer'>RNNoise ↗</a>"],
              ["响度测量与归一", "<code>ebur128=peak=true</code> / <code>loudnorm</code>",
               "I / S / LRA 与 True Peak；对照 {{ch:14}} 的 AGC"],
              ["电平统计", "<code>volumedetect</code> / <code>astats=metadata=1</code>",
               "mean_volume / max_volume / RMS / 削波计数"],
              ["重采样与回声合成", "<code>aresample=16000</code> / <code>aecho</code>",
               "统一采样率、造回声测试样本，见 {{ch:01}}"],
              ["WebRTC 参考实现", "<code>modules/audio_processing/</code>",
               "AEC3 / NS / AGC2 源码目录，见 "
               "<a href='https://webrtc.googlesource.com/src/+/refs/heads/main/modules/audio_processing/' target='_blank' rel='noopener noreferrer'>webrtc-src ↗</a>"],
          ], ["18%", "40%", "42%"]),
          note("口径提醒", "命令示例只给入口，不给版本承诺；"
               "书里的 <code>lufs_approx()</code> 是教学近似，合规测量请用 ffmpeg ebur128 / loudnorm。"))),
      ("A.4", "实验环境与复现约定", sec(
          ol([
              "运行环境：Python 3 <strong>标准库即可</strong>，不需要 numpy / scipy / torch / matplotlib / librosa / soundfile。",
              "随机数：PREAMBLE 固定 <code>random.seed(7)</code>，实验内再用 <code>rng = random.Random(7)</code>，保证逐行可复算。",
              "采样率：<code>SAMPLE_RATE = 16000</code>，WAV 为 16-bit 单声道 PCM，由 <code>write_wav()</code> 写出。",
              "产物：每个脚本在章节根目录写 <code>fig/*.svg</code>（<code>Chart().save()</code> 或 <code>heatmap()</code>）"
              "与 <code>audio/*.wav</code>；文件名带本章编号前缀以避免冲突。",
              "单章运行：<code>python3 part6/31-capstone/code/31-capstone.py</code>；"
              "语法自检：<code>python3 -m py_compile tools/chapters_30_A.py</code>。",
              "批量运行：先由生成器把 demos 的 code 落到各章 <code>code/*.py</code>，"
              "再逐个 <code>python3 &lt;路径&gt;</code>；页面代码块与 code 文件由同一份数据同步，不要手改生成的 HTML。",
          ]),
          note("可核对性", "每个实验都打印可手算核对的数值（ERLE、SNR、SI-SDR、LUFS、WAV 帧数与字节数），"
               "并声明 fig / audio 的文件名；运行时间控制在几秒内。"),
          warn("边界", "全部语音、噪声与 RIR 均为代码合成信号，不是真实录音，"
               "也不是任何厂商产品的性能数据；教学实现不能直接用于生产环境。"))),
  ],
  demos=[],
  commands=[
      shell("本机自查 ffmpeg 滤镜与版本，再对照官方文档",
            "ffmpeg -hide_banner -filters | grep -E 'afftdn|arnndn|loudnorm|ebur128|astats'",
            "滤镜清单随版本与编译选项变化；以本机输出与 https://ffmpeg.org/ffmpeg-filters.html 为准，不写死版本。"),
      shell("用 Python 标准库做全书语法自检",
            "python3 -m compileall -q tools",
            "只依赖 Python 3 标准库；该命令检查语法而不运行实验，随后再逐个实跑 code/*.py。"),
  ],
  highlights=[("dspguide", "卷积、FFT 与滤波器的免费在线教材"),
              ("ffmpeg-filters", "全部音频滤镜的权威说明页"),
              ("webrtc-src", "AEC3 / NS / AGC2 的工业级参考实现目录"),
              ("python-docs", "wave / array / math / random 等标准模块说明")],
  analogy="附录是项目的 README + cheatsheet：A.1 是 API 签名，A.2 是术语词典，"
          "A.3 是常用 CLI，A.4 是「如何在干净环境里跑起来」。"
          "<strong>命令要以本机自查为准，等价于不要硬编码依赖版本。</strong>",
  bridge="全书收束。{{ch:03}} 定义指标、{{ch:17}} 实操命令、{{ch:30}} 讲评测陷阱、"
         "{{ch:31}} 给验收清单；A.5～A.7 由生成器自动补上示例总表与资源总表。",
  pitfalls=["把教学近似 lufs_approx 当成合规的 EBU R128 测量。",
            "照抄书里的滤镜名却不做本机 ffmpeg -filters 自查。",
            "手改生成的 HTML 代码块，导致与 code/*.py 不同步。",
            "换随机种子或采样率后仍直接比较旧数值。"],
  exercises=["用本机 ffmpeg -filters 列出所有含 dn 的降噪滤镜，并记录实际输出。",
             "把 A.1 的 SI-SDR 公式与 tools/dsp.py 的 si_sdr_db 逐行对照。",
             "按 A.4 的约定批量运行两个结课实验，核对声明的 SVG 与 WAV 是否全部生成。"],
  further=["{{ch:03}} 指标定义；{{ch:02}} STFT 与 WOLA；{{ch:17}} 工具链命令实操。",
           "{{ch:30}} 评测陷阱；{{ch:31}} 结课项目验收清单。"]),

]
