# true-needs-analysis

> 基于《真需求》（梁宁著）的需求验证工具包 — 在动手开发之前，先验证需求是不是真的。

## 这是什么

大多数产品失败不是因为做得不好，而是因为建立在了**想象的需求**上。

这个工具包把《真需求》的方法论变成了可执行的 AI 工具，帮你用最快的速度判断一个想法到底值不值得做。

## 工具包结构

```
true-needs-analysis/
├── skills/
│   ├── true-needs-filter/    # 快速过滤：30秒出结论
│   │   └── SKILL.md
│   └── true-needs-deep/      # 深度分析：KANO+价值护城河
│       └── SKILL.md
├── competitor_analysis.py     # 竞品分析脚本：自动搜索互联网竞品
├── SKILL.md                   # 旧版单文件skill（兼容保留）
├── LICENSE
└── README.md
```

## 两个 Skill

| Skill | 定位 | 触发词 | 用时 | 输出 |
|-------|------|--------|------|------|
| **true-needs-filter** | 急诊分诊 | "值不值得做"、"快速判断" | 30秒 | 通过/风险/暂停 |
| **true-needs-deep** | 全面体检 | "深入分析"、"详细分析" | 5-10分钟 | 三要素+KANO+护城河报告 |

### true-needs-filter（快速过滤）

只问三个**选择题**（选 A/B/C，不用打字）：
1. 你的用户是谁？——能说出具体的人 / 大概知道哪类人 / 只能描述人群
2. 你从哪些渠道了解到痛点？——**可多选**：亲眼观察 / 听别人说 / 自己就是用户 / 逻辑推断
3. 用户目前怎么处理的？——**可多选**：花钱凑合 / 手工处理 / 无人解决 / 没调查过

根据选择组合给出：✅ 可以推进 / ⚠️ 需要先调查 / 🛑 暂停

### true-needs-deep（深度分析）

四个维度的系统性检验，全程**选择题交互**：
1. **三要素精度检验** — 用户、场景、痛点是否足够具体（不达标的继续用选择题追问，追问支持多选）
2. **竞品市场调研** — 自动调用 `competitor_analysis.py` 搜索互联网竞品
3. **KANO 类型判断** — "功能消失用户怎么反应？"三选一定型，不确定再反向验证
4. **价值护城河检验** — 功能价值（单选）+ 情绪价值（**多选**：省心/被理解/有面子）+ 资产价值（**多选**：数据/习惯/关系）

## 竞品分析脚本

不依赖任何 AI 平台，直接命令行跑：

```bash
# 安装依赖
pip install duckduckgo-search

# 直接使用
python competitor_analysis.py "我想做一个帮助大学生找兼职的App"

# 交互模式
python competitor_analysis.py --interactive

# 指定搜索量和输出目录
python competitor_analysis.py "AI招聘工具" -m 10 -o ./reports
```

设置 `OPENAI_API_KEY` 或 `DEEPSEEK_API_KEY` 环境变量后，脚本会自动调用 AI 生成深度分析报告。不设也行，会输出搜索结果和分析提示词，复制到任意 AI 工具里用。

## 安装方式

### 方式一：作为 Skill 安装

将 `skills/true-needs-filter/` 和 `skills/true-needs-deep/` 目录复制到你的 AI 助手的 skills 目录下。

适用于：WorkBuddy、Claude Code、Cursor 等支持 SKILL.md 的 AI 助手。

### 方式二：直接用竞品分析脚本

```bash
git clone https://github.com/SHU996/true-needs-analysis.git
cd true-needs-analysis
pip install duckduckgo-search
python competitor_analysis.py "你的产品想法"
```

## 来源

- 方法论框架：梁宁《真需求》（新星出版社，2024）
- 核心理念：真需求 = 用户 + 场景 + 痛点，三者都必须具体、可观察，不能是推断

## License

MIT
