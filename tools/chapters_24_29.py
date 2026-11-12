#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 24～29 章：神经 3A、联合建模与实时部署三本账（因果、延迟、量化）。"""
from __future__ import annotations

from book_schema import C, eq, table
from chapter_kit import mk_demo, shell, p, ul, ol, note, warn, sec


def S(num, title, *parts):
    """构造 (编号, 标题, HTML) 原理小节。"""
    return (num, title, sec(*parts))


CH = [

# ==================================================================== 24
C("24", "p5", "part5/24-neural-aec", "神经 AEC 与回声/噪声联合抑制",
  "把远端参考接进网络：从「减掉预测回声」到「学一个残余抑制器」。",
  hours="3 学时",
  goals=["能画出神经 AEC 的三种接法并说明各自的输入输出。",
         "能解释参考信号如何作为条件输入进入网络。",
         "能量化双讲条件下固定抑制与自适应抑制的差距。",
         "能说明为什么神经方法常作为线性 AEC 的后处理而非替代。"],
  points=["线性 AEC + 神经后处理", "参考信号条件输入", "对齐与时延估计", "残余回声功率谱",
          "双讲透明度", "ERLE 与近端失真权衡", "端到端神经 AEC", "AEC Challenge"],
  sections=[
      S("24.1", "三种接法，同一个接口",
        table(["接法", "网络输入", "网络输出", "特点"], [
            ["后处理型", "误差谱 + 远端参考谱", "残余回声/噪声增益", "最稳，工业主流"],
            ["联合估计型", "麦克风谱 + 远端参考谱", "近端语音掩码", "端到端优化，需大量配对数据"],
            ["全替代型", "麦克风波形 + 远端波形", "增强波形", "无需手工 AEC，但算力与风险最高"],
        ], ["18%", "32%", "24%", "26%"]),
        p("主流工程几乎都保留线性 AEC：它有参考、可证明收敛、低算力，"
          "能把回声能量先消掉 20～30 dB；网络只处理<strong>非线性失真、路径突变与双讲残差</strong>。"
          "Micrsoft AEC Challenge 的基线也是「经典线性 AEC + 神经后处理」的组合。")),
      S("24.2", "双讲是神经 AEC 的试金石",
        eq("G[t,k] = max(G_floor, 1 − β·P̂_res[t,k] / P_e[t,k])　，P̂_res ≈ γ·|Ŷ|²"),
        p("残余回声功率无法直接观测，但线性滤波器的输出 <code>Ŷ</code> 携带「此刻应该有多少回声」的信息，"
          "把它按泄漏系数缩放就是廉价估计（WebRTC AEC3 的核心思想）。"
          "双讲时 <code>P_e</code> 中混进大量近端语音，若用静态系数抵消会把近端一起压掉；"
          "网络学到的正是「根据参考与误差的关系判断此刻该压多少」。"),
        ul(["<strong>对齐</strong>：参考信号必须先与麦克风对齐，否则网络学到的是错误的时延分布。",
            "<strong>透明度</strong>：双讲段应同时报近端 SI-SDR 与 ERLE，只看 ERLE 会奖励过度抑制。",
            "<strong>非线性</strong>：扬声器削波产生的谐波与参考不成线性关系，只能靠后处理。"]),
        note("实验口径", "本实验用一段<strong>前半段有回声、后半段无回声</strong>的受控信号，"
             "对比静态抵消系数与逐帧 oracle 抵消。"
             "量化的是「条件化估计」相对「固定参数」的价值，不是任何具体网络的性能。")),
  ],
  demos=[mk_demo(
      file="code/24-neural-aec.py",
      title="实验 24-1 · 时变残余回声下的静态抵消 vs 逐帧 oracle 抵消",
      doc="构造前半段有回声、后半段无回声的受控场景，量化静态系数与逐帧估计的差距。",
      params="""N = 8000
LEAK_FIRST = 0.50        # 前半段线性 AEC 残留的回声比例
LEAK_SECOND = 0.00       # 后半段远端静音 / 路径变化后不再有回声
STATIC_ALPHA = 0.25      # 静态抵消固定使用的系数""",
      body="""rng = random.Random(7)
far = synthetic_speech(rng, N)
near = synthetic_speech(rng, N)
h = rir(rng, 128, decay=0.006)
echo_full = [1.4 * v for v in fft_convolve(far, h)[:N]]
alpha = [LEAK_FIRST if i < N // 2 else LEAK_SECOND for i in range(N)]
res_echo = [alpha[i] * echo_full[i] for i in range(N)]
noise = white_noise(rng, N, 0.003)

def run(near_gain, mode):
    clean = [near_gain * near[i] for i in range(N)]
    linear = [clean[i] + res_echo[i] + noise[i] for i in range(N)]
    if mode == "linear":
        out = linear
    elif mode == "static":
        out = [linear[i] - STATIC_ALPHA * echo_full[i] for i in range(N)]
    else:
        out = [linear[i] - alpha[i] * echo_full[i] for i in range(N)]
    residual = [out[i] - clean[i] for i in range(N)]
    return erle_db(res_echo, residual), seg_snr_db(clean, scale_align(out, clean)), out
conditions = (("单讲", 0.30), ("双讲", 0.90))
modes = (("线性AEC", "linear"), ("静态抵消", "static"), ("逐帧抵消", "adaptive"))
erles, snrs, labels = [], [], []
for cname, ng in conditions:
    for mname, mode in modes:
        e, s, out = run(ng, mode)
        erles.append(e)
        snrs.append(s)
        labels.append(cname + "-" + mname)
        if cname == "双讲" and mode == "linear":
            linear_dt = out
        if cname == "双讲" and mode == "adaptive":
            adaptive_dt = out
c = Chart(FIG / "24-aec.svg", "单讲/双讲下三种方案的 ERLE 与分段 SNR", xlabel="场景-方案", ylabel="dB",
          xticks=[(i, l) for i, l in enumerate(labels)])
c.bars(range(len(labels)), erles, BLUE, label="ERLE (dB)")
c.bars(range(len(labels)), snrs, GREEN, label="分段 SNR (dB)")
print("AEC图:", c.save())
heatmap(FIG / "24-matrix.svg", [erles, snrs], ["ERLE", "分段 SNR"], labels,
        title="六组实验的指标矩阵", vmin=-10, vmax=35, annotate=True)
print("矩阵图:", str(FIG / "24-matrix.svg"))
write_wav(AUDIO / "24-linear.wav", normalize_peak(linear_dt))
write_wav(AUDIO / "24-adaptive.wav", normalize_peak(adaptive_dt))
for l, e, s in zip(labels, erles, snrs):
    print("%s: ERLE=%.2f dB segSNR=%.2f dB" % (l, e, s))
print("SAMPLE_RATE=%d | 前半段泄漏=%.2f 后半段=%.2f 静态系数=%.2f" %
      (SAMPLE_RATE, LEAK_FIRST, LEAK_SECOND, STATIC_ALPHA))""",
      figs=[("fig/24-aec.svg", "三种方案在单讲/双讲下的指标"),
            ("fig/24-matrix.svg", "六组实验的指标矩阵")],
      audio=[("audio/24-linear.wav", "双讲：仅线性 AEC，前半段有残余回声"),
             ("audio/24-adaptive.wav", "双讲：逐帧抵消后的输出")],
      steps="重点比较双讲三组的分段 SNR；试听两个双讲 WAV。",
      expect="静态系数在前半段只抵消了一部分回声，后半段远端已静音却仍继续减，"
             "等于<strong>凭空往输出里加入反向回声</strong>，近端语音被明显损伤；"
             "逐帧估计随路径变化更新，两项指标都更好。这正是双讲与路径突变下"
             "必须用条件化的神经后处理替代固定增益的原因。",
      tweak="把 STATIC_ALPHA 改成 0.50，前半段抵消更准，但后半段的反向回声也更强。")],
  commands=[shell("查看 AEC Challenge 的数据与基线说明",
                  "git clone --depth 1 https://github.com/microsoft/AEC-Challenge && ls AEC-Challenge/",
                  "该仓库提供真实双讲、非线性失真与远端单讲录音；请以其 README 与许可为准，"
                  "本书实验全部使用合成信号。")],
  highlights=[("aec-challenge", "真实双讲与非线性失真的标准评测集"),
              ("clearervoice", "开源增强/分离框架里的 AEC 相关配方"),
              ("webrtc-aec3", "线性滤波输出用于残余回声估计的工业范例"),
              ("speechbrain", "条件输入与多任务训练的参考实现")],
  repos=[("Microsoft AEC-Challenge", "https://github.com/microsoft/AEC-Challenge",
          "真实双讲、非线性失真与远端单讲录音", "数据集 · 基线"),
         ("WebRTC audio_processing", "https://webrtc.googlesource.com/src/+/refs/heads/main/modules/audio_processing/",
          "AEC3 的残余回声估计与双讲处理源码", "传统 · C++")],
  analogy="神经 AEC 是一个「有第二个输入端口的掩码估计器」："
          "远端参考是条件变量，网络学的是条件分布 p(近端谱 | 麦克风谱, 参考谱)。",
  bridge="{{ch:23}} 处理无参考的噪声，本章把参考信号接回来；"
         "{{ch:25}} 处理增益，{{ch:26}} 把三个任务合到一个模型里。",
  pitfalls=["忘记对齐参考与麦克风，网络学到错误的时延。",
            "只报单讲 ERLE，忽略双讲段的近端失真。",
            "用线性 AEC 的输出直接当标签，把残余回声也标成干净语音。",
            "把 oracle 残余功率谱当成网络可观测输入。"],
  exercises=["画出后处理型神经 AEC 的张量流图并标注因果性。",
             "解释为什么工业系统保留线性 AEC 而不做全替代。",
             "设计一组同时报 ERLE 与双讲透明度的评测表。"],
  further=["{{ch:11}} 残余回声抑制；{{ch:26}} 联合 3A；{{ch:30}} 泛化。"]),

# ==================================================================== 25
C("25", "p5", "part5/25-neural-agc", "神经增益控制与感知响度",
  "把 AGC 的固定目标电平换成从数据里学出来的一条增益律。",
  hours="3 学时",
  goals=["能把 AGC 写成「输入电平 → 增益」的可学习映射。",
         "能说明感知响度目标与 RMS 目标的区别。",
         "能用最小二乘拟合一条增益律并在留出电平上验证。",
         "能解释为什么工业系统仍保留传统 AGC 与限幅器。"],
  points=["电平到增益的映射", "感知偏好数据", "对数域最小二乘", "响度与 RMS 目标",
          "增益约束与钳位", "留出电平验证", "混合部署", "增益泵浦"],
  sections=[
      S("25.1", "AGC 其实是一维回归",
        eq("g = f_θ(L_in)　，传统: f = L_target / L_in　；学习: log g = a·log L_in + b"),
        p("{{ch:14}} 的 AGC 把目标电平写死成一个常数 <code>L_target</code>。"
          "但真实偏好随内容与输入电平变化：轻声说话时希望多抬一点，"
          "响亮段落则宁可少抬以避免背景噪声被放大。"
          "把它看成<strong>一维回归</strong>，就能从标注了偏好响度的数据里拟合 <code>f_θ</code>。"),
        table(["方案", "目标", "优点", "风险"], [
            ["无 AGC", "保持原样", "零失真", "电平起伏大"],
            ["固定目标 AGC", "恒到 L_target", "简单可证明", "弱段底噪被抬起"],
            ["学习增益律", "拟合偏好曲线", "听感更自然", "需要标注、分布外可能失控"],
            ["传统 + 神经混合", "神经给目标、传统做环路", "平滑、有安全边界", "两套状态需同步"],
        ], ["20%", "24%", "26%", "30%"])),
      S("25.2", "安全边界比拟合精度更重要",
        ul(["<strong>钳位</strong>：增益必须限制在 <code>[g_min, g_max]</code>，"
            "否则分布外输入会直接把信号推到削波。",
            "<strong>平滑</strong>：网络逐帧给的目标仍要经过攻击/释放一阶平滑，"
            "避免增益跳变（{{ch:14}}）。",
            "<strong>限幅</strong>：最后一级必须是确定性限幅器，不能交给网络兜底。",
            "<strong>评测</strong>：同时报响度偏差、峰值余量与语音失真，"
            "只用 LUFS 会奖励把一切都压到同一响度。"]),
        note("实验口径", "本实验用一条<strong>人为设定的偏好曲线</strong>生成标注，"
             "再用对数域最小二乘拟合两参数模型，并在未参与拟合的电平上验证。"
             "它演示的是「可学习增益律」的机制，不是任何产品的听感数据。")),
  ],
  demos=[mk_demo(
      file="code/25-neural-agc.py",
      title="实验 25-1 · 拟合增益律并在留出电平上比较三种 AGC",
      doc="用合成偏好响度拟合对数域增益律，比较无 AGC、固定目标与学习增益律的响度偏差。",
      params="""N = 4000
LEVELS = (0.08, 0.15, 0.30, 0.50, 0.80, 1.20)
TRAIN_N = 4                 # 前 4 个电平用于拟合，后 2 个留出验证
FIXED_TARGET = 0.16
G_MIN, G_MAX = 0.20, 8.0""",
      body="""rng = random.Random(7)
base = synthetic_speech(rng, N)
def pref(level):
    return 0.10 + 0.06 * (1.0 - math.exp(-3.0 * level))
signals = [(L, [L * base[i] for i in range(N)]) for L in LEVELS]
xs, ys = [], []
for L, x in signals[:TRAIN_N]:
    r = rms(x) + 1e-9
    xs.append(math.log10(r))
    ys.append(math.log10(pref(L) / r))
mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
var = sum((v - mx) ** 2 for v in xs)
cov = sum((xs[i] - mx) * (ys[i] - my) for i in range(len(xs)))
a = cov / (var + 1e-12)
b = my - a * mx
rows = []
for L, x in signals:
    r = rms(x) + 1e-9
    gains = [1.0, min(G_MAX, FIXED_TARGET / r),
             max(G_MIN, min(G_MAX, 10 ** (a * math.log10(r) + b)))]
    outs = [clip([v * g for v in x]) for g in gains]
    rows.append((L, [rms(o) for o in outs], gains, outs, pref(L)))
c = Chart(FIG / "25-levels.svg", "各输入电平下的输出 RMS 与偏好曲线",
          xlabel="输入电平", ylabel="RMS", xticks=[(i, "%.2f" % L) for i, L in enumerate(LEVELS)])
c.line(range(len(LEVELS)), [r[1][0] for r in rows], "#9aa6b2", label="无 AGC")
c.line(range(len(LEVELS)), [r[1][1] for r in rows], BLUE, label="固定目标 AGC")
c.line(range(len(LEVELS)), [r[1][2] for r in rows], GREEN, label="学习增益律")
c.line(range(len(LEVELS)), [r[4] for r in rows], RED, label="偏好曲线")
print("电平图:", c.save())
g = Chart(FIG / "25-gains.svg", "固定目标与学习增益律的增益曲线",
          xlabel="输入电平", ylabel="增益", xticks=[(i, "%.2f" % L) for i, L in enumerate(LEVELS)])
g.line(range(len(LEVELS)), [r[2][1] for r in rows], BLUE, label="固定目标")
g.line(range(len(LEVELS)), [r[2][2] for r in rows], GREEN, label="学习增益律")
print("增益图:", g.save())
write_wav(AUDIO / "25-quiet.wav", normalize_peak(signals[0][1]))
write_wav(AUDIO / "25-learned.wav", rows[0][3][2])
mae = [sum(abs(r[1][m] - r[4]) for r in rows) / len(rows) for m in range(3)]
held = [sum(abs(r[1][m] - r[4]) for r in rows[TRAIN_N:]) / (len(rows) - TRAIN_N) for m in range(3)]
clips = sum(1 for r in rows for v in r[3][2] if abs(v) >= 0.999)
print("拟合: log g = %.3f * log L_in + %.3f | 训练电平=%d 留出=%d" % (a, b, TRAIN_N, len(LEVELS) - TRAIN_N))
print("响度偏差 MAE 无AGC=%.4f 固定=%.4f 学习=%.4f | 留出集: %.4f/%.4f/%.4f" %
      (mae[0], mae[1], mae[2], held[0], held[1], held[2]))
print("学习增益钳位样本=%d | SAMPLE_RATE=%d | 偏好曲线为人为设定" % (clips, SAMPLE_RATE))""",
      figs=[("fig/25-levels.svg", "三种方案的输出 RMS 与偏好曲线"),
            ("fig/25-gains.svg", "固定目标与学习增益律的增益曲线")],
      audio=[("audio/25-quiet.wav", "低电平输入"),
             ("audio/25-learned.wav", "学习增益律处理后的输出")],
      steps="对照留出电平上的响度偏差；把 TRAIN_N 改成 2 观察外推误差。",
      expect="学习增益律在训练区间内明显更贴近偏好曲线；但在未参与拟合的电平上，"
             "两参数模型的外推误差可能反超固定目标 AGC（本例留出集即是如此）。"
             "<strong>这正说明留出验证、增益钳位、平滑与确定性限幅缺一不可</strong>。",
      tweak="把 LEVELS 增加一档 3.0（远超训练范围），观察外推时钳位是否生效。")],
  commands=[shell("用 ffmpeg loudnorm 核对学习增益律的输出响度",
                  "ffmpeg -hide_banner -i out.wav -af ebur128=peak=true -f null - 2>&1 | tail -12",
                  "ebur128 给出合规的积分响度与真峰值；本书 lufs_approx 只是教学近似。"
                  "滤镜可用性以本机 `ffmpeg -filters` 与 https://ffmpeg.org/ffmpeg-filters.html 为准。")],
  highlights=[("ffmpeg-loudnorm", "合规响度归一化的对照实现"),
              ("ebu-r128", "响度目标与真峰值规范"),
              ("itu-bs1770", "K 加权与 LUFS 的算法来源"),
              ("dnsmos", "无参考评分可用来校准感知偏好")],
  repos=[("FFmpeg", "https://ffmpeg.org/ffmpeg-filters.html",
          "loudnorm / dynaudnorm / speechnorm 的离线验证工具", "工具"),
         ("DNSMOS", "https://github.com/microsoft/DNS-Challenge/tree/master/DNSMOS",
          "无参考神经 MOS，可用于偏好数据的辅助标注", "评测")],
  analogy="学习 AGC 是把控制器里的常数 <code>L_target</code> 换成一个查表/回归函数；"
          "执行层仍是一阶平滑 + 钳位 + 限幅，网络只负责给目标值。",
  bridge="{{ch:24}} 学残余抑制，本章学增益，{{ch:26}} 把 AEC / ANS / AGC 三个目标合并；"
         "{{ch:28}} 会把这些模块的延迟一起算进预算。",
  pitfalls=["让网络直接输出逐样本增益，不经平滑导致增益跳变。",
            "没有增益钳位与确定性限幅器，分布外输入直接削波。",
            "只用 LUFS 偏差做评测，忽略语音失真与泵浦。",
            "把人为设定的偏好曲线当成真实用户数据。"],
  exercises=["推导对数域最小二乘的 a、b 闭式解。",
             "解释为什么增益仍需攻击/释放平滑。",
             "设计一个能暴露外推失效的留出集。"],
  further=["{{ch:14}} 传统 AGC；{{ch:26}} 联合 3A；{{ch:30}} 泛化。"]),

# ==================================================================== 26
C("26", "p5", "part5/26-joint-3a", "联合 3A：多任务、级联与端到端建模",
  "三个目标共用一个模型时，真正要调的不是网络深度，而是损失与约束。",
  hours="4 学时",
  goals=["能比较级联式、多任务式与端到端式三种联合 3A 结构。",
         "能写出多任务损失并解释权重对结果的影响。",
         "能量化 AEC / ANS / AGC 三个校正加权后的权衡曲面。",
         "能说明联合模型的失效模式与可观测性代价。"],
  points=["级联与联合", "多任务损失", "损失权重与 Pareto 前沿", "共享编码器",
          "任务冲突与负迁移", "端到端可微分链路", "可观测性下降", "消融实验"],
  sections=[
      S("26.1", "三种结构，一条链路",
        eq("L = λ₁·L_AEC + λ₂·L_ANS + λ₃·L_AGC + λ₄·L_SI-SDR"),
        table(["结构", "模块关系", "优点", "缺点"], [
            ["级联式", "AEC → NS → AGC 各自独立", "可定位失效、可分别调优", "误差逐级累积，无法联合优化"],
            ["多任务式", "共享编码器 + 三个输出头", "特征复用、算力省", "任务冲突时负迁移"],
            ["端到端式", "一个网络直接输出波形", "全局目标最优", "需要海量数据、可解释性最差"],
        ], ["16%", "30%", "26%", "28%"]),
        p("从 {{ch:16}} 的级联顺序到本章的联合模型，<strong>不变量一个都没少</strong>："
          "参考信号必须未经加工、因果性不能破、AGC 之后评测要尺度对齐。"
          "变的是「谁来负责每一项误差」从三个模块变成一个损失组合。")),
      S("26.2", "权重不是超参，是产品规格",
        ul(["<strong>任务冲突</strong>：AEC 想压掉远端相关成分，ANS 想保留一切像语音的成分；"
            "双讲时二者方向相反，需要显式的双讲条件或任务门控。",
            "<strong>Pareto 前沿</strong>：把 λ 扫一遍画出 ERLE—segSNR 曲线，"
            "才能说明「没有免费午餐」，单点分数没有意义。",
            "<strong>消融</strong>：必须单独关掉每个任务头，验证它确实有贡献；"
            "否则共享编码器可能只是把最简单的任务做对了。",
            "<strong>可观测性</strong>：级联链路能旁路定位，端到端模型出问题只能靠输入/输出对比。"]),
        note("实验口径", "本实验构造三种彼此独立的退化（回声、噪声、时变电平），"
             "并给出三个只在自己那一轴上有效的 oracle 校正；权重之和固定为 1，"
             "模拟「多任务头共享有限容量」。扫描权重画出权衡曲面，"
             "不代表任何真实多任务网络的训练结果。")),
  ],
  demos=[mk_demo(
      file="code/26-joint-3a.py",
      title="实验 26-1 · 三类 oracle 校正的加权扫描与权衡曲面",
      doc="构造回声、噪声、时变电平三种退化与三个 oracle 校正，扫描权重画出综合得分热力图。",
      params="""N = 6000
LEVEL_MIN, LEVEL_SWING = 0.85, 0.15   # 时变电平（AGC 要修的退化）
GRID = (0.0, 0.25, 0.50, 0.75, 1.00)""",
      body="""rng = random.Random(7)
clean = synthetic_speech(rng, N)
far = synthetic_speech(rng, N)
h = rir(rng, 128, decay=0.006)
echo = [0.35 * v for v in fft_convolve(far, h)[:N]]
noise = white_noise(rng, N, 0.070)
level = [LEVEL_MIN + LEVEL_SWING * math.sin(2 * math.pi * i / N) for i in range(N)]
base = [clean[i] + echo[i] + noise[i] for i in range(N)]
y = [level[i] * base[i] for i in range(N)]
# 三个 oracle 校正：各自只负责一种退化，权重之和为 1 意味着算力/预算被分摊
corr_aec = [-level[i] * echo[i] for i in range(N)]
corr_ans = [-level[i] * noise[i] for i in range(N)]
corr_agc = [(1.0 - level[i]) * base[i] for i in range(N)]
echo_scaled = [level[i] * echo[i] for i in range(N)]

def task_score(w):
    return min(35.0, -20.0 * math.log10(max(1e-4, 1.0 - w)))
def apply(w1, w2):
    w3 = 1.0 - w1 - w2
    out = [y[i] + w1 * corr_aec[i] + w2 * corr_ans[i] + w3 * corr_agc[i] for i in range(N)]
    residual = [out[i] - clean[i] for i in range(N)]
    e = erle_db(echo_scaled, residual)
    s = seg_snr_db(clean, scale_align(out, clean))
    tasks = [task_score(w) for w in (w1, w2, w3)]
    return min(tasks), tasks, out, e, s
matrix, best = [], (-1e9, 0.0, 0.0, None)
for w1 in GRID:
    row = []
    for w2 in GRID:
        if w1 + w2 > 1.0 + 1e-9:
            row.append(-20.0)
            continue
        score, tasks, out, e, s = apply(w1, w2)
        row.append(round(score, 2))
        if score > best[0]:
            best = (score, w1, w2, out)
    matrix.append(row)
eq_out = apply(1.0 / 3, 1.0 / 3)[2]
a1, a2, a3 = apply(0.75, 0.15), apply(1.0 / 3, 1.0 / 3), apply(0.15, 0.75)
c = Chart(FIG / "26-grid.svg", "三种权重下三个任务各自的抑制比", xlabel="权重组合", ylabel="dB",
          xticks=[(0, "偏AEC"), (1, "均衡"), (2, "偏ANS")])
for j, (name, color) in enumerate((("AEC 抑制比", BLUE), ("ANS 抑制比", GREEN), ("AGC 抑制比", AMBER))):
    dx = (j - 1) * 0.24
    c.bars([i + dx for i in range(3)], [a[1][j] for a in (a1, a2, a3)], color, label=name)
print("任务图:", c.save())
heatmap(FIG / "26-surface.svg", matrix,
        ["w1=%.2f" % v for v in GRID], ["w2=%.2f" % v for v in GRID],
        title="最短板得分 min(S_aec,S_ans,S_agc) 的权重曲面", vmin=-20, vmax=12, annotate=True)
print("曲面图:", str(FIG / "26-surface.svg"))
write_wav(AUDIO / "26-equal.wav", normalize_peak(eq_out))
write_wav(AUDIO / "26-best.wav", normalize_peak(best[3]))
for name, a in (("偏AEC", a1), ("均衡", a2), ("偏ANS", a3)):
    print("%s 三项抑制比(AEC/ANS/AGC)=%.1f/%.1f/%.1f dB | 最短板=%.1f dB" %
          (name, a[1][0], a[1][1], a[1][2], a[0]))
print("最短板最优=%.2f dB (w1=%.2f w2=%.2f w3=%.2f) | SAMPLE_RATE=%d" %
      (best[0], best[1], best[2], 1.0 - best[1] - best[2], SAMPLE_RATE))""",
      figs=[("fig/26-grid.svg", "三种权重下各任务的抑制比"),
            ("fig/26-surface.svg", "最短板得分的权重曲面")],
      audio=[("audio/26-equal.wav", "三个任务等权重的输出"),
             ("audio/26-best.wav", "扫描得到的最优权重输出")],
      steps="观察哪个权重组合让三项抑制比都不至于太低；对照热力图的高分区位置。",
      expect="偏重任一任务都会让另外两项成为短板：偏 AEC 时 ANS/AGC 抑制比只有 1 dB 左右，偏 ANS 时反之。"
             "以「最短板」为综合分时，最优落在三项都不太低的内部区域（本例网格上为 "
             "<code>w1=w2=0.25, w3=0.50</code>）。"
             "<strong>λ 的选择本质上是产品规格，不是纯调参</strong>。",
      tweak="把综合分改成 0.4*ERLE+segSNR（单一指标），最优点会跑到角落——这正是单指标评测的陷阱。")],
  commands=[shell("查看多任务/联合增强的开源配方",
                  "git clone --depth 1 https://github.com/modelscope/ClearerVoice-Studio && ls ClearerVoice-Studio/",
                  "该框架含增强、分离与超分的多任务配方；请以其 README 与许可为准，"
                  "本书实验不依赖 PyTorch。")],
  highlights=[("speechbrain", "多任务训练与损失组合的参考实现"),
              ("clearervoice", "增强/分离/超分一体化框架"),
              ("asteroid", "SI-SDR 与多任务损失实现"),
              ("dns-challenge", "联合任务的训练数据与基线")],
  repos=[("ClearerVoice-Studio", "https://github.com/modelscope/ClearerVoice-Studio",
          "语音增强/分离/超分一体化训练与推理框架", "AI · 框架"),
         ("SpeechBrain", "https://github.com/speechbrain/speechbrain",
          "多任务语音配方齐全，适合复现损失组合", "AI · 框架")],
  analogy="多任务学习是共享底座 + 三个 head，损失权重 λ 就是三个 SLO 的优先级；"
          "扫 λ 相当于画系统的 Pareto 前沿。",
  bridge="{{ch:24}}～{{ch:25}} 分头替换模块，本章合并；"
         "{{ch:27}} 起转入部署三本账：因果、延迟、量化。",
  pitfalls=["把三个任务的损失直接相加而不做量级归一化。",
            "只报综合得分，不画 ERLE—segSNR 权衡曲线。",
            "不做任务消融就宣称多任务带来收益。",
            "联合后丢掉级联链路的旁路定位能力却没有补偿监控。"],
  exercises=["写出含四项的多任务损失并说明每项的量级。",
             "解释双讲时 AEC 与 ANS 目标为何冲突。",
             "设计一组能验证「共享编码器是否真的有用」的消融。"],
  further=["{{ch:16}} 级联顺序；{{ch:27}} 因果性；{{ch:30}} 泛化。"]),

# ==================================================================== 27
C("27", "p6", "part6/27-causal-streaming", "因果性与流式推理：状态缓存、感受野",
  "实时不是「跑得快」，而是「输出第 n 个样本时绝不看第 n+1 个」。",
  hours="3 学时",
  goals=["能给出因果系统的形式定义并识别常见违规写法。",
         "能实现分块流式处理并验证它与离线因果处理逐样本一致。",
         "能量化非因果前瞻带来的「虚假提前量」。",
         "能列出 TCN / RNN / 注意力各自的状态缓存内容。"],
  points=["因果性定义", "算法前瞻与延迟", "分块流式处理", "状态缓存",
          "膨胀卷积感受野", "RNN 隐状态", "注意力 KV 缓存", "流式与离线等价"],
  sections=[
      S("27.1", "因果是一条单元测试",
        eq("因果: y[n] = f(x[0..n], state[n−1])　；非因果: y[n] = f(x[0..n+L])"),
        p("判断是否因果有个笨但可靠的办法：<strong>把输入在 n+1 处截断，输出 y[0..n] 必须一模一样</strong>。"
          "双向 RNN、非因果卷积、整段归一化、全局注意力都会破坏这条性质。"
          "离线论文里漂亮的数字若用了未来帧，在实时链路上要么删掉，要么把前瞻时间加进延迟预算。"),
        table(["结构", "需要的状态", "感受野", "流式可行性"], [
            ["因果 TCN", "每层最后 (K−1)·d 个样本", "由膨胀系数决定", "好，状态大小可预算"],
            ["GRU / LSTM", "隐状态向量", "理论无限", "好，但逐帧串行"],
            ["因果注意力", "KV 缓存", "窗口长度", "可以，内存随窗口增长"],
            ["双向 / 整段归一化", "整段输入", "全序列", "不可流式，只能离线"],
        ], ["20%", "30%", "24%", "26%"])),
      S("27.2", "分块推理的正确性契约",
        ul(["<strong>状态即接口</strong>：每个模块暴露 <code>reset()</code> 与 "
            "<code>process(block) -> (block, state)</code>，状态必须显式传递，不能藏在全局里。",
            "<strong>等价性测试</strong>：把长信号按 10 ms 切块逐块跑，"
            "与把整段一次性跑因果版本的结果应当在浮点误差内一致。",
            "<strong>边界</strong>：STFT 的帧覆盖、卷积的左填充、AGC 的包络初值都会导致首块差异，"
            "需要预热或固定初值。",
            "<strong>延迟</strong>：状态缓存本身不增加延迟，但为凑齐一个块而产生的等待会（{{ch:28}}）。"]),
        note("实验口径", "用一个 k 点滑动平均代表「有状态的平滑器」，"
             "比较离线因果版、分块流式版与中心化（非因果）版，"
             "把「用未来帧换来的提前量」变成一个可测的样本数。")),
  ],
  demos=[mk_demo(
      file="code/27-causal-streaming.py",
      title="实验 27-1 · 因果、非因果与分块流式的一致性及前瞻量",
      doc="实现三种滑动平均，验证流式与离线因果逐样本一致，并测量非因果前瞻。",
      params="""N = 6000
K = 64                   # 平滑窗口（样本）
BLOCK = 256              # 流式分块大小（16 ms @ 16 kHz）""",
      body="""def causal_ma(x, k):
    out, acc = [], 0.0
    for i, v in enumerate(x):
        acc += v
        if i >= k:
            acc -= x[i - k]
        out.append(acc / min(i + 1, k))
    return out
def centered_ma(x, k):
    half, out = k // 2, []
    for i in range(len(x)):
        seg = x[max(0, i - half):min(len(x), i + half + 1)]
        out.append(sum(seg) / len(seg))
    return out
def stream_ma(x, k, block):
    out, hist = [], []
    for s in range(0, len(x), block):
        for v in x[s:s + block]:
            hist.append(v)
            if len(hist) > k:
                hist.pop(0)
            out.append(sum(hist) / len(hist))
    return out

step = [0.0 if i < N // 3 else 1.0 for i in range(N)]
env_c, env_n, env_s = causal_ma(step, K), centered_ma(step, K), stream_ma(step, K, BLOCK)
maxdiff = max(abs(a - b) for a, b in zip(env_c, env_s))
def cross(env):
    for i, v in enumerate(env):
        if v >= 0.5:
            return i
    return len(env)
lag = cross(env_c) - cross(env_n)
rng = random.Random(7)
speech = synthetic_speech(rng, N)
raw_env = rolling_rms(speech, 128)
smooth_c = causal_ma(raw_env, K)
smooth_n = centered_ma(raw_env, K)
c = Chart(FIG / "27-streaming.svg", "阶跃响应：因果 / 非因果 / 分块流式", xlabel="样本", ylabel="平滑值")
c.line(range(0, N, 20), [step[i] for i in range(0, N, 20)], "#9aa6b2", label="输入阶跃")
c.line(range(0, N, 20), [env_c[i] for i in range(0, N, 20)], BLUE, label="因果 / 流式")
c.line(range(0, N, 20), [env_n[i] for i in range(0, N, 20)], RED, label="中心化（非因果）")
print("阶跃图:", c.save())
e = Chart(FIG / "27-envelope.svg", "语音包络：因果平滑 vs 非因果平滑", xlabel="样本 / 40", ylabel="RMS")
e.line(range(0, N, 40), [raw_env[i] for i in range(0, N, 40)], "#9aa6b2", label="原始包络")
e.line(range(0, N, 40), [smooth_c[i] for i in range(0, N, 40)], BLUE, label="因果")
e.line(range(0, N, 40), [smooth_n[i] for i in range(0, N, 40)], RED, label="非因果")
print("包络图:", e.save())
carrier = tone(440, N, amp=0.30)
write_wav(AUDIO / "27-causal.wav", [carrier[i] * env_c[i] for i in range(N)])
write_wav(AUDIO / "27-noncausal.wav", [carrier[i] * env_n[i] for i in range(N)])
print("流式 vs 离线因果 最大误差=%.2e | 状态缓存=%d 样本 | 分块=%d 样本" %
      (maxdiff, K - 1, BLOCK))
print("非因果提前量=%d 样本 = %.2f ms | 阶跃位置=%d | SAMPLE_RATE=%d" %
      (lag, 1000.0 * lag / SAMPLE_RATE, N // 3, SAMPLE_RATE))""",
      figs=[("fig/27-streaming.svg", "三种平滑器的阶跃响应"),
            ("fig/27-envelope.svg", "语音包络的因果与非因果平滑")],
      audio=[("audio/27-causal.wav", "因果包络调制的音调：起音在阶跃之后"),
             ("audio/27-noncausal.wav", "非因果包络调制的音调：起音提前出现")],
      steps="核对流式与离线因果的最大误差；试听两个 WAV 的起音先后。",
      expect="分块流式与离线因果逐样本一致（浮点误差量级）；"
             "中心化平滑在阶跃之前就开始上升，这段「提前量」正是它不可实时的证据，"
             "若强行上线必须把同等时间计入算法延迟。",
      tweak="把 K 改成 128，提前量与状态缓存都约翻倍。")],
  commands=[shell("查看流式推理与 STFT 缓存的工业接口",
                  "python3 -c \"import torchaudio; print(torchaudio.__version__)\"",
                  "torchaudio 的流式 STFT / 缓存接口见 https://docs.pytorch.org/audio/stable/index.html ；"
                  "本机未必安装，本书实验不依赖它。")],
  highlights=[("torchaudio", "流式 STFT 与缓存的工业接口"),
              ("onnxruntime", "有状态推理的运行时参考"),
              ("rnnoise", "逐帧 GRU 状态复用的工程范例"),
              ("rfc3550", "实时链路里时间戳与抖动的来源")],
  repos=[("ONNX Runtime", "https://onnxruntime.ai/",
          "端侧有状态推理与量化部署的常用运行时", "部署"),
         ("RNNoise", "https://github.com/xiph/rnnoise",
          "逐帧 GRU 状态复用的实时降噪实现", "AI · C")],
  analogy="流式推理就是「把无状态函数改成带 state 的迭代器」："
          "同一份权重、同一份计算图，只是把历史窗口显式存在结构体里。",
  bridge="{{ch:26}} 完成模型结构，本章给出流式的正确性判据；"
         "{{ch:28}} 把这些状态与等待时间折成延迟预算，{{ch:29}} 再压缩算力。",
  pitfalls=["用双向层或整段归一化，却在报告里写「实时」。",
            "把状态藏在全局变量里，多路并发时串线。",
            "忽略首块预热，导致上线后第一句异常。",
            "只测吞吐不测最坏单帧耗时。"],
  exercises=["写出 process(block, state) 的接口契约与等价性测试。",
             "估算 5 层膨胀 TCN 需要缓存多少历史样本。",
             "解释为什么「提前量」不能通过提高算力消除。"],
  further=["{{ch:28}} 延迟预算；{{ch:29}} 量化；{{ch:31}} 结课项目。"]),

# ==================================================================== 28
C("28", "p6", "part6/28-latency-budget", "延迟预算与 RTF：实时链路账本",
  "把「能不能实时」写成一张可以逐行相加、可以实测核对的表。",
  hours="3 学时",
  goals=["能列出端到端延迟的各个组成项并给出量级。",
         "能计算实时因子 RTF 并说明它与吞吐的区别。",
         "能用计时实测一段处理链路的 RTF 并与预算对照。",
         "能说明延迟超标时该按什么顺序优化。"],
  points=["端到端延迟", "算法延迟", "帧长与前瞻", "缓冲与抖动", "编解码延迟",
          "实时因子 RTF", "最坏单帧耗时", "预算优化顺序"],
  sections=[
      S("28.1", "延迟是一张账本，不是一个数字",
        eq("T_total = T_capture + T_frame + T_algo + T_jitter + T_codec + T_network"),
        table(["组成", "典型量级", "由谁决定", "能否压缩"], [
            ["采集 / 播放缓冲", "5～20 ms", "驱动与 OS", "有限"],
            ["帧长与 WOLA", "10～32 ms", "STFT 参数", "可，但影响频率分辨率"],
            ["算法前瞻", "0～32 ms", "是否因果", "因果化可归零"],
            ["神经推理", "1～10 ms", "模型 MACs 与硬件", "可，见 {{ch:29}}"],
            ["抖动缓冲", "20～100 ms", "网络 RTT 抖动", "由网络决定"],
            ["编解码", "5～30 ms", "codec 帧长与前瞻", "换低延迟 codec"],
        ], ["22%", "20%", "28%", "30%"]),
        p("ITU-T G.114 常把单向 150 ms 作为通话可接受的粗略上界；"
          "3A 处理通常只被允许占用其中很小一块（十毫秒量级）。"
          "<strong>先定预算再选模型</strong>，而不是先训出一个大模型再想办法塞进去。")),
      S("28.2", "RTF 与最坏耗时",
        eq("RTF = T_计算 / T_音频时长　；实时条件: RTF < 1 且 P99 单帧耗时 < 帧长"),
        ul(["<strong>RTF &lt; 1 只是必要条件</strong>：平均够快不代表每帧都够快，"
            "调度抖动、GC 与多路并发都会造成尾延迟。",
            "<strong>实测口径</strong>：固定种子、跑足够多帧、报平均与 P99，并注明硬件与是否多线程。",
            "<strong>优化顺序</strong>：先砍非因果前瞻，再降帧长与通道数，最后做量化与算子融合。",
            "<strong>端到端</strong>：RTP 时间戳与抖动缓冲由 {{ch:00}} 的实时链路决定，"
            "算法侧省下的毫秒可能被网络侧吃掉。"]),
        note("实验口径", "下面用纯标准库实测「STFT → 逐 bin 增益 → ISTFT」一段的 RTF，"
             "并给出一份可逐行相加的延迟预算表。数值随机器而变，重点是口径而非绝对毫秒数。")),
  ],
  demos=[mk_demo(
      file="code/28-latency-budget.py",
      title="实验 28-1 · 延迟组成账本与三种帧长的 RTF 实测",
      doc="列出链路延迟组成，并用计时实测三种 STFT 帧长下的实时因子。",
      params="""N = 4000
REPEAT = 6
FFTS = (128, 256, 512)
BUDGET = (("采集/播放", 10.0), ("帧长与WOLA", 16.0), ("AEC分块", 4.0),
          ("神经推理", 6.0), ("AGC平滑", 2.0), ("抖动缓冲", 20.0), ("编解码", 10.0))""",
      body="""rng = random.Random(7)
sp = synthetic_speech(rng, N)
nz = white_noise(rng, N, 0.02)
sig = [sp[i] + nz[i] for i in range(N)]
rtfs, frame_ms = [], []
for n_fft in FFTS:
    hop = n_fft // 2
    t0 = time.perf_counter()
    for _ in range(REPEAT):
        frames = stft(sig, n_fft, hop)
        for re, im in frames:
            for k in range(n_fft):
                g = max(0.2, 1.0 - 0.3 / (math.hypot(re[k], im[k]) + 1e-9))
                re[k] *= g
                im[k] *= g
        out = istft(frames, n_fft, hop, N)
    elapsed = time.perf_counter() - t0
    rtfs.append(elapsed / (REPEAT * N / SAMPLE_RATE))
    frame_ms.append(1000.0 * hop / SAMPLE_RATE)
names = [b[0] for b in BUDGET]
values = [b[1] for b in BUDGET]
total = sum(values)
c = Chart(FIG / "28-budget.svg", "一份可逐行相加的端到端延迟预算（示意值）",
          xlabel="组成", ylabel="ms", xticks=[(i, n) for i, n in enumerate(names)])
c.bars(range(len(names)), values, BLUE, label="延迟 ms")
print("预算图:", c.save())
r = Chart(FIG / "28-rtf.svg", "三种帧长下实测的实时因子 RTF", xlabel="FFT 长度", ylabel="RTF",
          xticks=[(i, "%d" % v) for i, v in enumerate(FFTS)])
r.bars(range(len(FFTS)), rtfs, GREEN, label="实测 RTF")
r.hline(1.0, RED, label="实时上限 RTF=1")
print("RTF图:", r.save())
write_wav(AUDIO / "28-input.wav", normalize_peak(sig))
write_wav(AUDIO / "28-output.wav", normalize_peak(out))
print("延迟组成: " + " ".join("%s=%.0fms" % (n, v) for n, v in BUDGET))
print("单向合计=%.1f ms | 帧长(跳)=" % total + " ".join("%d=%.1fms" % (f, m) for f, m in zip(FFTS, frame_ms)))
print("实测 RTF: " + " ".join("%d=%.4f" % (f, v) for f, v in zip(FFTS, rtfs)))
print("SAMPLE_RATE=%d REPEAT=%d | 数值随机器而变，重点是口径" % (SAMPLE_RATE, REPEAT))""",
      figs=[("fig/28-budget.svg", "端到端延迟组成账本"),
            ("fig/28-rtf.svg", "三种帧长的实测 RTF")],
      audio=[("audio/28-input.wav", "输入信号"),
             ("audio/28-output.wav", "最小链路处理后的输出")],
      steps="把预算表逐行相加；对照三种帧长的 RTF 与 1.0 的实时上限。",
      expect="帧长增大带来更细的频率分辨率与更高的算法延迟；"
             "本实验的纯标准库实现 RTF 远小于 1，但真实神经模型的推理耗时要另算。"
             "<strong>RTF 达标不等于端到端延迟达标</strong>，抖动缓冲与编解码往往占大头。",
      tweak="把 REPEAT 增加到 30，观察计时噪声变小、RTF 估计更稳。")],
  commands=[shell("用 ffmpeg 检查一段音频的实际时长与时间戳",
                  "ffprobe -hide_banner -v error -show_entries format=duration -of default=nw=1 out.wav",
                  "ffprobe 给出文件时长，可用于核对 RTF 的分母；"
                  "工具是否安装与参数以本机输出及 https://ffmpeg.org/ffmpeg.html 为准。")],
  highlights=[("rfc3550", "RTP 时间戳、抖动与序列号基础"),
              ("mdn-webaudio", "浏览器里观察 AudioWorklet 与延迟"),
              ("onnxruntime", "推理耗时的运行时测量入口"),
              ("webrtc", "工业实时链路的整体参照")],
  repos=[("WebRTC", "https://webrtc.org/",
          "实时通信标准与参考实现，含抖动缓冲与延迟预算", "工程"),
         ("ONNX Runtime", "https://onnxruntime.ai/",
          "端侧推理耗时与量化的常用测量目标", "部署")],
  analogy="延迟预算是一张 BOM 表：每个模块报自己的毫秒数，"
          "总价超了就按「性价比」从大到小砍，而不是凭感觉调模型。",
  bridge="{{ch:27}} 给出流式的正确性，本章给出时间账本；"
         "{{ch:29}} 处理算力与模型体积，{{ch:31}} 把三本账一起纳入验收。",
  pitfalls=["只报平均 RTF，忽略最坏单帧耗时。",
            "把离线两遍处理的耗时当成实时耗时。",
            "算法侧省下的毫秒被抖动缓冲与编解码吃掉却没算进总账。",
            "忽略非因果前瞻对延迟的贡献。"],
  exercises=["为一条 16 kHz / 10 ms 帧的链路写出完整延迟预算表。",
             "解释为什么 RTF < 1 仍可能不满足实时要求。",
             "给出延迟超标时的三级优化顺序与理由。"],
  further=["{{ch:27}} 因果流式；{{ch:29}} 量化；{{ch:31}} 结课项目。"]),

# ==================================================================== 29
C("29", "p6", "part6/29-quantization", "量化、剪枝与端侧推理",
  "把浮点模型塞进端侧预算，同时守住「不能听出来」这条底线。",
  hours="3 学时",
  goals=["能写出均匀量化的误差模型并估算量化 SNR。",
         "能区分训练后量化 PTQ 与量化感知训练 QAT。",
         "能量化不同位深对掩码精度与增强质量的影响。",
         "能列出端侧部署的完整检查清单。"],
  points=["均匀量化与步长", "int8 与定点 DSP", "量化噪声与 SNR", "训练后量化 PTQ",
          "量化感知训练 QAT", "校准与激活范围", "剪枝与稀疏", "端侧推理检查清单"],
  sections=[
      S("29.1", "量化就是给每个数重新定一把尺子",
        eq("q = round(x / Δ)·Δ　，Δ = (x_max − x_min)/(2^b − 1)　，SNR_q ≈ 6.02·b + 1.76 dB"),
        p("{{ch:02}} 讨论过 PCM 量化，模型量化是同一件事，只是对象从波形换成权重与激活。"
          "对输出在 <code>[0,1]</code> 的掩码/增益，尺子是固定的；"
          "对权重则要先统计每层的动态范围（校准），否则少数离群值会把步长撑大、精度全丢。"),
        table(["方法", "何时做", "需要数据吗", "特点"], [
            ["PTQ", "训练完成后", "少量校准集", "最快，低比特时掉点明显"],
            ["QAT", "训练中插入伪量化", "完整训练集", "精度最好，训练成本最高"],
            ["动态量化", "推理时按 batch 统计", "不需要", "权重定长，激活范围动态"],
            ["剪枝", "训练中或之后", "可选", "减少 MACs，但需硬件支持稀疏"],
        ], ["16%", "28%", "22%", "34%"])),
      S("29.2", "端侧部署的检查清单",
        ul(["<strong>精度</strong>：同时报客观指标与主观听测；"
            "只报 segSNR 会漏掉量化引入的音乐噪声。",
            "<strong>算子</strong>：确认目标运行时支持所用算子（复数卷积、GRU、因果注意力）。",
            "<strong>状态</strong>：流式状态本身也要量化或保持浮点，"
            "否则 {{ch:27}} 的等价性测试会失败。",
            "<strong>预算</strong>：重算 {{ch:28}} 的 RTF 与内存带宽，"
            "并测最坏单帧耗时；int8 未必等于 4 倍加速。",
            "<strong>回退</strong>：保留一条传统 3A 兜底链路，"
            "在模型加载失败或设备过载时降级。"]),
        note("实验口径", "下面把 oracle IRM 掩码均匀量化到 2～16 bit，"
             "测量掩码 SNR 与增强后的分段 SNR。这一步隔离了「量化」这一项误差，"
             "不含模型训练误差，便于看清位深的边际收益。")),
  ],
  demos=[mk_demo(
      file="code/29-quantization.py",
      title="实验 29-1 · 掩码位深扫描：量化噪声、增强质量与模型体积",
      doc="把 oracle 掩码量化到 2～16 bit，测量掩码 SNR、分段 SNR 与模型体积估算。",
      params="""N = 8000
N_FFT, HOP = 256, 128
NOISE_AMP = 0.035
BITS = (2, 4, 6, 8, 12, 16)
MODEL_PARAMS = 100000""",
      body="""rng = random.Random(7)
clean = synthetic_speech(rng, N)
noise = white_noise(rng, N, NOISE_AMP)
noisy = [clean[i] + noise[i] for i in range(N)]
fs, fn = stft(clean, N_FFT, HOP), stft(noise, N_FFT, HOP)

def quantize(v, bits):
    levels = 2 ** bits - 1
    return round(max(0.0, min(1.0, v)) * levels) / levels
def enhance(bits):
    frames = stft(noisy, N_FFT, HOP)
    err2, energy, count = 0.0, 0.0, 0
    for idx, (ry, iy) in enumerate(frames):
        rs, is_ = fs[idx]
        rn, in_ = fn[idx]
        for k in range(N_FFT):
            ms = math.hypot(rs[k], is_[k])
            mn = math.hypot(rn[k], in_[k])
            g0 = ms / (ms + mn + 1e-9)
            g = quantize(g0, bits)
            err2 += (g - g0) ** 2
            energy += g0 ** 2
            count += 1
            ry[k] *= g
            iy[k] *= g
    return istft(frames, N_FFT, HOP, N), 10 * math.log10((energy / count) / (err2 / count + 1e-12))
outputs, segs, mask_snrs = [], [], []
for b in BITS:
    out, m = enhance(b)
    outputs.append(out)
    segs.append(seg_snr_db(clean, scale_align(out, clean)))
    mask_snrs.append(m)
c = Chart(FIG / "29-bits.svg", "掩码位深与增强后分段 SNR", xlabel="位深 (bit)", ylabel="dB",
          xticks=[(i, "%d" % b) for i, b in enumerate(BITS)])
c.line(range(len(BITS)), segs, BLUE, label="分段 SNR (dB)")
print("位深图:", c.save())
m = Chart(FIG / "29-mask.svg", "掩码位深与掩码量化 SNR", xlabel="位深 (bit)", ylabel="dB",
          xticks=[(i, "%d" % b) for i, b in enumerate(BITS)])
m.line(range(len(BITS)), mask_snrs, GREEN, label="掩码 SNR (dB)")
m.line(range(len(BITS)), [6.02 * b + 1.76 - 6.02 for b in BITS], RED, label="理论趋势（相对偏移）")
print("掩码图:", m.save())
write_wav(AUDIO / "29-4bit.wav", normalize_peak(outputs[1]))
write_wav(AUDIO / "29-12bit.wav", normalize_peak(outputs[4]))
sizes = [MODEL_PARAMS * b / 8.0 / 1024.0 for b in BITS]
print("分段 SNR: " + " ".join("%dbit=%.2f" % (b, s) for b, s in zip(BITS, segs)))
print("掩码 SNR: " + " ".join("%dbit=%.2f" % (b, s) for b, s in zip(BITS, mask_snrs)))
print("模型体积(估算, %d 参数): " % MODEL_PARAMS +
      " ".join("%dbit=%.1fKB" % (b, z) for b, z in zip(BITS, sizes)))
print("SAMPLE_RATE=%d | 低比特省内存但可能引入音乐噪声" % SAMPLE_RATE)""",
      figs=[("fig/29-bits.svg", "位深与增强后分段 SNR"),
            ("fig/29-mask.svg", "位深与掩码量化 SNR")],
      audio=[("audio/29-4bit.wav", "4 bit 掩码的输出"),
             ("audio/29-12bit.wav", "12 bit 掩码的输出")],
      steps="对照两条曲线，找出「再增加位深收益很小」的拐点；试听 4 bit 与 12 bit。",
      expect="掩码 SNR 随位深约每 bit 提升 6 dB；分段 SNR 在 8 bit 之后趋于饱和，"
             "说明<strong>继续加位深对最终听感的边际收益很小</strong>。"
             "低比特的量化台阶可能带来可听的增益跳变。",
      tweak="把 NOISE_AMP 提到 0.10，观察低比特与高比特的差距是否拉大。")],
  commands=[shell("查看 ONNX Runtime 的量化入口",
                  "python3 -c \"import onnxruntime; print(onnxruntime.__version__)\"",
                  "本机未必安装 onnxruntime；进阶路径见 https://onnxruntime.ai/ ，"
                  "本书实验不依赖任何第三方包。")],
  highlights=[("wiki-quantization", "定点与均匀量化的共同基础"),
              ("onnxruntime", "端侧量化推理的常用运行时"),
              ("rnnoise", "极小模型 + 定点实现的工程范例"),
              ("deepfilternet", "低算力实时增强的模型压缩思路")],
  repos=[("ONNX Runtime", "https://onnxruntime.ai/",
          "端侧推理、量化与算子支持检查的常用目标", "部署"),
         ("RNNoise", "https://github.com/xiph/rnnoise",
          "极小模型与定点实时实现的参考", "AI · C")],
  analogy="量化是给模型的所有数换一把刻度更粗的尺子；"
          "校准是先量出这批数到底有多大，再决定尺子的量程。",
  bridge="{{ch:27}} 与 {{ch:28}} 给出状态与时间约束，本章压缩空间与算力；"
         "{{ch:30}} 讨论分布外泛化，{{ch:31}} 把全部约束写进结课验收。",
  pitfalls=["不做校准直接按理论范围量化，离群值毁掉精度。",
            "只报模型体积，不报量化后的指标与听测。",
            "忘记把流式状态一并量化或保持浮点。",
            "默认 int8 必然带来 4 倍加速，忽略内存带宽与算子支持。"],
  exercises=["推导均匀量化的 SNR ≈ 6.02b + 1.76 dB。",
             "解释 PTQ 与 QAT 各自的适用场景。",
             "写一份至少 6 项的端侧部署检查清单。"],
  further=["{{ch:28}} 延迟预算；{{ch:30}} 泛化；{{ch:31}} 结课项目。"]),

]
