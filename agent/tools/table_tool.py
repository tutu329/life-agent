import win32com.client as win32
from win32com.client import constants
import os
import re

def extract_table_to_word(excel_path, sheet_name, table_title='', word_path=None):
    """
    从指定的 Excel 文件和工作表中提取表格数据，并将其以文本形式复制到 Word 中，
    根据每个单元格的 NumberFormat 格式化数值，包括百分数格式。

    :param excel_path: Excel 文件的路径
    :param sheet_name: 工作表的名称
    :param word_path: 输出的 Word 文件路径（可选）
    """
    # 检查文件是否存在
    if not os.path.exists(excel_path):
        print(f"错误: Excel 文件 '{excel_path}' 不存在。")
        return

    # 初始化 Excel 应用
    try:
        excel = win32.gencache.EnsureDispatch('Excel.Application')
        excel.Visible = False  # 设置为 True 以调试
        excel.DisplayAlerts = False
    except Exception as e:
        print(f"无法启动 Excel 应用程序: {e}")
        return

    try:
        # 打开指定的工作簿
        workbook = excel.Workbooks.Open(os.path.abspath(excel_path))

        # 获取指定的工作表
        try:
            sheet = workbook.Worksheets(sheet_name)
        except Exception as e:
            print(f"无法找到工作表 '{sheet_name}': {e}")
            workbook.Close(SaveChanges=False)
            excel.Quit()
            return

        # 确定表格的起始和结束单元格
        used_range = sheet.UsedRange
        start_row = used_range.Row
        start_col = used_range.Column
        end_row = start_row + used_range.Rows.Count - 1
        end_col = start_col + used_range.Columns.Count - 1

        # 提取数据
        data = []
        for row in range(start_row, end_row + 1):
            row_data = []
            for col in range(start_col, end_col + 1):
                cell_obj = sheet.Cells(row, col)
                cell_value = cell_obj.Value
                if cell_value is None:
                    cell_str = ""
                elif isinstance(cell_value, (int, float)):
                    # 获取单元格的数字格式
                    number_format = cell_obj.NumberFormat
                    decimal_places, is_percentage = get_decimal_places_and_percentage(number_format)
                    if is_percentage:
                        # 将数值转换为百分比
                        cell_percentage = cell_value * 100
                        cell_str = f"{cell_percentage:.{decimal_places}f}%"
                    else:
                        # 格式化数值，保留相应的小数位数
                        cell_str = f"{cell_value:.{decimal_places}f}"
                else:
                    cell_str = str(cell_value)
                row_data.append(cell_str)

            # [row_data的string, row_data]
            data.append(["\t".join(row_data), row_data])

        # 将数据转换为单一的文本字符串，每行以换行符分隔
        table_text = "\n".join([item[0] for item in data])

    except Exception as e:
        print(f"在处理 Excel 文件时出错: {e}")
        workbook.Close(SaveChanges=False)
        excel.Quit()
        return

    finally:
        # 关闭工作簿和 Excel 应用
        workbook.Close(SaveChanges=False)
        excel.Quit()

        # 获取当前光标位置
        word = win32.gencache.EnsureDispatch('Word.Application')
        selection = word.Selection

        # 获取表格的行数和列数
        num_rows = len(data)
        num_cols = len(data[0][1])
        # num_cols = len(data[0]) if num_rows > 0 else 0

        if num_rows == 0 or num_cols == 0:
            print("警告: 提取到的表格数据为空。")
            return

        # Step 1: 在当前位置插入分节符（下一页）
        selection.InsertBreak(constants.wdSectionBreakNextPage)

        # Step 2.1: 添加表头
        selection.TypeText(f'{table_title}')
        # 存储当前对齐方式
        previous_alignment = selection.ParagraphFormat.Alignment
        # 设置段落居中对齐
        selection.ParagraphFormat.Alignment = win32.constants.wdAlignParagraphCenter

        # Step 2.2: 添加表格
        table = selection.Tables.Add(Range=selection.Range, NumRows=num_rows, NumColumns=num_cols)

        # 设置当前节的页面方向为横向
        selection.Sections(1).PageSetup.Orientation = constants.wdOrientLandscape

        # Step 3: 在表格后插入另一个分节符（下一页）
        # 将光标移动到表格末尾
        selection.EndKey(Unit=6)  # 6 表示 wdStory，移动到文档末尾

        # 插入分节符
        selection.InsertBreak(constants.wdSectionBreakNextPage)
        # 设置新节的页面方向为纵向
        selection.Sections(1).PageSetup.Orientation = constants.wdOrientPortrait

        # 填充表格数据
        try:
            for i in range(num_rows):
                for j in range(num_cols):
                    cell = table.Cell(i + 1, j + 1)
                    cell.Range.Text = data[i][1][j]
        except Exception as e:
            print(f'表格创建出错: {e}')

        # 设置表格边框
        set_table_borders(table)

        # 自动调整表格以适应内容
        # Behavior 参数可以是以下值之一：
        # 0 或 win32com.client.constants.wdAutoFitFixed：固定列宽，不自动调整。
        # 1 或 win32com.client.constants.wdAutoFitContent：根据内容自动调整列宽。
        # 2 或 win32com.client.constants.wdAutoFitWindow：自动调整表格宽度以适应窗口（页面）宽度。
        table.AutoFitBehavior(2)  # Behavior = 2
        selection.EndKey(Unit=6)  # 6 表示 wdStory，移动到文档末尾

        # 设置段落居中对齐
        selection.ParagraphFormat.Alignment = previous_alignment

    return table_text

def set_table_borders(table):
    """
    设置 Word 表格的边框样式：外边框为粗线，内部分隔线为细线。

    :param table: Word 表格对象
    """
    # 获取 Word 常量
    constants = win32.constants

    # 设置内部边框为细线
    table.Borders(constants.wdBorderHorizontal).LineStyle = constants.wdLineStyleSingle
    table.Borders(constants.wdBorderHorizontal).LineWidth = constants.wdLineWidth025pt  # 细线

    table.Borders(constants.wdBorderVertical).LineStyle = constants.wdLineStyleSingle
    table.Borders(constants.wdBorderVertical).LineWidth = constants.wdLineWidth025pt  # 细线

    # 设置外边框为粗线
    table.Borders(constants.wdBorderTop).LineStyle = constants.wdLineStyleSingle
    table.Borders(constants.wdBorderTop).LineWidth = constants.wdLineWidth150pt  # 粗线

    table.Borders(constants.wdBorderBottom).LineStyle = constants.wdLineStyleSingle
    table.Borders(constants.wdBorderBottom).LineWidth = constants.wdLineWidth150pt  # 粗线

    table.Borders(constants.wdBorderLeft).LineStyle = constants.wdLineStyleSingle
    table.Borders(constants.wdBorderLeft).LineWidth = constants.wdLineWidth150pt  # 粗线

    table.Borders(constants.wdBorderRight).LineStyle = constants.wdLineStyleSingle
    table.Borders(constants.wdBorderRight).LineWidth = constants.wdLineWidth150pt  # 粗线



def get_decimal_places_and_percentage(number_format):
    """
    根据 Excel 单元格的 NumberFormat 获取小数位数和是否为百分比格式。

    :param number_format: Excel 单元格的 NumberFormat 属性
    :return: (小数位数（整数）, 是否为百分比（布尔值）)
    """
    is_percentage = False
    # 检查是否包含百分号
    if '%' in number_format:
        is_percentage = True

    # 使用正则表达式查找小数点后的零的数量
    # 例如：0.00, #,##0.000, 0.00%, #,##0.000%
    match = re.search(r'0\.([0]+)', number_format)
    if match:
        decimal_places = len(match.group(1))
    else:
        # 如果没有明确的小数位数，则默认返回0
        decimal_places = 0

    return decimal_places, is_percentage

# 使用示例
if __name__ == "__main__":
    excel_file = 'd:/demo/负荷及平衡.xlsx'        # Excel 文件路径
    # excel_file = 'y:/demo/负荷及平衡.xlsx'        # Excel 文件路径
    sheet = '负荷预测'                          # 工作表名称
    word_file = 'output.docx'                   # 输出的 Word 文件路径（可选）

    print(extract_table_to_word(excel_file, sheet, table_title='负荷预测表', word_path=word_file ))
