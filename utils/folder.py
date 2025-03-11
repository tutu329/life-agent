import os
import sys
import argparse
from pathlib import Path

# 获取某个文件夹下所有文件和文件夹的名字list，directory可以是绝对路径或相对路径
def get_folder_all_items_string(directory):
    # 获取当前工作目录
    current_directory = os.getcwd()
    # 打印当前工作目录
    print(f'【get_folder_files_list()】当前工作目录是："{current_directory}"')

    p = Path(directory)
    print(f'【get_folder_files_list()】输入的目录是: "{p.absolute()}"')

    if not p.exists():
        print(f"错误：路径 '{directory}' 不存在。")
        sys.exit(1)
    if not p.is_dir():
        print(f"错误：路径 '{directory}' 不是一个文件夹。")
        sys.exit(1)

    items_name_list = []
    # 扫描目录，并区分文件夹和文件
    with os.scandir(p) as entries:
        for entry in entries:
            if entry.is_dir():
                items_name_list.append(f"文件夹: {entry.name}")
                # print(f"文件夹: {entry.name}")
            elif entry.is_file():
                items_name_list.append(f"文件: {entry.name}")
                # print(f"文件: {entry.name}")

    if items_name_list:
        return '\n'.join(items_name_list)
    else:
        return '该文件夹为空.'

# 获取某个文件夹下所有文件的文件名信息list，directory可以是绝对路径或相对路径
def get_folder_files_list(directory, mode='name'):
    # 获取当前工作目录
    current_directory = os.getcwd()
    # 打印当前工作目录
    print(f'【get_folder_files_list()】当前工作目录是："{current_directory}"')

    p = Path(directory)
    print(f'【get_folder_files_list()】输入的目录是: "{p.absolute()}"')

    if not p.exists():
        print(f"错误：路径 '{directory}' 不存在。")
        sys.exit(1)
    if not p.is_dir():
        print(f"错误：路径 '{directory}' 不是一个文件夹。")
        sys.exit(1)

    files = []
    for item in p.iterdir():
        if item.is_file():
            if mode == 'absolute':
                files.append(str(item.resolve()))
            elif mode == 'name':
                files.append(item.name)
            elif mode == 'basename':
                files.append(item.stem)
    return files

# 获取某个文件夹下所有文件的文件名信息string，directory可以是绝对路径或相对路径
def get_folder_files_info_string(directory, mode='name'):
    files_list = get_folder_files_list(directory=directory, mode=mode)
    info_string = '\n'.join(files_list)

    return info_string




def main():
    parser = argparse.ArgumentParser(description="列出指定文件夹下的所有文件名。")
    parser.add_argument("directory", help="目标文件夹的路径。")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--absolute", action="store_true", help="输出文件的绝对路径。")
    group.add_argument("--name", action="store_true", help="仅输出文件名（包含扩展名）。")
    group.add_argument("--basename", action="store_true", help="仅输出主文件名（不包含扩展名）。")

    args = parser.parse_args()

    if args.name:
        mode = 'name'
    elif args.basename:
        mode = 'basename'
    else:
        mode = 'absolute'  # 默认模式

    files = get_folder_files_list(args.directory, mode)

    if files:
        print("文件列表：")
        for f in files:
            print(f)
    else:
        print("该文件夹下没有文件。")


if __name__ == "__main__":
    # main()
    files_str = get_folder_files_info_string('d:\\demo\\依据')
    # files_str = get_folder_files_info_string('../')
    # files_str = get_folder_files_info_string('../', 'basename')
    # files_str = get_folder_files_info_string('../', 'absolute')
    print(files_str)


