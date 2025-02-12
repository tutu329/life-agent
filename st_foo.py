# import streamlit as st
#
# import re
import streamlit as st
#
#
# def process_string(streamlit, s):
#     """
#     处理输入字符串，识别 LaTeX 表达式并使用 Streamlit 渲染。
#
#     Args:
#         s (str): 输入的字符串，包含 LaTeX 表达式。
#     """
#     # 正则表达式模式，匹配 \[ ... \] 或 \( ... \)
#     pattern = r'\\\[(.*?)\\\]|\\\((.*?)\\\)'
#
#     # 上一次匹配结束的位置
#     last_index = 0
#
#     # 遍历所有匹配的 LaTeX 表达式
#     for match in re.finditer(pattern, s):
#         start, end = match.span()
#
#         # 提取 LaTeX 表达式前的普通文本并渲染为 Markdown
#         if start > last_index:
#             markdown_text = s[last_index:start]
#             streamlit.markdown(markdown_text)
#
#         # 提取 LaTeX 表达式内容
#         latex_content = match.group(1) if match.group(1) else match.group(2)
#         streamlit.latex(latex_content)
#
#         # 更新最后处理的位置
#         last_index = end
#
#     # 处理最后一个 LaTeX 表达式后的文本
#     if last_index < len(s):
#         markdown_text = s[last_index:]
#         streamlit.markdown(markdown_text)
#
#
# # 示例字符串
# example_str1 = r'这是一些文本 \[ \int f(x) dx \] 这是 \[ \int f(x) dx \]更多的文本。'
# example_str2 = r'当然！这里有一个简单的积分表达式：\n\n\n\\int x^2 \\, dx\n\n\n这个积分表达式表示对  x^2  关于  x  的不定积分。其结果是：\n\n\n\\frac{x^3}{3} + C\n\n\n其中  C  是积分常数。\n\n:green[99 ( 25 + 74 ) tokens in 2.1 ( 0.4 + 1.6 ) secs, 59.3 t/s, 45.3 t/s ]'
#
# # 使用 Streamlit 渲染
# st.title("正则表达式处理字符串示例")
#
# st.header("处理 example_str1:")
# process_string(st, example_str1)
#
# st.header("处理 example_str2:")
# process_string(st, example_str2)
#
# # str = r'''
# # \[
# # \int x^n \, dx = \frac{x^{n+1}}{n+1} + C
# # \]
# #     '''
# # print(str)
# # print(str.replace(r'\[', '').replace(r'\]', ''))
# st.latex(str.replace(r'\[', '').replace(r'\]', ''))

st.write(r"""
1) Given:
- A document is a sequence of $N$ words denoted by $\textbf{w} = (w_1,w_2,... ,w_N)$, where $w_n$ is the nth word b in the sequence.
- A corpus is a collection of $M$ documents denoted by $D = \textbf{w}_1, \textbf{w}_2,...\textbf{w}_m$
- $\alpha$ is the Dirichlet prior on the per-document topic distributions
- $\beta$ is the Dirichlet prior on the per-topic  word distributions
- $\Theta$ is the topic distribution for document $m$
- $z_{mn}$ is the topic for $n^{\text{th}}$  word in document $m$
""")

st.latex(r"""
2) Given:
- A document is a sequence of $N$ words denoted by $\textbf{w} = (w_1,w_2,... ,w_N)$, where $w_n$ is the nth word b in the sequence.
- A corpus is a collection of $M$ documents denoted by $D = \textbf{w}_1, \textbf{w}_2,...\textbf{w}_m$
- $\alpha$ is the Dirichlet prior on the per-document topic distributions
- $\beta$ is the Dirichlet prior on the per-topic  word distributions
- $\Theta$ is the topic distribution for document $m$
- $z_{mn}$ is the topic for $n^{\text{th}}$  word in document $m$
""")

st.write(r"""
3) 已知：
- 文档是由$N$个单词组成的序列，记为$\textbf{w} = (w_1,w_2,... ,w_N)$，其中$w_n$表示序列中第$n$个单词。
- 语料库是$M$个文档的集合，记为$D = \textbf{w}_1, \textbf{w}_2,...\textbf{w}_m$。
- $\alpha$是文档-主题分布（per-document topic distributions）的狄利克雷先验参数。
- $\beta$是主题-词语分布（per-topic word distributions）的狄利克雷先验参数。
- $\Theta$表示文档$m$的主题分布。
- $z_{mn}$表示文档$m$中第$n^{\text{th}}$个单词对应的主题。
- $a \left(\frac{1-r^{n}}{1-r}\right)$
- [ x^2 - 6x + 9 + 4x = r^2 ] [ x^2 - 2x + 9 = r^2 ] [ x^2 - 2x + (9 - r^2) = 0 ]
- $[ x^2 - 6x + 9 + 4x = r^2 ] [ x^2 - 2x + 9 = r^2 ] [ x^2 - 2x + (9 - r^2) = 0 ]$
- \boxed{(0, 0), (2, 2\sqrt{2}), (2, -2\sqrt{2})}
- $\boxed{(0, 0), (2, 2\sqrt{2}), (2, -2\sqrt{2})}$
""")

st.latex(r"""
4) 已知：
- 文档是由$N$个单词组成的序列，记为$\textbf{w} = (w_1,w_2,... ,w_N)$，其中$w_n$表示序列中第$n$个单词。
- 语料库是$M$个文档的集合，记为$D = \textbf{w}_1, \textbf{w}_2,...\textbf{w}_m$。
- $\alpha$是文档-主题分布（per-document topic distributions）的狄利克雷先验参数。
- $\beta$是主题-词语分布（per-topic word distributions）的狄利克雷先验参数。
- $\Theta$表示文档$m$的主题分布。
- $z_{mn}$表示文档$m$中第$n^{\text{th}}$个单词对应的主题。
""")

st.latex(r'''
5) \int x , dx
任务(ReAct模式)已启动...
    a + ar + a r^2 + a r^3 + \cdots + a r^{n-1} =
    \sum_{k=0}^{n-1} ar^k =
    a \left(\frac{1-r^{n}}{1-r}\right)
    ''')

st.markdown(r'''
6) \[
\int x , dx
任务(ReAct模式)已启动...
    a + ar + a r^2 + a r^3 + \cdots + a r^{n-1} =
    \sum_{k=0}^{n-1} ar^k =
    a \left(\frac{1-r^{n}}{1-r}\right)
\]
    ''')

st.write(r'''
7) \[
\int x , dx
任务(ReAct模式)已启动...
    a + ar + a r^2 + a r^3 + \cdots + a r^{n-1} =
    \sum_{k=0}^{n-1} ar^k =
    a \left(\frac{1-r^{n}}{1-r}\right)
\]
    ''')
# #
# # print(r'\(\[hihhh\]\)'.strip("\(").strip("\)").strip("\[").strip("\]"))
#
# import streamlit as st
#
# # 设置页面标题（可选）
# st.title("不定积分示例")
#
# # 使用多行字符串（triple quotes）和 Markdown 语法显示内容
# st.markdown(r"""
# \[
# \int x^2 \, dx
# \]
#
# 这个积分表达式表示对 \( x^2 \) 关于 \( x \) 的不定积分。解这个积分可以得到：
#
# \[
# \int x^2 \, dx = \frac{x^3}{3} + C
# \]
# """)

# hhh
