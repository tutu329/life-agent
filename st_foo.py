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

st.latex(r'''
\int x , dx
任务(ReAct模式)已启动...
    a + ar + a r^2 + a r^3 + \cdots + a r^{n-1} =
    \sum_{k=0}^{n-1} ar^k =
    a \left(\frac{1-r^{n}}{1-r}\right)
    ''')

st.markdown(r'''
\[
\int x , dx
任务(ReAct模式)已启动...
    a + ar + a r^2 + a r^3 + \cdots + a r^{n-1} =
    \sum_{k=0}^{n-1} ar^k =
    a \left(\frac{1-r^{n}}{1-r}\right)
\]
    ''')

st.write(r'''
\[
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
