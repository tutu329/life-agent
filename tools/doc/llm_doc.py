from tools.llm.api_client_qwen_openai import *
import openai
openai.api_base = "http://116.62.63.204:8000/v1"

from docx import Document
# llm = LLM_Qwen()

def is_win():
    import platform
    sys_platform = platform.platform().lower()
    if "windows" in sys_platform:
        return True
    else:
        return False

class LLM_Doc():
    def __init__(self, in_file_name):
        self.doc_name = in_file_name

        self.win32_doc = None
        self.win32_doc_app = None
        self.win32_constant = None
        
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
            self.win32_doc_app.Documents.Close(self.doc_name)

    def __get_paragraphs_generator_for_docx_file(self):
        try:
            doc = Document(self.doc_name)
        except Exception as e:
            print(f'文件"{self.doc_name}" 未找到。')
            return None

        for para in doc.paragraphs:
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
        for para in self.__get_paragraphs_generator_for_docx_file():
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
def main():
    llm = LLM_Qwen(history=False, history_max_turns=50, history_clear_method='pop', temperature=0.9)
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

    doc = LLM_Doc('/tools/doc/错别字案例.docx')
    doc.win32com_init()
    res_list = doc.check_wrong_written_in_docx_file(llm)
    doc.win32_close_file()

    print("*"*30+"纠错结果汇编"+"*"*30)
    jj=0
    for item in res_list:
        jj += 1
        print(f'第{jj}段检查结果：\n {item}')


if __name__ == "__main__":
    main()