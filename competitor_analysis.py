#!/usr/bin/env python3
"""
true-needs-analysis 竞品分析脚本

输入产品描述 → 搜索互联网竞品 → 提取关键信息 → 输出竞争力分析报告

使用方式:
    python competitor_analysis.py "我想做一个帮助大学生找兼职的App"
    python competitor_analysis.py "一个基于AI的家电物流知识库问答系统"
    python competitor_analysis.py --interactive
    python competitor_analysis.py "大学生答疑AI工具" -q "论文不会写怎么办,作业题做不出用什么软件,best homework help app reddit"

依赖安装:
    pip install ddgs

可选环境变量:
    OPENAI_API_KEY    设置后自动调用GPT做深度分析 + LLM动态生成搜索词
    DEEPSEEK_API_KEY  或使用DeepSeek做分析 + 搜索词生成

搜索词生成策略（优先级从高到低）:
    1. --queries 参数传入的自定义搜索词（信噪比最高）
    2. LLM动态生成（有API Key时自动启用，根据产品描述生成"用户视角"搜索词）
    3. 去污染硬编码模板（兜底，无需API Key）
"""

import sys
import os
import json
import argparse
from datetime import datetime

# 兼容新版 ddgs 和旧版 duckduckgo_search
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        print("请先安装依赖: pip install ddgs")
        sys.exit(1)


# ========== 搜索模块 ==========

def generate_search_queries(product_desc: str, use_llm: bool = False) -> list:
    """根据产品描述生成多组搜索查询
    
    优先使用LLM动态生成（需API Key），否则使用去污染的硬编码模板。
    
    污染问题说明（旧版4组模板已废弃）：
    - "{产品} 竞品分析" → "竞品分析"本身是高频搜索词，返回一堆教程
    - "{产品} 对比 推荐" → "对比推荐"触发购物推荐博文和导航站
    - "类似{产品}的产品 工具" → "工具"触发AI工具导航站
    - "{产品} 行业 玩家" → "玩家"有歧义（游戏），返回游戏产业报告
    
    解决思路：用"用户真实搜索表达"替代"分析师造词"
    """
    if use_llm:
        llm_queries = generate_search_queries_with_llm(product_desc)
        if llm_queries:
            return llm_queries

    # 兜底：去污染的硬编码模板
    # 设计原则：
    # 1. 用户视角而非分析师视角——不用"竞品分析"、"行业现状"等元词
    # 2. 场景化而非概念化——用用户真实搜索表达
    # 3. 加入社区标识（知乎/博客/reddit）获取UGC内容而非软文
    # 4. 加入负面口碑搜索（缺点/不足）——信噪比比正面推荐更高
    # 5. 中英文双查——中文和英文互联网竞品往往不同
    queries = [
        f"{product_desc}哪个好用 知乎",                    # 痛点求助——用户在知乎发问的真实表达
        f"{product_desc}评测 体验 博客",                    # 评测讨论——用户在博客讨论时的用词
        f"{product_desc}替代品 类似软件",                   # 找替代品——用户找竞品时的真实用词
        f"best {product_desc} alternative reddit",         # 英文reddit——讨论比中文博客真实得多
        f"{product_desc}怎么样 缺点 不足",                  # 负面口碑——抓用户抱怨，信噪比最高
    ]
    return queries


def generate_search_queries_with_llm(product_desc: str) -> list:
    """使用LLM动态生成搜索词（需API Key）
    
    LLM会根据产品描述生成"真实用户视角"的搜索词，
    避免"竞品分析"、"行业现状"等分析师术语污染搜索结果。
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return []

    provider = "deepseek" if os.environ.get("DEEPSEEK_API_KEY") else "openai"

    meta_prompt = f"""你是一位熟悉中国互联网搜索行为的竞品调研专家。我需要为一个产品想法做竞品调研，请你帮我生成 6-8 组 DuckDuckGo 搜索词。

【产品想法】
{product_desc}

【生成搜索词的核心原则】
1. 用户视角而非分析师视角：不要用"竞品分析"、"行业现状"、"玩家"这类分析师术语——这些词在搜索引擎里会被解读成"用户想学竞品分析"，返回一堆教程博文。改用真实用户会搜的口语化表达。

2. 避免元搜索陷阱：搜索词里不要包含"竞品"、"分析"、"对比"、"推荐"这些元词，它们本身就是高频搜索词，会喧宾夺主。

3. 场景化而非概念化：不要直接搜产品概念词（如"大学生答疑AI"），而是搜用户在具体场景下的痛点表达（如"论文不会写怎么办"、"作业题做不出用什么软件"）。

4. 中英文双查：中文互联网和英文互联网的竞品往往不同，每组搜索词给出中文版和英文版各一条。

5. 覆盖三类意图：
   - 痛点求助类（用户在论坛/知乎发问的真实表达）
   - 工具寻找类（用户在找替代品时的搜索词）
   - 评测讨论类（用户在博客/社区讨论某类工具时的用词）

【输出格式】
直接输出搜索词列表，每行一条，不要编号不要解释，只输出搜索词本身。"""

    try:
        result = analyze_with_llm(meta_prompt, api_key, provider)
        # 解析LLM返回的搜索词列表——每行一条，去掉空行和注释
        queries = []
        for line in result.strip().split("\n"):
            line = line.strip()
            # 跳过空行、标题行、编号行
            if line and not line.startswith("#") and not line.startswith("搜索词"):
                # 去掉可能的编号前缀（1. 2. 等）
                if line[0].isdigit() and "." in line[:3]:
                    line = line.split(".", 1)[1].strip()
                if line:
                    queries.append(line)
        return queries if queries else []
    except Exception:
        return []


def search_competitors(product_desc: str, max_results: int = 8, custom_queries: list = None) -> list:
    """搜索互联网获取竞品信息
    
    搜索词优先级：
    1. custom_queries（用户/AI通过 --queries 参数传入的自定义搜索词）
    2. LLM动态生成（有API Key时自动调用，质量最高）
    3. 去污染硬编码模板（兜底，不需要API Key）
    """
    if custom_queries:
        queries = custom_queries
        print(f"  使用自定义搜索词（{len(queries)}组）")
    else:
        # 有API Key时尝试用LLM动态生成搜索词
        api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if api_key:
            print("  检测到API Key，正在用LLM生成精准搜索词...")
            queries = generate_search_queries(product_desc, use_llm=True)
            if queries:
                print(f"  LLM生成了 {len(queries)} 组搜索词")
            else:
                print("  LLM生成失败，使用去污染模板兜底")
                queries = generate_search_queries(product_desc, use_llm=False)
        else:
            queries = generate_search_queries(product_desc, use_llm=False)
            print(f"  使用去污染模板搜索（{len(queries)}组），设置API Key可启用LLM动态生成")

    all_results = []
    seen_urls = set()

    for i, query in enumerate(queries, 1):
        print(f"  [{i}/{len(queries)}] 搜索: {query}")
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results, region="wt-wt"))
                for r in results:
                    url = r.get("href", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append({
                            "query": query,
                            "title": r.get("title", ""),
                            "url": url,
                            "snippet": r.get("body", ""),
                        })
        except Exception as e:
            print(f"  搜索失败 [{query}]: {e}")

    return all_results


# ========== 信息提取模块 ==========

def extract_competitor_info(results: list) -> list:
    """从搜索结果中提取竞品信息"""
    competitors = []
    for r in results:
        info = {
            "来源": r["title"],
            "链接": r["url"],
            "描述": r["snippet"],
            "搜索词": r["query"],
        }
        competitors.append(info)
    return competitors


# ========== 分析模块 ==========

ANALYSIS_PROMPT_TEMPLATE = """你是一位产品竞品分析专家。请根据以下搜索结果，分析用户的产品想法在市场中的竞争力。

## 用户的产品想法
{product_desc}

## 互联网搜索结果
{search_results}

## 请按以下结构输出分析报告

### 一、市场现状
- 这个赛道目前有多少玩家？
- 市场成熟度如何？（蓝海/红海/正在升温）

### 二、主要竞品清单
列出找到的竞品，每个竞品包含：
| 竞品名称 | 核心功能 | 目标用户 | 优势 | 劣势 |
|---------|---------|---------|------|------|

### 三、竞争力分析
- 用户产品相比竞品的差异化机会在哪？
- 哪些功能是必备的（竞品都有）？
- 哪些功能可以做出差异化？

### 四、风险点
- 最大的3个风险是什么？
- 有没有竞品已经占据了不可撼动的位置？

### 五、建议
- 如果要做，最关键的切入点是什么？
- 如果不做，原因是什么？

### 六、真需求验证
基于搜索结果，这个需求看起来是：
- [ ] 真需求（市场上有明确的用户痛点和付费意愿）
- [ ] 伪需求（搜索结果很少，或用户谈论的不是痛点）
- [ ] 红海需求（需求真实但竞争过于激烈）

请给出判断依据。
"""


def build_analysis_prompt(product_desc: str, results: list) -> str:
    """构建分析提示词"""
    search_text = ""
    for i, r in enumerate(results[:20], 1):
        title = r.get("来源", r.get("title", ""))
        snippet = r.get("描述", r.get("snippet", ""))
        url = r.get("链接", r.get("url", ""))
        search_text += f"\n[{i}] {title}\n    {snippet}\n    来源: {url}\n"

    return (ANALYSIS_PROMPT_TEMPLATE
            .replace("{product_desc}", product_desc)
            .replace("{search_results}", search_text))


def analyze_with_llm(prompt: str, api_key: str, provider: str = "openai") -> str:
    """调用LLM做深度分析"""
    if provider == "deepseek":
        import urllib.request
        data = json.dumps({
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
        }).encode()
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]
    else:
        import urllib.request
        data = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
        }).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]


# ========== 输出模块 ==========

def print_report(product_desc: str, competitors: list, analysis: str = ""):
    """输出分析报告"""
    print("\n" + "=" * 60)
    print("  竞品分析报告")
    print(f"  产品想法: {product_desc}")
    print(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  搜索到 {len(competitors)} 条相关信息")
    print("=" * 60)

    print("\n## 搜索结果摘要\n")
    for i, c in enumerate(competitors[:15], 1):
        print(f"[{i}] {c['来源']}")
        print(f"    {c['描述'][:120]}...")
        print(f"    搜索词: {c['搜索词']}")
        print(f"    链接: {c['链接']}")
        print()

    if analysis:
        print("\n## AI 深度分析\n")
        print(analysis)
    else:
        print("\n## 分析提示词（复制到任意AI工具中使用）\n")
        prompt = build_analysis_prompt(product_desc, competitors)
        print(prompt)
        print("\n" + "-" * 60)
        print("提示: 设置 OPENAI_API_KEY 或 DEEPSEEK_API_KEY 环境变量后，")
        print("      脚本会自动调用AI生成深度分析报告。")


def save_report(product_desc: str, competitors: list, analysis: str, output_dir: str = "."):
    """保存报告到文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = product_desc[:20].replace(" ", "_").replace("/", "_")
    filename = os.path.join(output_dir, f"competitor_report_{safe_name}_{timestamp}.md")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# 竞品分析报告\n\n")
        f.write(f"**产品想法:** {product_desc}\n\n")
        f.write(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**搜索结果数:** {len(competitors)}\n\n")
        f.write(f"---\n\n## 搜索结果\n\n")
        for i, c in enumerate(competitors, 1):
            f.write(f"### [{i}] {c['来源']}\n\n")
            f.write(f"- **描述:** {c['描述']}\n")
            f.write(f"- **搜索词:** {c['搜索词']}\n")
            f.write(f"- **链接:** {c['链接']}\n\n")

        if analysis:
            f.write(f"---\n\n## AI 深度分析\n\n{analysis}\n")
        else:
            f.write(f"---\n\n## 分析提示词\n\n")
            f.write(build_analysis_prompt(product_desc, competitors))

    print(f"\n报告已保存到: {filename}")
    return filename


# ========== 主流程 ==========

def main():
    parser = argparse.ArgumentParser(description="竞品分析脚本 - 搜索互联网竞品并分析竞争力")
    parser.add_argument("product", nargs="?", help="产品描述，例如: '帮助大学生找兼职的App'")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式，逐步输入产品信息")
    parser.add_argument("--max-results", "-m", type=int, default=8, help="每组搜索的最大结果数（默认8）")
    parser.add_argument("--queries", "-q", help="自定义搜索词，用逗号分隔。不传则自动生成（有API Key时用LLM动态生成，否则用去污染模板）")
    parser.add_argument("--output", "-o", default=".", help="报告输出目录")
    args = parser.parse_args()

    # 获取产品描述
    if args.interactive:
        print("=== 竞品分析工具 - 交互模式 ===\n")
        product_desc = input("请描述你的产品想法（一句话）:\n> ").strip()
        if not product_desc:
            print("产品描述不能为空")
            sys.exit(1)
    elif args.product:
        product_desc = args.product
    else:
        parser.print_help()
        sys.exit(1)

    print(f"\n正在搜索竞品信息: {product_desc}")
    print("这可能需要10-20秒...\n")

    # 解析自定义搜索词
    custom_queries = None
    if args.queries:
        custom_queries = [q.strip() for q in args.queries.split(",") if q.strip()]

    # 搜索竞品
    results = search_competitors(product_desc, max_results=args.max_results, custom_queries=custom_queries)

    if not results:
        print("未搜索到相关信息，请尝试调整产品描述后重试。")
        sys.exit(1)

    competitors = extract_competitor_info(results)

    # 分析
    analysis = ""
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if api_key:
        provider = "deepseek" if os.environ.get("DEEPSEEK_API_KEY") else "openai"
        print(f"检测到 {provider.upper()} API Key，正在生成深度分析...")
        prompt = build_analysis_prompt(product_desc, competitors)
        try:
            analysis = analyze_with_llm(prompt, api_key, provider)
        except Exception as e:
            print(f"AI分析失败: {e}")
            print("将输出搜索结果和提示词供手动分析。")

    # 输出报告
    print_report(product_desc, competitors, analysis)
    save_report(product_desc, competitors, analysis, args.output)


if __name__ == "__main__":
    main()
