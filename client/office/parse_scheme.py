import re
from config import dred, dgreen, dblue

def parse_scheme(file_path):
    scheme_list = []
    current_index = -1  # To keep track of the last added chapter

    # Regular expressions to match different line types
    # report_time_pattern = re.compile(r'^编制时间[:：]\s*(\d{2,4}年\d{1,2}月)')
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
    chapter_pattern = re.compile(r'^(\d+(\.\d+)*)\s+(.+)$')  # Matches headings like '1 概述' or '1.1 设计依据'
    text_pattern = re.compile(r'^\s+(.+)$')  # Matches indented text lines

    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for line_num, line in enumerate(lines, start=1):
        original_line = line  # Keep the original line for debugging
        line = line.rstrip()  # Remove trailing whitespace and newline characters

        if not line:
            continue  # Skip empty lines

        # Check for report start time
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

        # Check for chapter headings
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

        # Check for indented text associated with the last chapter
        text_match = text_pattern.match(line)
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

        # If the line does not match any pattern, you can choose to handle it or skip
        # For now, we'll skip unrecognized lines
        dred(f"【parse_scheme()】Line {line_num}: Unrecognized line format. Skipping.")
        continue

    return scheme_list


# Example usage
if __name__ == "__main__":
    file_path = 'scheme.txt'  # Replace with the path to your scheme.txt file
    scheme_list = parse_scheme(file_path)
    for item in scheme_list:
        print(item)
