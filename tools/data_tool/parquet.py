#pip install pyarrow

import pyarrow.parquet as pq
import json
import os

def print_parquet_head(filename):
    # 读取 parquet 文件
    parquet_file = filename  # 替换为你的 parquet 文件路径
    table = pq.read_table(parquet_file)

    # 显示前几行数据
    df = table.to_pandas()
    print(df.head())  # 可以更改参数来显示更多行

def parquet_to_jsonl(parquet_file_name):
    # 读取 parquet 文件
    print(f'开始读取parquet文件"{parquet_file_name}"...')
    parquet_file = parquet_file_name  # 替换为你的 parquet 文件路径
    table = pq.read_table(parquet_file)

    # 显示前几行数据
    df = table.to_pandas()


    jsonl_file_without_extension = os.path.splitext(parquet_file_name)[0]

    # 将数据转换为 JSONL 格式并保存
    jsonl_file_name = jsonl_file_without_extension + '.jsonl'  # 输出的 JSONL 文件路径
    print(f'开始将parquet文件转换为"{jsonl_file_name}"...')
    i=0
    print('前20个数据为:')
    with open(jsonl_file_name, 'w', encoding='utf-8') as f:
        for record in df.to_dict(orient='records'):
            i = i + 1
            if i<=20:
                print(f'record: "{record}"')
            elif i==21:
                print('继续剩余数据的转换...')
            # 去除{'text': '\xa0\xa0\xa0\xa0“是啊，那是金色的?火焰。”'}中的特殊字符\xa0\xa0\xa0\xa0
            record = {k: (v.replace('\xa0', '') if isinstance(v, str) else v) for k, v in record.items()}

            if record['text']:
                # 'text'内容不为''时，写入jsonl
                f.write(json.dumps(record, ensure_ascii=False) + '\n')  # 确保中文不被转义
    print(f"Parquet 文件已成功转换为 JSONL 格式并保存到 {jsonl_file_name}")

def main():
    parquet_to_jsonl('y:/train-00000-of-00192.parquet')
    # print_parquet_head('y:/train-00000-of-00192.parquet')

if __name__ == '__main__':
    main()