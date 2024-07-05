from bs4 import BeautifulSoup

# 示例 HTML 数据
html1 = '''<div><p>This is a paragraph1.</p>
<p>This is a paragraph2.</p>
<p>This is a paragraph3.</p>
<p>This is a paragraph4.</p>
And some more text.
</div>'''
html2 = '''<div>div_text<p>This is a paragraph1.</p>
<p>This is a paragraph2.</p>
<p>This is a paragraph3.</p>
<p>This is a paragraph4.</p>
And some more text.
</div>'''

# 使用 BeautifulSoup 解析 HTML
soup1 = BeautifulSoup(html1, 'html.parser')
soup2 = BeautifulSoup(html2, 'html.parser')

# 获取 div 标签
div1 = soup1.find('div')
div2 = soup2.find('div')

# 仅获取 div 标签下直接的文本内容
def get_direct_text(div):
    return ''.join(text for text in div.find_all(text=True, recursive=False)).strip()

# 获取结果
text1 = get_direct_text(div1)
text2 = get_direct_text(div2)

print(f"HTML1 div 直接文本: {text1}")
print(f"HTML2 div 直接文本: {text2}")