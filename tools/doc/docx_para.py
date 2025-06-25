# docx_parser.py
import argparse
import pathlib
import sys
from typing import List, Optional, Tuple

from docx.document import Document as DocumentObject
from docx.table import Table

# 确保 outline_extractor.py 在同一个目录下
from tools.doc.docx_outline import DocxOutlineExtractor, OutlineNode, OutlineTree


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

        # 1. 使用我们现有的提取器来获取文档对象和大纲
        self.extractor = DocxOutlineExtractor(file_path)
        self.doc: DocumentObject = self.extractor.doc
        self.outline_tree: OutlineTree = self.extractor.outline()

        # 2. 扁平化大纲以便于顺序查找，并将其存储为实例属性
        self.flat_outline: List[OutlineNode] = self._flatten_tree(self.outline_tree.roots)

        if not self.flat_outline:
            raise ValueError(f"无法从文档 '{file_path}' 中解析出任何大纲结构。")

    @staticmethod
    def _flatten_tree(nodes: List[OutlineNode]) -> List[OutlineNode]:
        """将大纲树结构递归地扁平化为一个节点列表，保持文档顺序。"""
        flat_list = []
        for node in nodes:
            flat_list.append(node)
            if node.children:
                flat_list.extend(DocxParser._flatten_tree(node.children))
        return flat_list

    @staticmethod
    def _get_table_text(table: Table) -> str:
        """将单个表格对象转换为格式化的字符串。"""
        return "\n".join([
            " | ".join([cell.text.strip() for cell in row.cells])
            for row in table.rows
        ])

    def _find_chapter_boundary(self, chapter_number: str) -> Optional[Tuple[OutlineNode, Optional[OutlineNode]]]:
        """
        在扁平化的大纲中找到目标章节节点及其内容的结束边界节点。
        """
        target_node = None
        target_node_index = -1
        token_re = self.extractor._TOKEN_RE  # 复用提取器中的正则表达式

        for i, node in enumerate(self.flat_outline):
            match = token_re.match(node.title)
            if match and match.group(1).strip() == chapter_number:
                target_node = node
                target_node_index = i
                break

        if not target_node:
            print(f"错误：在大纲中未找到章节 '{chapter_number}'。", file=sys.stderr)
            return None

        end_boundary_node = None
        for i in range(target_node_index + 1, len(self.flat_outline)):
            next_node = self.flat_outline[i]
            if next_node.level <= target_node.level:
                end_boundary_node = next_node
                break

        return (target_node, end_boundary_node)

    def get_chapter(self, chapter_number: str) -> Optional[str]:
        """
        获取指定章节的全部内容，包括所有子章节和表格。

        Args:
            chapter_number: 目标章节的编号字符串 (例如 '1', '1.1', '2.1.3')。

        Returns:
            一个包含章节所有内容的字符串，如果章节不存在则返回 None。
        """
        # 1. 查找章节的起始节点和结束边界节点
        boundary_result = self._find_chapter_boundary(chapter_number)
        if not boundary_result:
            return None
        target_node, end_boundary_node = boundary_result

        # 2. 获取起始和结束段落的底层 XML 元素作为标记
        start_para_element = self.doc.paragraphs[target_node.paragraph_index]._p
        end_para_element = None
        if end_boundary_node:
            end_para_element = self.doc.paragraphs[end_boundary_node.paragraph_index]._p

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
        epilog="示例: python docx_parser.py my_report.docx 1.1\n       python docx_parser.py my_report.docx 1"
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