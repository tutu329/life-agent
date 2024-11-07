#pip install pyarrow

import pyarrow.parquet as pq
import json
import os

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
    print('前20个数据为:')
    with open(jsonl_file_name, 'w', encoding='utf-8') as f:
        for record in df.to_dict(orient='records'):
            i = i + 1
            if i<=20:
                print(f'record: "{record}"')
            elif i==21:
                print('继续剩余数据的转换...')
            # 去除\xa0、\u3000等字符
            # 如去除{'text': '\xa0\xa0\xa0\xa0“是啊，那是金色的?火焰。”'}中的特殊字符\xa0\xa0\xa0\xa0
            record = {k: (v.replace('\xa0', '') if isinstance(v, str) else v) for k, v in record.items()}
            record = {k: (v.replace('\u3000', '') if isinstance(v, str) else v) for k, v in record.items()}

            if record['text']:
                # 'text'内容不为''时，写入jsonl
                f.write(json.dumps(record, ensure_ascii=False) + '\n')  # 确保中文不被转义
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

def main():
    # parquet_to_jsonl('y:/train-00000-of-00192.parquet')
    # print_parquet_head('y:/train-00000-of-00192.parquet')
    parquets_to_jsonls_in_folder('/home/tutu/data/Chinese-H-Novels')

if __name__ == '__main__':
    main()