from singleton import singleton

import win32com.client as win32
# import win32com
import requests
import json

from tools.llm.api_client import LLM_Client

@singleton
class Office_Client():
    def __init__(self):
        self.llm = None
        self.word = None

        self._init()

    def _init(self):
        self.llm = LLM_Client()
        # 启动Word应用程序
        self.word = win32.gencache.EnsureDispatch('Word.Application')
        # 启动Excel应用程序
        self.excel = win32.gencache.EnsureDispatch('Excel.Application')

    def _excel_get_selected_table(self):
        wb = self.excel.ActiveWorkbook
        ws = wb.ActiveSheet
        selection = self.excel.Selection
        # 获取选中的单元格范围
        data = []
        for row in selection:
            row_data = []
            for cell in row:
                row_data.append(cell.Value)
            data.append(row_data)
        return data

    def excel_get_selected_table_string(self):
        # 获取Excel中的表格数据
        table_data = self._excel_get_selected_table()

        # 将表格数据格式化为字符串
        table_str = '\n'.join(['\t'.join(map(str, row)) for row in table_data])
        return table_str

    def word_get_selected_text(self):
        doc = self.word.ActiveDocument
        selection = self.word.Selection
        selected_text = selection.Text
        return selected_text

    def word_update_text(self, new_text):
        selection = self.word.Selection
        selection.Text = new_text

    def word_insert_text_at_cursor(self, prompt):
        try:
            # 可选：使Word应用程序可见，便于调试
            self.word.Visible = True

            # 获取当前的选区
            selection = self.word.Selection

            # 1）插入 '一、概述'，样式为一级标题
            selection.Style = '标题 1'  # 使用Word的内置样式名称（中文版本）
            selection.TypeText('一、概述')
            selection.TypeParagraph()  # 插入段落符

            # 2）插入 '1、总体情况'，样式为二级标题
            selection.Style = '标题 2'
            selection.TypeText('1、总体情况')
            selection.TypeParagraph()

            # 3）插入 '正文’ ，样式为正文
            selection.Style = '！正文'
            # 在光标位置插入新文本

            gen = self.llm.ask_prepare(question=prompt).get_answer_generator()
            for chunk in gen:
                selection.TypeText(chunk)
            selection.TypeParagraph()

            # 可选：保存文档或执行其他操作
            # word.ActiveDocument.Save()

            # 可选：关闭Word应用程序
            # word.Quit()
        except Exception as e:
            print(f'word通信报错: "{e}"')

def main():
    office = Office_Client()
    office.word_insert_text_at_cursor('我叫土土')

if __name__ == "__main__":
    main()