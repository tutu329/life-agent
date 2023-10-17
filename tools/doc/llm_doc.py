from dataclasses import dataclass
import copy

from tools.llm.api_client_qwen_openai import *
import openai
openai.api_base = "http://116.62.63.204:8001/v1"

import docx
from docx import Document
# llm = LLM_Qwen()

from enum import Enum, auto

def is_win():
    import platform
    sys_platform = platform.platform().lower()
    if "windows" in sys_platform:
        return True
    else:
        return False

# =========================================管理doc的层次化递归数据结构=================================================
@dataclass
class Image_Part():
    name: str
    data: str
    width: int
    height: int

@dataclass
class Node_Data():
    level: int
    name: str
    text: str
    image: Image_Part

class Doc_Node:
    def __init__(self, node_data):
        self.node_data = node_data
        self.children = []

    def __str__(self):
        return ', '.join([
            'level: ' + str(self.node_data.level),
            'name: ' + self.node_data.name,
            'text: ' + self.node_data.text,
            'children: [' + ', '.join([child.node_data.name for child in self.children]) + ']',
        ])

    def add_child(self, child):
        self.children.append(child)

    def traverse(self, in_node_name):
        print(f'进入节点: {self.node_data.name}')
        if self.node_data.name == in_node_name:
            print(f'--------找到了node: {self.node_data.name}---------')
            return self.node_data

        if self.children:
            print(f'准备进入子节点: [' + ', '.join([child.node_data.name for child in self.children]) + ']')
        for child in self.children:
            res = child.traverse(in_node_name)
            if res is not None:
                return res
        return None
# =========================================管理doc的层次化递归数据结构=================================================

# LLM_Doc：采用python-docx解析文档，采用win32com解决页码问题
class LLM_Doc():
    def __init__(self, in_file_name):
        self.doc_name = in_file_name

        self.win32_doc = None
        self.win32_doc_app = None
        self.win32_constant = None

        self.doc = None
        self.doc_tree = None

        try:
            self.doc = Document(self.doc_name)
        except Exception as e:
            print(f'文件"{self.doc_name}" 未找到。')
        
    def win32com_init(self):
        print(f'win32尝试打开文件"{self.doc_name}"')
        if is_win():
            import win32com.client as win32
            from win32com.client import constants
            self.win32_constant = constants
        else:
            print(f"未在windows系统下运行，无法获取word文档页码.")
            return

        import os

        self.win32_doc_app = win32.gencache.EnsureDispatch('Word.Application')  # 打开word应用程序
        self.win32_doc_app.Visible = False
        # doc_app.Visible = True
        curr_path = os.getcwd()
        self.win32_doc = self.win32_doc_app.Documents.Open(self.doc_name)
        print(f'win32打开了文件"{self.doc_name}"')

    def win32_close_file(self):
        if self.win32_doc:
            try:
                self.win32_doc_app.Documents.Close(self.doc_name)
            except Exception as e:
                print(f'关闭文件"{self.doc_name}"出错: {e}')

    # 将doc解析为层次结构，每一级标题（容器）下都有text、image等对象
    def parse_all_docx(self, inout_doc_tree, in_doc):
        inout_doc_tree = {
            'node':{},
            'container':{}
        }

        for para in in_doc.paragraphs:
            style = para.style.name                 # "Heading 1"
            toc_name  = style.split(' ')[0]         # 标题 "Heading

            if toc_name=='Heading':
                # 增加新的层级
                toc_level = int(style.split(' ')[1])    # 标题级别 1
            else:
                # text、image等元素
                pass

    def get_para_inline_images(self, in_para):
        image = {
            'name':'',
            'data':None,
            'width':0,
            'height':0,
        }
        images_list = []

        # 打印ImagePart的成员函数
        # for item in dir(docx.parts.image.ImagePart):
        #     print(item)

        # 这一段由python-docx库的issue中网友mfripp提供：https://github.com/python-openxml/python-docx/issues/249
        for run in in_para.runs:
            for inline in run._r.xpath("w:drawing/wp:inline"):
                width = float(inline.extent.cx)  # in EMUs https://startbigthinksmall.wordpress.com/2010/01/04/points-inches-and-emus-measuring-units-in-office-open-xml/
                height = float(inline.extent.cy)
                if inline.graphic.graphicData.pic is not None:
                    rId = inline.graphic.graphicData.pic.blipFill.blip.embed
                    image_part = self.doc.part.related_parts[rId]
                    filename = image_part.filename      # 文件名称(其实是类型), 如"image.wmf"
                    bytes_of_image = image_part.blob    # 文件数据(bytes)
                    image['name'] = filename
                    image['data'] = bytes_of_image
                    image['width'] = width
                    image['height'] = height
                    images_list.append(copy.deepcopy(image))

                    # print(f'image_part:{image_part}, width:{width}, height:{height}, rId: {rId}, image:{image}, filename:{filename}')
                    # with open('a.wmf', 'wb') as f:  # make a copy in the local dir
                    #     f.write(bytes_of_image)
        return images_list


    def get_all_inline_images(self):
        images_list = []

        for para in self.doc.paragraphs:
            images_list += self.get_para_inline_images(para)
        return images_list

    def get_paras(self):
        for para in self.doc.paragraphs:
            yield para.text

    # 检查某doc文档所有para的错别词
    def check_wrong_written_in_docx_file(self, in_llm):
        try:
            doc = Document(self.doc_name)
        except Exception as e:
            print(f'文件"{self.doc_name}" 未找到。')
            return

        ii = 0
        result_list = []
        for para in self.get_paras():
            ii += 1
            # print(f"正在分析第{ii}个段落...")

            # para result登记
            print("*"*30+f"正在分析第{ii}个段落"+"*"*30)
            check_prompt = f'现在帮我在这段文字中找错别字："{para}"'
            print(f'本段落内容："{para}"')
            # in_llm.print_history()
            # print(f'check prompt 为：{check_prompt}')
            result_list.append(in_llm.ask_prepare(check_prompt).get_answer_and_sync_print())

        return result_list

# ============================关于角色提示============================
# 一、你希望llm了解哪些信息：
# 1) where are you based?
# 2) what do you do for work?
# 3) what are your hobbies and interests?
# 4) what subject can you talk about for hours?
# 5) what are some goals you have?
# 二、你希望llm怎样回复：
# 1) how formal or casual should llm be?
# 2) how long or short should responses generally be?
# 3) how do you want to be addressed?
# 4) should llm have opinions on topics or remain neutral?
# ============================关于角色提示============================
def main1():
    llm = LLM_Qwen(
        url='http://116.62.63.204:8001/v1',
        history=False,
        history_max_turns=50,
        history_clear_method='pop',
        temperature=0.9,
    )
    role_prompt = '你是一位汉字专家。你需要找出user提供给你的文本中的所有错别字，并给出修改意见。'
    example_prompts = [
        '例如，user发送给你的文字中有单个字的笔误："你是我的好彭友，我们明天粗去玩吧？"，你要指出"彭"应为"朋"、"粗"应为"出"。',
        '例如，user发送给你的文字中有涉及语义的笔误："我们已对全社会效益已经财务效益进行了全面分析。"，你要指出"已经"应为"以及"。',
    ]
    # nagetive_example_prompt = '需要注意的是，一个词语不完整或者多余，并不属于错别字，例如"社会效益最大"应为"社会效益最大化"、"电影院"应为"电影"就不属于错别字，不要将这种情况误判为错别字。'
    nagetive_example_prompt = ''
    style_prompt = '你的错别字修改意见要以json格式返回，具体的json格式要求是，有错别字时像这样：{"result":"有错别字", [{"原有词语":"彭友", "修改意见":"朋友"}, {"原有词语":"粗去", "修改意见":"出去"}]}，没用错别字时像这样：{"result":"无错别字"}。'
    other_requirement = '直接返回json意见，不作任何解释。一步一步想清楚。'
    llm.set_role_prompt(role_prompt+''.join(example_prompts)+nagetive_example_prompt+style_prompt+other_requirement)

    # llm.print_history()
    # llm.ask_prepare('现在帮我在这段文字中找错别字："报告所提投资优化分析适用于新型电力系统、综合能源项目、微电网项目以及传统电力系统项目，具体支持冷热电气各类机组和设备模型，负荷类型支持城市类型、工业类型等，优化目标支持社会效益最大和财务效益最佳等。计算中已经内置了8760h负荷特性、新能源出力特性已经分时电价等信息。"').get_answer_and_sync_print()

    doc = LLM_Doc('d:/server/life-agent/tools/doc/错别字案例.docx')
    doc.win32com_init()
    res_list = doc.check_wrong_written_in_docx_file(llm)
    doc.win32_close_file()

    print("*"*30+"纠错结果汇编"+"*"*30)
    jj=0
    for item in res_list:
        jj += 1
        print(f'第{jj}段检查结果：\n {item}')

def main_toc():
    llm = LLM_Qwen(
        url='http://116.62.63.204:8001/v1',
        history=False,
        history_max_turns=50,
        history_clear_method='pop',
        temperature=0.9,
    )
    file = 'd:/server/life-agent/tools/doc/南麂岛离网型微网示范工程-总报告.docx'
    import docx
    doc = docx.Document(file)
    for para in doc.paragraphs:
        if para.style.name=="Heading 1":
            print(para.text)
        if para.style.name=="Heading 2":
            print('\t'+para.text)
        if para.style.name=="Heading 3":
            print('\t\t'+para.text)
        # if para.style.name=="Heading 4":
        #     print('\t\t\t'+para.text)
    # doc = LLM_Doc(file)
    # doc.win32com_init()
    # for para in doc.get_paras():
    #     print(para)
    # doc.win32_close_file()

def main_image():
    file = 'd:/server/life-agent/tools/doc/南麂岛离网型微网示范工程-总报告.docx'
    doc = LLM_Doc(file)
    # for para in doc.get_paras():
    #     print(para)
    # for image in doc.doc.inline_shapes:
    #     print(f'image: {image.type}')
        # print(f'image: {docx.enum.shape.WD_INLINE_SHAPE(3)}')
        # print(docx.enum.shape.WD_INLINE_SHAPE.PICTURE)
    for image in doc.get_all_inline_images():
        print(', '.join([
            f'image name: {image["name"]}',
            f'image size: {len(image["data"])}',
            f'image width: {image["width"]}',
            f'image height: {image["height"]}'
        ]))


# Color枚举类
class Color(Enum):
    red=auto()
    green=auto()
    blue=auto()

if __name__ == "__main__":
    root = Doc_Node(Node_Data(0, '0', 'aaa', None))
    node_1 = Doc_Node(Node_Data(1, '1', 'abc', None))
    node_1_1 = Doc_Node(Node_Data(2, '1.1', 'cde', None))
    node_1_2 = Doc_Node(Node_Data(2, '1.2', 'fea', None))

    node_2 = Doc_Node(Node_Data(1, '2', 'abc', None))
    node_2_1 = Doc_Node(Node_Data(2, '2.1', 'fhn', None))
    node_2_2 = Doc_Node(Node_Data(2, '2.2', 'hww', None))

    root.add_child(node_1)
    root.add_child(node_2)
    node_1.add_child(node_1_1)
    node_1.add_child(node_1_2)
    node_2.add_child(node_2_1)
    node_2.add_child(node_2_2)

    print(root)
    print(node_1)
    print(node_1_1)
    print(node_1_2)
    print(node_2)
    print(node_2_1)
    print(node_2_2)
    print('='*80)

    res = root.traverse('2.1')
    print(f'res: {res}')

    # main_image()

    # print(f'color: {Color(1)}')
    # print(f'color: {Color.blue}')


# 若win32com打开word文件报错：AttributeError: module 'win32com.gen_py.00020905-0000-0000-C000-000000000046x0x8x7' has no attribute 'CLSIDToClassMap'
# 则删除目录C:\Users\tutu\AppData\Local\Temp\gen_py\3.10中的对应缓存文件夹00020905-0000-0000-C000-000000000046x0x8x7即可

# doc.win32_close_file()若报错：pywintypes.com_error: (-2147352567, '发生意外。', (0, 'Microsoft Word', '类型不匹配', 'wdmain11.chm', 36986, -2146824070), None)
# 很可能是和wps有关，据说卸载word，win32.gencache.EnsureDispatch('Word.Application')会成功调用wps