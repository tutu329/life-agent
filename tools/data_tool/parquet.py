#pip install pyarrow

import pyarrow.parquet as pq
import json
import os
import re

from utils.folder import get_folder_files_list
from config import dred, dgreen, dblue, dyellow, dcyan

def print_parquet_head(filename):
    # 读取 parquet 文件
    parquet_file = filename  # 替换为你的 parquet 文件路径
    table = pq.read_table(parquet_file)

    # 显示前几行数据
    df = table.to_pandas()
    print(df.head())  # 可以更改参数来显示更多行

def parquet_to_jsonl(parquet_file_name):
    # 读取 parquet 文件
    dgreen(f'开始读取parquet文件"{parquet_file_name}"...')
    parquet_file = parquet_file_name  # 替换为你的 parquet 文件路径
    table = pq.read_table(parquet_file)

    # 显示前几行数据
    df = table.to_pandas()


    jsonl_file_without_extension = os.path.splitext(parquet_file_name)[0]

    # 将数据转换为 JSONL 格式并保存
    jsonl_file_name = jsonl_file_without_extension + '.jsonl'  # 输出的 JSONL 文件路径
    dgreen(f'开始将parquet文件转换为"{jsonl_file_name}"...')
    i=0
    j=0
    k=0
    print('前20个数据为:')
    with open(jsonl_file_name, 'w', encoding='utf-8') as f:
        for record in df.to_dict(orient='records'):
            i = i + 1
            if i<=20:
                print(f'record: "{record}"')
            elif i==21:
                print('继续剩余数据的转换...')

            line = record['text']
            if line:
                # 'text'内容不为''、没有乱码时，写入jsonl
                if not _check_line_has_garbled_text(line):
                    k += 1
                    if k<10:
                        dblue(line)
                    # 去除\xa0、\u3000等字符
                    # 如去除{'text': '\xa0\xa0\xa0\xa0“是啊，那是金色的?火焰。”'}中的特殊字符\xa0\xa0\xa0\xa0
                    record = {k: (v.replace('\xa0', '') if isinstance(v, str) else v) for k, v in record.items()}
                    record = {k: (v.replace('\u3000', '') if isinstance(v, str) else v) for k, v in record.items()}

                    # 写入文件
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')  # 确保中文不被转义
                else:
                    j += 1
                    if j<100:
                        dred(f'{line}')


    dgreen(f"Parquet 文件已成功转换为 JSONL 格式并保存到 {jsonl_file_name}")

def parquets_to_jsonls_in_folder(folder_absolute_path):
    try:
        file_name_list = get_folder_files_list(folder_absolute_path, mode='absolute')
        dblue(f'开始进行文件夹"{folder_absolute_path}"下所有parquet文件向jsonl文件的转换...')
        i=0
        for abs_file_name in file_name_list:
            i = i+1
            dgreen(f'开始转换第[{i}]个文件: "{abs_file_name}"...')
            f, ext = os.path.splitext(abs_file_name)
            if ext == '.parquet':
                parquet_to_jsonl(abs_file_name)
        dgreen(f'文件夹"{folder_absolute_path}"共计[{i}]个parquet文件均已成功转换为jsonl文件.')
    except Exception as e:
        dred(f'parquets_to_jsonls_in_folder()报错: "{e}"')

def _check_line_has_garbled_text(line):
    if (('\u0000' in line and '�' in line) \
            or ('\x00' in line and '�' in line)) \
            or ('\x00' == line) \
            or ('\u0000' == line):
        return True
    else:
        return False

# 检查文本文件是否有乱码：如 \x00\x000\x000\x1c 钄�)Yf[闉婚緯\x02^铏樺墘.U'锟�:gvz閬�/f\x0e`HN杞涘
# 判断依据：'�'超过100个
def _contains_garbled_text(filename):
    with open(filename, 'r') as file:  # 以二进制模式读取文件
        has_garbled_text = False
        garbled_text_num = 0
        check_max_garbled_text_num = 100000

        # 逐行读取
        line = file.readline()
        i=0

        head_lines = []
        while line:
            i += 1
            # print(line.strip())
            line = file.readline()
            if i<10:
                # print(line)
                head_lines.append(line)
                pass

            if _check_line_has_garbled_text(line):
                garbled_text_num += 1
                if garbled_text_num > check_max_garbled_text_num:
                    has_garbled_text = True
                    dblue(head_lines)
                    dblue(line)
                    break

        return has_garbled_text
        # return bool(garbled_pattern.search(content))

# 检查jsonls文档内容是否为乱码：如 \x00\x000\x000\x1c 钄�)Yf[闉婚緯\x02^铏樺墘.U'锟�:gvz閬�/f\x0e`HN杞涘
# file_ext：如'jsonl'
def check_text_files_in_folder(folder_absolute_path, file_ext):
    file_name_list = get_folder_files_list(folder_absolute_path, mode='absolute')
    for abs_file_name in file_name_list:
        fname, ext = os.path.splitext(abs_file_name)
        if ext == '.'+file_ext:
            dgreen(f'检查文件: "{abs_file_name}"')
            if _contains_garbled_text(abs_file_name):   # 文件中包含乱码字符
                dred(f'文件"{abs_file_name}"包含乱码')

def main():
    # parquet_to_jsonl('y:/train-00000-of-00192.parquet')
    # print_parquet_head('y:/train-00000-of-00192.parquet')

    # parquets_to_jsonls_in_folder('/home/tutu/data/Chinese-H-Novels/test')
    # parquets_to_jsonls_in_folder('/home/tutu/data/Chinese-H-Novels')

    # check_text_files_in_folder('/home/tutu/data/Chinese-H-Novels/test', 'jsonl')
    check_text_files_in_folder('/home/tutu/data/Chinese-H-Novels', 'jsonl')

if __name__ == '__main__':
    main()