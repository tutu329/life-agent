from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Any
from docx import Document
# 新增导入，用于类型提示
from docx.text.paragraph import Paragraph
import re
import json


# ---------------------------------------------------------------------------
# Data structures (无变化)
# ---------------------------------------------------------------------------

@dataclass
class OutlineNode:
    level: int
    title: str
    paragraph_index: int
    children: list["OutlineNode"] = field(default_factory=list)

    def add_child(self, node: "OutlineNode") -> None:
        self.children.append(node)

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "title": self.title,
            "paragraph_index": self.paragraph_index,
            "children": [c.to_dict() for c in self.children],
        }

    def _collect_md(self, out: list[str], max_hash: int) -> None:
        if self.level > 0:
            out.append(f"{'#' * min(self.level, max_hash)} {self.title}")
        for c in self.children:
            c._collect_md(out, max_hash)

    def to_markdown(self, max_hash: int = 6) -> str:
        out: list[str] = []
        self._collect_md(out, max_hash)
        return "\n".join(out)


@dataclass
class OutlineTree:
    roots: list[OutlineNode]

    def to_markdown(self) -> str:
        return "\n".join(r.to_markdown() for r in self.roots)

    def to_json(self, **json_kwargs: Any) -> str:
        return json.dumps([r.to_dict() for r in self.roots], **json_kwargs)


# ---------------------------------------------------------------------------
# Core extractor
# ---------------------------------------------------------------------------

class DocxOutlineExtractor:
    """Outline extractor supporting Chinese & Western mixed numbering."""

    # characters allowed *after* numbering token to qualify as delimiter
    _DELIMS = " 、.．)）]>»›››·‧•\t --–—\u3000"

    _TOKEN_RE = re.compile(
        r"""^\s*                 # lead space
        [\(（\[]?                 # optional opening bracket
        (                         # token
            (?:[0-9]+(?:\.[0-9]+)*) |   # 1 / 1.1 / 1.1.1 …
            (?:[IVXLCDM]+)        |       # Roman upper
            (?:[ivxlcdm]+)        |       # Roman lower
            (?:[一二三四五六七八九十百千]+) | # Chinese numeral
            (?:[a-z])             |       # latin lower
            (?:[A-Z])                     # latin upper
        )
        [\)）\]]?                # optional closing bracket INSIDE token
        """,
        re.VERBOSE,
    )

    # --- 新增部分 ---
    # 用于识别目录项的正则表达式
    # 匹配模式：(至少2个空格 或 至少2个点) + (可选的空格) + (数字) + (可选的空格) + (行尾)
    # 这可以捕获 "标题 ...... 123" 或 "标题    123" 这样的格式
    _TOC_HEURISTIC_RE = re.compile(r'(\s{2,}|\.{2,})\s*\d+\s*$')
    # --- 结束新增 ---

    _CHINESE_RE = re.compile(r"^[一二三四五六七八九十百千]+$")

    def __init__(self, file_path: str, max_level: Optional[int] = 4):
        self.doc = Document(file_path)
        self.paragraphs = self.doc.paragraphs
        self.max_level = max_level

        # First scan: Detect if there are any multi-level headings
        self.has_dot_chain = self._detect_dot_depth() > 0
        self.max_dot_chain = self._detect_dot_depth()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def outline(self) -> OutlineTree:
        if self._has_heading():
            return self._outline_from_heading()
        if self._has_numbering():
            return self._outline_from_numbering()
        return self._outline_from_plain()

    # ------------------------------------------------------------------
    # Heading / numPr strategies
    # ------------------------------------------------------------------

    def _outline_from_heading(self) -> OutlineTree:
        roots: list[OutlineNode] = []
        stack: list[OutlineNode] = []
        for i, p in enumerate(self.paragraphs):
            # --- 新增修改 ---
            if self._is_toc_entry(p):
                continue
            # --- 结束修改 ---

            style = getattr(p.style, "name", "")
            if not style.startswith("Heading"):
                continue
            try:
                lvl = int(style.split()[1])
            except Exception:
                lvl = 1
            if self._skip(lvl):
                continue
            self._insert(OutlineNode(lvl, p.text.strip(), i), stack, roots)
        return OutlineTree(roots)

    def _outline_from_numbering(self) -> OutlineTree:
        roots, stack = [], []
        for i, p in enumerate(self.paragraphs):
            # --- 新增修改 ---
            if self._is_toc_entry(p):
                continue
            # --- 结束修改 ---

            numPr = p._p.pPr.numPr if p._p.pPr is not None else None
            if numPr is None:
                continue
            try:
                lvl = int(numPr.ilvl.val) + 1
            except Exception:
                lvl = 1
            if self._skip(lvl):
                continue
            self._insert(OutlineNode(lvl, p.text.strip(), i), stack, roots)
        return OutlineTree(roots)

    # ------------------------------------------------------------------
    # Heuristic parsing
    # ------------------------------------------------------------------

    def _outline_from_plain(self) -> OutlineTree:
        """Fallback for documents without Heading styles or numbering."""
        roots, stack = [], []
        for i, p in enumerate(self.paragraphs):
            # --- 新增修改 ---
            if self._is_toc_entry(p):
                continue
            # --- 结束修改 ---

            txt = p.text.rstrip()
            if not txt:
                continue
            m = self._TOKEN_RE.match(txt)
            if not m:
                continue
            end = m.end()
            delim = txt[end] if end < len(txt) else ""
            token_includes_bracket = m.group(0).strip().endswith((")", "）", "]"))
            if end < len(txt) and not token_includes_bracket and delim not in self._DELIMS:
                continue
            raw = m.group(0)
            lvl = self._infer_level(raw)
            if self._skip(lvl):
                continue
            self._insert(OutlineNode(lvl, txt.strip(), i), stack, roots)
        return OutlineTree(roots)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    # --- 新增方法 ---
    def _is_toc_entry(self, p: Paragraph) -> bool:
        """
        Checks if a paragraph is likely a Table of Contents entry.
        """
        # 1. Style-based check (most reliable)
        # Word TOC styles are often named "TOC 1", "TOC 2" or "目录 1" etc.
        style_name = getattr(p.style, 'name', '').lower()
        if 'toc' in style_name or '目录' in style_name:
            return True

        # 2. Heuristic content-based check
        text = p.text.strip()
        if not text:
            return False

        # Heuristic 2a: Check for tab separators. A line with a tab, where the
        # last part is a number, is almost certainly a TOC entry.
        # e.g., "1.1 Introduction\t1"
        if '\t' in text:
            last_part = text.split('\t')[-1].strip()
            if last_part.isdigit():
                return True

        # Heuristic 2b: Check for long space/dot separators before a page number.
        # e.g., "1.1 Introduction ...... 1" or "1.1 Introduction   1"
        if self._TOC_HEURISTIC_RE.search(text):
            return True

        return False

    # --- 结束新增 ---

    def _detect_dot_depth(self) -> int:
        """Scan the document to see if it has multi-level numbered headings (like 1.1, 1.1.1)."""
        max_depth = 0
        for p in self.paragraphs:
            # --- 新增修改 ---
            # Don't let TOC entries influence the detection
            if self._is_toc_entry(p):
                continue
            # --- 结束修改 ---
            m = self._TOKEN_RE.match(p.text.lstrip())
            if m and "." in m.group(0):
                token = m.group(0).lstrip(" (（[").rstrip(self._DELIMS).rstrip(" )）]")
                if token.replace(".", "").isdigit():
                    max_depth = max(max_depth, token.count(".") + 1)
        return max_depth

    def _infer_level(self, raw: str) -> int:
        """
        Infer the heading level based on the token and document context.
        Implements complex rules for documents with dot-chain headings.
        """
        token = raw.strip().lstrip(" (（[").rstrip(self._DELIMS).rstrip(" )）]")

        # Rule 1: Dot-chain format has the highest precedence. Its level is absolute.
        if "." in token and token.replace(".", "").isdigit():
            return token.count(".") + 1

        # Get format characteristics for subsequent rules
        is_chinese = bool(self._CHINESE_RE.fullmatch(token))
        is_digit = token.isdigit()
        is_letter = len(token) == 1 and token.isalpha()
        has_paren = any(c in raw for c in ")）")
        has_comma = any(c in raw for c in "、.．")

        # Rule 2: Logic depends on whether the document contains dot-chains.
        if self.has_dot_chain:
            # For documents with dot-chains ("1.1", "1.1.1"), apply the specified hierarchy.
            if is_digit and not has_comma and not has_paren:
                return 1
            base = self.max_dot_chain
            if is_chinese:
                return base + 1
            if is_digit and has_comma:
                return base + 2
            if is_digit and has_paren:
                return base + 3
            if is_letter and has_paren:
                return base + 4
            return 99

        else:
            # For simple documents without dot-chains, use a standard hierarchy.
            if is_chinese:
                return 1
            if is_digit and has_comma:
                return 2
            if is_digit and has_paren:
                return 3
            if is_letter and has_paren:
                return 4
            if is_digit:
                return 2
            return 99

    # tree helpers
    def _insert(self, node: OutlineNode, stack: list[OutlineNode], roots: list[OutlineNode]):
        while len(stack) >= node.level:
            stack.pop()
        (stack[-1].add_child(node) if stack else roots.append(node))
        stack.append(node)

    # misc
    def _skip(self, lvl: int) -> bool:
        return self.max_level is not None and lvl > self.max_level

    def _has_heading(self) -> bool:
        # We also need to filter TOC styles from this check
        for p in self.paragraphs:
            style_name = getattr(p.style, 'name', '')
            if 'toc' in style_name.lower() or '目录' in style_name:
                continue
            if style_name.startswith("Heading"):
                return True
        return False

    def _has_numbering(self) -> bool:
        return any(
            p._p.pPr is not None and p._p.pPr.numPr is not None and not self._is_toc_entry(p) for p in self.paragraphs)


# ---------------------------------------------------------------------------
# CLI helper (无变化)
# ---------------------------------------------------------------------------

def _main():
    import argparse, pathlib, sys, textwrap
    ap = argparse.ArgumentParser(
        description="Extract outline from DOCX",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""Examples:
  python outline.py report.docx
  python outline.py report.docx -l 2 --format json
"""),
    )
    ap.add_argument("file", help="Path to .docx")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    ap.add_argument("-l", "--max-level", type=int, default=4)
    args = ap.parse_args()

    if not pathlib.Path(args.file).exists():
        sys.exit(f"File not found: {args.file}")

    tree = DocxOutlineExtractor(args.file, args.max_level).outline()
    print(tree.to_markdown() if args.format == "md" else tree.to_json(ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()