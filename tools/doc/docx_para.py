# docx_parser.py
import argparse
import pathlib
import sys
from typing import List, Optional, Tuple, Dict
from docx import Document
from docx.document import Document as DocumentObject
from docx.table import Table
import re

# 导入新的大纲提取器
from tools.doc.docx_outline import DocxOutlineExtractor

class DocxParser:
    """
    一个用于解析 DOCX 文档并提取特定章节内容的类。

    该类在初始化时一次性解析整个文档的大纲结构，
    然后可以高效地多次提取不同章节的内容。
    """

    def __init__(self, file_path: str):
        """
        初始化解析器。

        Args:
            file_path: .docx 文件的路径。

        Raises:
            FileNotFoundError: 如果文件不存在。
            ValueError: 如果无法从文档中解析出大纲结构。
        """
        if not pathlib.Path(file_path).exists():
            raise FileNotFoundError(f"文件未找到: {file_path}")

        self.file_path = file_path

        # 1. 创建大纲提取器并提取大纲
        self.extractor = DocxOutlineExtractor()

        # 确保是 .docx 格式（如果是 .doc 则自动转换）
        self.docx_path = self.extractor._ensure_docx(file_path)

        # 2. 读取文档对象
        self.doc: DocumentObject = Document(self.docx_path)

        # 3. 提取大纲结构（传递已转换的docx路径避免重复转换）
        self.chapters: List[Dict] = self.extractor.extract_outline(self.docx_path)

        # 4. 创建章节编号到段落索引的映射
        self._create_chapter_paragraph_mapping()

        if not self.chapters:
            raise ValueError(f"无法从文档 '{file_path}' 中解析出任何大纲结构。")

    def _create_chapter_paragraph_mapping(self):
        """创建章节编号到段落索引的映射"""
        self.chapter_paragraph_map = {}

        # 遍历所有段落，找到章节标题对应的段落索引
        for i, para in enumerate(self.doc.paragraphs):
            para_text = para.text.strip()
            if not para_text:
                continue

            # 尝试匹配章节 - 改为更精确的匹配
            for chapter in self.chapters:
                if self._is_chapter_match(para_text, chapter):
                    chapter_key = chapter['number'] if chapter['number'] else chapter['title']
                    # 只有当还没有映射时才设置，避免覆盖
                    if chapter_key not in self.chapter_paragraph_map:
                        self.chapter_paragraph_map[chapter_key] = i
                    break

    def _is_chapter_match(self, para_text: str, chapter: Dict) -> bool:
        """判断段落是否与章节匹配 - 更严格的匹配逻辑"""
        if chapter['number']:
            # 检查是否是列表项（包含中文顿号、中文句号等）
            if '、' in para_text or '。' in para_text or '：' in para_text:
                # 对于包含这些符号的内容，需要更严格的匹配
                # 只有当段落严格按照"编号 标题"格式时才匹配
                expected_format = f"{chapter['number']} {chapter['title']}"
                if para_text.strip() == expected_format:
                    return True
                # 或者允许标题后面有少量额外内容
                if para_text.strip().startswith(expected_format):
                    return True
                return False

            # 对于不包含特殊符号的内容，使用更宽松的匹配
            # 构建匹配模式
            patterns = [
                f"^{re.escape(chapter['number'])}\\s+{re.escape(chapter['title'])}\\s*$",  # 严格匹配（有空格）
                f"^{re.escape(chapter['number'])}\\s+{re.escape(chapter['title'])}\\s",  # 标题后有空格
                f"^{chapter['number']}\\s+{re.escape(chapter['title'])}\\s*$",  # 不转义编号（有空格）
                f"^{chapter['number']}\\s+{re.escape(chapter['title'])}\\s",  # 不转义编号，标题后有空格
                f"^{chapter['number']}{re.escape(chapter['title'])}\\s*$",  # 编号标题连在一起
                f"^{chapter['number']}{re.escape(chapter['title'])}\\s"  # 编号标题连在一起，后有空格
            ]

            for pattern in patterns:
                if re.search(pattern, para_text, re.IGNORECASE):
                    return True

            # 最后检查：段落以编号开头，并且包含章节标题
            if para_text.startswith(chapter['number']) and chapter['title'] in para_text:
                # 但要排除明显的列表项
                if not re.search(r'[\u4e00-\u9fff]、', para_text):  # 不包含中文字符+顿号
                    return True

        else:
            # 如果没有编号，只有当标题完全匹配时才认为匹配
            return para_text.strip() == chapter['title'].strip()

        return False

    def _find_chapter_boundary(self, chapter_number: str) -> Optional[Tuple[Dict, Optional[Dict], int, Optional[int]]]:
        """
        找到目标章节及其内容的边界。

        Returns:
            (target_chapter, end_boundary_chapter, start_para_index, end_para_index)
        """
        target_chapter = None
        target_chapter_index = -1

        # 查找目标章节
        for i, chapter in enumerate(self.chapters):
            if chapter['number'] == chapter_number:
                target_chapter = chapter
                target_chapter_index = i
                break

        if not target_chapter:
            # 如果直接匹配不到，尝试查找以该编号开头的章节
            for i, chapter in enumerate(self.chapters):
                if chapter['number'] and chapter['number'].startswith(chapter_number):
                    # 确保是精确匹配，比如查找"3.2"不应该匹配到"3.20"
                    if chapter['number'] == chapter_number or chapter['number'].startswith(chapter_number + '.'):
                        if chapter['number'] == chapter_number:  # 优先精确匹配
                            target_chapter = chapter
                            target_chapter_index = i
                            break

        if not target_chapter:
            print(f"错误：在大纲中未找到章节 '{chapter_number}'。", file=sys.stderr)
            print(f"可用的章节编号：{[ch['number'] for ch in self.chapters if ch['number']]}", file=sys.stderr)
            return None

        # 查找结束边界章节
        end_boundary_chapter = None
        for i in range(target_chapter_index + 1, len(self.chapters)):
            next_chapter = self.chapters[i]
            if next_chapter['level'] <= target_chapter['level']:
                end_boundary_chapter = next_chapter
                break

        # 获取段落索引
        target_key = target_chapter['number'] if target_chapter['number'] else target_chapter['title']
        start_para_index = self.chapter_paragraph_map.get(target_key)

        end_para_index = None
        if end_boundary_chapter:
            end_key = end_boundary_chapter['number'] if end_boundary_chapter['number'] else end_boundary_chapter[
                'title']
            end_para_index = self.chapter_paragraph_map.get(end_key)

        return (target_chapter, end_boundary_chapter, start_para_index, end_para_index)

    @staticmethod
    def _get_table_text(table: Table) -> str:
        """将单个表格对象转换为格式化的字符串。"""
        return "\n".join([
            " | ".join([cell.text.strip() for cell in row.cells])
            for row in table.rows
        ])

    def get_chapter(self, chapter_number: str) -> Optional[str]:
        """
        获取指定章节的全部内容，包括所有子章节和表格。

        Args:
            chapter_number: 目标章节的编号字符串 (例如 '1', '1.1', '2.1.3')。

        Returns:
            一个包含章节所有内容的字符串，如果章节不存在则返回 None。
        """
        # 1. 查找章节的起始和结束边界
        boundary_result = self._find_chapter_boundary(chapter_number)
        if not boundary_result:
            return None

        target_chapter, end_boundary_chapter, start_para_index, end_para_index = boundary_result

        if start_para_index is None:
            print(f"错误：无法找到章节 '{chapter_number}' 对应的段落。", file=sys.stderr)
            return None

        # 2. 获取起始和结束段落的底层 XML 元素作为标记
        start_para_element = self.doc.paragraphs[start_para_index]._p
        end_para_element = None
        if end_para_index is not None:
            end_para_element = self.doc.paragraphs[end_para_index]._p

        # 3. 准备从 XML 元素反向查找对象的映射
        table_map = {t._element: t for t in self.doc.tables}
        para_map = {p._p: p for p in self.doc.paragraphs}

        content_parts = []
        collecting = False

        # 4. 遍历文档主体的所有顶级 XML 元素
        for element in self.doc.element.body.iterchildren():
            if element == end_para_element:
                break

            if collecting:
                if element in para_map:
                    para = para_map[element]
                    if para.text.strip():
                        content_parts.append(para.text)
                elif element in table_map:
                    table = table_map[element]
                    table_text = self._get_table_text(table)
                    content_parts.append(f"\n--- 表格内容 ---\n{table_text}\n--- 表格结束 ---\n")

            if element == start_para_element:
                collecting = True

        if not content_parts:
            return f"章节 '{chapter_number}' 存在，但其内容为空。"

        return "\n\n".join(content_parts)


def main():
    """处理命令行调用的主函数。"""
    parser = argparse.ArgumentParser(
        description="使用 DocxParser 类从 DOCX 文件中提取指定章节的全部内容。",
        epilog="示例: python from_server_docx_para.py my_report.docx 1.1\n       python from_server_docx_para.py my_report.docx 1"
    )
    parser.add_argument("file", help="DOCX 文件的路径")
    parser.add_argument("chapter", help="要提取的章节号 (例如 '1', '1.1', '2.1.3')")
    args = parser.parse_args()

    try:
        # 1. 创建 DocxParser 实例，所有解析工作在初始化时完成
        doc_parser = DocxParser(args.file)

        # 2. 调用 get_chapter 方法来获取内容
        content = doc_parser.get_chapter(args.chapter)

        # 3. 打印结果
        if content:
            print(content)
        else:
            sys.exit(1)  # 如果 get_chapter 返回 None (即找不到章节)，则以错误码退出

    except (FileNotFoundError, ValueError) as e:
        print(f"初始化错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()