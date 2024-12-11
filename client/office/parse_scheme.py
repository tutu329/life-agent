import re
from config import dred, dgreen, dblue

def get_scheme_list(file_path):
    scheme_list = []
    current_index = -1  # To keep track of the last added chapter

    # Regular expressions to match different line types
    # report_time_pattern = re.compile(r'^编制时间[:：]\s*(\d{2,4}年\d{1,2}月)')

    # 匹配“报告编制时间”
    report_time_pattern = re.compile(
        r'^编制时间[:：]\s*'  # Matches the start "编制时间："
        r'('
        r'\d{2,4}年\d{1,2}月'          # e.g., 2024年9月
        r'|'
        r'\d{2,4}-\d{1,2}-\d{1,2}'      # e.g., 2024-09-03
        r'|'
        r'\d{2,4}\.\d{1,2}\.\d{1,2}'    # e.g., 2024.9.3
        r')$'
    )
    # 匹配“章节标题”
    chapter_pattern = re.compile(r'^(\d+(\.\d+)*)\s+(.+)$')  # Matches headings like '1 概述' or '1.1 设计依据'
    # 匹配“章节标题”后缩进的文本内容
    indent_text_pattern = re.compile(r'^\s+(.+)$')  # Matches indented text lines。其中^表示匹配字符串的开头，\s表示任意空白字符包括空格、制表符（tab）、换行符等
    # 匹配非“章节标题”后文本（如开篇文本）
    alone_text_pattern = re.compile(r'^(.+)$')

    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for line_num, line in enumerate(lines, start=1):
        original_line = line  # Keep the original line for debugging
        line = line.rstrip()  # Remove trailing whitespace and newline characters

        if not line:
            continue  # Skip empty lines

        # Check if the line is a full-line comment
        if line.lstrip().startswith('#'):
            dgreen(f"【parse_scheme()】Line {line_num}: Full-line comment detected. Skipping.")
            continue

        # Handle inline comments: Remove everything after the first '#'
        if '#' in line:
            line = line.split('#', 1)[0].rstrip()
            dgreen(f"【parse_scheme()】Line {line_num}: Inline comment detected. Content before '#' retained: '{line}'")

        if not line:
            continue  # If line becomes empty after removing inline comment

        # 检查非缩进的独立文本
        # alone_text_match = alone_text_pattern.match(line)

        # 检查“报告编制时间”
        report_time_match = report_time_pattern.match(line)
        if report_time_match:
            date = report_time_match.group(1)
            scheme_list.append({
                'type': 'report_start_time',
                'content': {'date': date}
            })
            current_index = -1  # Reset current_index since report_start_time is not a chapter
            # print(f"Line {line_num}: Matched report_start_time with date '{date}'")
            continue

        # 检查“章节标题”
        chapter_match = chapter_pattern.match(line)
        if chapter_match:
            heading_num = chapter_match.group(1)
            heading = chapter_match.group(3)
            scheme_list.append({
                'type': 'chapter',
                'content': {
                    'heading_num': heading_num,
                    'heading': heading,
                    'text': ''
                }
            })
            current_index = len(scheme_list) - 1  # Set current_index to the last added chapter
            # print(f"Line {line_num}: Matched chapter '{heading_num} {heading}' at index {current_index}")
            continue

        # 检查上一个“章节标题”后的缩进文本
        text_match = indent_text_pattern.match(line)
        if text_match and current_index >= 0:
            text = text_match.group(1)
            # Append the text to the last chapter's 'text' field
            # If there's already text, append with a space
            existing_text = scheme_list[current_index]['content']['text']
            if existing_text:
                scheme_list[current_index]['content']['text'] += ' ' + text
            else:
                scheme_list[current_index]['content']['text'] = text
            # print(f"Line {line_num}: Appended text to chapter index {current_index}: '{text}'")
            continue

        # 如果检查结果都不符合，做如下处理，或不处理
        if scheme_list[current_index]['type']=='along_text':
            # 如果上一行也是'along_text'，则追加内容
            scheme_list[current_index]['content']['text'] += '\n' + line
        else:
            scheme_list.append({
                'type': 'along_text',
                'content': {
                    'text': line,
                }
            })
            current_index = len(scheme_list) - 1

        # dred(f"【parse_scheme()】Line {line_num}: Unrecognized line format. Skipping.")
        continue

    return scheme_list

# Example usage
if __name__ == "__main__":
    file_path = 'D:/server/life-agent/client/office/xiaoshan_prj/scheme.txt'  # Replace with the path to your scheme.txt file
    # file_path = 'demo/scheme.txt'  # Replace with the path to your scheme.txt file
    scheme_list = get_scheme_list(file_path)
    for item in scheme_list:
        print(item)
