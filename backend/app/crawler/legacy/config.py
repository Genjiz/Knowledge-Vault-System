MODEL_CONFIG = {
    "default_model": "gemini-3-flash-preview",
    "alternative_models": ["gemini-2.5-flash"],
}

PROMPTS = {
    "journal_analysis": """
你现在是一位资深的信息科学领域分析师。你的任务是深入分析我提供给你的最新一期《{journal_name}》中
{paper_count} 篇论文的标题、摘要和关键词，并生成一份结构清晰、内容详实的综合分析报告。

# 输入信息
我将提供每篇论文的以下内容：
1. 标题（Title）
2. 摘要（Abstract）
3. 关键词（Keywords）

# 任务与输出要求
请严格按照以下结构输出 Markdown：

1. 核心研究主题聚类（Core Research Themes Clustering）
- 归纳 3-5 个核心主题。
- 每个主题需包含：主题名称、主题说明、对应论文标题清单。

2. 研究方法与技术视角（Methodology & Technical Perspective）
- 总结主要研究方法与关键技术。
- 可按机器学习、深度学习、知识图谱、计量分析、系统设计等分类并简要说明。

3. 关键创新与前沿趋势（Key Innovations & Frontier Trends）
- 提炼 2-3 个关键创新点或趋势。
- 每个趋势结合具体论文内容做简要阐述。

4. 单篇论文亮点速览（Individual Paper Highlights）
- 必须使用 Markdown 表格输出。
- 必须完整覆盖全部论文：共 {paper_count} 篇，就输出 {paper_count} 行（不含表头）。
- 必须按输入顺序逐篇对应（Paper 1 到 Paper {paper_count}），不得跳号、不得合并、不得省略。
- 每行包含三列：
  - 论文标题
  - 核心研究问题
  - 主要创新点/贡献
- 严禁输出“受篇幅限制”“仅列举代表作”“示例性列举”等任何省略说明。
- 如果某篇信息不足，也必须保留该行，并明确写“未提供/信息不足”。

5. 总结（Overall Summary）
- 用一段话概括本期整体研究方向、方法特征与前沿动态。

请确保分析客观、准确、专业，语言自然流畅。
"""
}


def get_default_model():
    return MODEL_CONFIG["default_model"]


def get_prompt(prompt_key):
    return PROMPTS.get(prompt_key, "")
