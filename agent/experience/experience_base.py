# # pip install anytree

from __future__ import annotations

"""Experience 树形结构工具（成员函数版）

主要特性
==========
* :meth:`Experience.add_node`               —— 在当前节点下添加子节点
* :meth:`Experience.add_node_by_path`       —— 在title path下添加子节点
* :meth:`Experience.get_tree_title_string`  —— 渲染整棵（或部分）树为纯文本（仅 title）
* :meth:`Experience.get_tree_all_string`    —— 渲染整棵（或部分）树为纯文本（title + summary）
* :meth:`Experience.get_node_by_path`       —— **按 *title* 路径** 查找节点（支持绝对/相对）
* :meth:`Experience.del_node_tree_by_path`  —— 字符串专用删除接口（向后兼容）
* :meth:`export_to_json_file`               —— 导出json文件
* :meth:`import_from_json_file`             —— 导入json文件

路径解析规则
------------
* 路径以 ``/`` 分隔，各段 **对应节点的 ``title`` 字段**。
* 既支持 *绝对路径*（以当前节点的 ``title`` 为首段），也支持 *相对路径*（省略首段）。
  例如：
  ``root.get_node_by_path("根/子/孙")`` 与 ``root.get_node_by_path("子/孙")`` 等价。

直接运行 ``python experience_tree_utils.py`` 可查看演示。
"""

from datetime import datetime
from typing import List, Sequence
import json
from pathlib import Path

from anytree import NodeMixin, RenderTree

__all__ = ["Experience"]


class Experience(NodeMixin):
    """领域对象：一段“经验”的抽象，可组成树结构。"""

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------
    def __init__(
        self,
        title: str,
        summary: str = "",
        created_at: datetime | None = None,
        name: str | None = None,
        parent: "Experience" | None = None,
    ) -> None:
        self.title = title                          # 标题（路径组件）
        self.summary = summary                      # 经验描述
        self.created_at = created_at or datetime.now()
        self.name = name or title                   # Graphviz 等工具默认使用 name
        self.parent = parent                        # NodeMixin 关系字段 *必须* 最后赋值

    # ------------------------------------------------------------------
    # 字符串表现
    # ------------------------------------------------------------------
    def __str__(self) -> str:  # noqa: D401
        return self.title

    def __repr__(self) -> str:  # noqa: D401
        par = self.parent.title if self.parent else None
        return (
            "Experience(title={!r}, summary={!r}, created_at={!r}, parent={!r})"
        ).format(self.title, self.summary, self.created_at, par)

    # ------------------------------------------------------------------
    # 增
    # ------------------------------------------------------------------
    def add_node(
        self,
        title: str,
        summary: str = "",
        created_at: datetime | None = None,
        name: str | None = None,
    ) -> "Experience":
        """在当前节点下添加子节点并返回新节点。"""

        return Experience(
            title=title,
            summary=summary,
            created_at=created_at,
            name=name,
            parent=self,
        )

    # def add_node_by_path(
    #     self,
    #     path: str | Sequence[str],
    #     summary: str = "",
    #     created_at: datetime | None = None,
    #     name: str | None = None,
    # ) -> "Experience":
    #     """根据路径一次性添加节点。
    #
    #     * 路径最后一段视为 **新节点的 title**。
    #     * 父路径（若有）必须已存在；否则抛 :class:`KeyError`。
    #     * 若同名节点已存在将抛 :class:`ValueError`。
    #     """
    #
    #     parts = self._split_path(path)
    #     if parts and parts[0] == self.title:  # 绝对路径 → 去掉首段
    #         parts = parts[1:]
    #     if not parts:
    #         raise ValueError("路径为空，无法添加节点")
    #
    #     parent_parts, new_title = parts[:-1], parts[-1]
    #     parent_node = self.get_node_by_path(parent_parts) if parent_parts else self
    #
    #     # 冲突检测
    #     if any(c.title == new_title for c in parent_node.children):
    #         raise ValueError(f"节点 '{new_title}' 已存在于 '{parent_node.title}' 下")
    #
    #     return Experience(
    #         title=new_title,
    #         summary=summary,
    #         created_at=created_at,
    #         name=name,
    #         parent=parent_node,
    #     )

    def add_node_by_path(
        self,
        path: str | Sequence[str],
        summary: str = "",
        created_at: datetime | None = None,
        name: str | None = None,
    ) -> "Experience":
        """沿着 *title* 路径逐级查找 / 创建节点，最后一级为新节点并返回。

        - 允许路径中出现尚不存在的中间节点，自动创建。
        - 如果最终节点已存在，则抛 ``ValueError``，防止重复。
        - 支持绝对 / 相对路径；绝对路径第一段应等于当前节点的 ``title``。
        """

        parts = self._split_path(path)
        if parts and parts[0] == self.title:        # 绝对路径 → 去掉首段
            parts = parts[1:]
        if not parts:
            raise ValueError("路径不能为空")

        node: Experience = self
        # 处理除最后一段外的所有部分：不存在就补建
        for comp in parts[:-1]:
            try:
                node = next(c for c in node.children if c.title == comp)  # 已存在
            except StopIteration:
                node = Experience(title=comp, parent=node)                # 自动补建

        new_title = parts[-1]
        # 冲突检测：最后一级不能重名
        if any(c.title == new_title for c in node.children):
            raise ValueError(f"节点 '{new_title}' 已存在于 '{node.title}' 下")

        # 创建并返回最终节点
        return Experience(
            title=new_title,
            summary=summary,
            created_at=created_at,
            name=name,
            parent=node,
        )

    # ------------------------------------------------------------------
    # 查
    # ------------------------------------------------------------------
    def get_tree_title_string(self, level: int | None = None) -> str:
        """渲染 title 树。

        ``level`` 为 ``None`` 时输出整棵树；否则限制深度（0=仅自身）。"""

        lines: List[str] = []
        max_level = None if level is None else level + 1
        for pre, _, node in RenderTree(self, maxlevel=max_level):
            lines.append(f"{pre}{node.title}")
        return "\n".join(lines)

    def get_tree_all_string(self, level: int | None = None) -> str:
        """渲染 title+summary 树。见 :meth:`render_tree` 的 ``level`` 说明。"""

        lines: List[str] = []
        max_level = None if level is None else level + 1
        for pre, _, node in RenderTree(self, maxlevel=max_level):
            line = f"{pre}{node.title}"
            if node.summary:
                line += f" — {node.summary}"
            lines.append(line)
        return "\n".join(lines)

    # ---------------- 路径辅助 ----------------
    @staticmethod
    def _split_path(path: str | Sequence[str]) -> List[str]:
        if isinstance(path, str):
            parts = [p for p in path.strip("/").split("/") if p]
        else:
            parts = list(path)
        if not parts:
            raise ValueError("路径至少应包含一个组件")
        return parts

    # ---------------- 获
    def get_node_by_path(self, path: str | Sequence[str]) -> "Experience":
        """根据 *title* 路径查找节点。

        支持：
        * 绝对路径：首段 == 当前节点 ``title``
        * 相对路径：首段省略
        """

        parts = self._split_path(path)

        # 若首段等于自身 title，视为绝对路径，跳过
        if parts and parts[0] == self.title:
            parts = parts[1:]

        node: Experience = self
        for comp in parts:
            try:
                node = next(c for c in node.children if c.title == comp)  # type: ignore[arg-type]
            except StopIteration:
                raise KeyError(f"在 '{node.title}' 下找不到名为 '{comp}' 的子节点")
        return node

    # ------------------------------------------------------------------
    # 删
    # ------------------------------------------------------------------
    def del_node_tree_by_path(self, path: str | Sequence[str]) -> None:
        """删除由路径指定的子树。路径规则见 :meth:`get_node_by_path`。"""

        node = self.get_node_by_path(path)
        if node is self:
            raise ValueError("不允许删除根节点自身")
        node.parent = None

    # ------------------------------------------------------------------
    # JSON 序列化 / 反序列化
    # ------------------------------------------------------------------
    def _to_dict(self) -> dict:
        """递归转为可 JSON 序列化的字典。"""
        return {
            "title": self.title,
            "summary": self.summary,
            "created_at": self.created_at.isoformat(),
            "children": [c._to_dict() for c in self.children],
        }

    @classmethod
    def _from_dict(cls, data: dict, parent: "Experience" | None = None) -> "Experience":
        """递归从字典构建树。"""
        created_at = None
        if ts := data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(ts)
            except ValueError:
                pass
        node = cls(
            title=data["title"],
            summary=data.get("summary", ""),
            created_at=created_at,
            parent=parent,
        )
        for child_data in data.get("children", []):
            cls._from_dict(child_data, parent=node)
        return node

    def export_to_json_file(self, file_path: str | Path) -> None:
        """将当前节点作为根的整棵树导出到 JSON 文件。"""
        path = Path(file_path)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self._to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def import_from_json_file(cls, file_path: str | Path) -> "Experience":
        """从 JSON 文件构建并返回树根节点。"""
        path = Path(file_path)
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return cls._from_dict(data)

# =====================================================================
# 演示
# =====================================================================
if __name__ == "__main__":
    from textwrap import indent

    root = Experience("root", "")
    exp1 = Experience("工程可研", "", parent=root)
    exp11 = Experience("经验1", "要有设计依据", parent=exp1)
    exp12 = Experience("经验2", "投资估算很重要", parent=exp1)

    exp2 = Experience("科技可研", "", parent=root)
    exp21 = Experience("经验1", "必要性很关键", parent=exp2)
    exp22 = Experience("经验2", "方案很重要", parent=exp2)

    print("0) 整棵树 (title+summary):\n" + indent(root.get_tree_all_string(), "   "))

    # 相对路径
    node = root.get_node_by_path("工程可研/经验1")
    print(f"1) 相对路径成功找到节点: {node!r}")

    # 绝对路径
    node_abs = root.get_node_by_path("root/科技可研/经验2")
    print(f"2) 绝对路径成功找到节点: {node_abs!r}")

    # 删除相对路径
    root.del_node_tree_by_path("科技可研/经验1")
    print("3) '科技可研/经验1' 删除后 (title) (get_tree_title_string):\n" + indent(root.get_tree_title_string(), "   "))

    # 相对路径下add node
    root.add_node_by_path("科技可研/经验3", '好好吃饭')
    print("4) '科技可研/经验3' add后 (title):\n" + indent(root.get_tree_all_string(), "   "))

    # 绝对路径下add node
    root.add_node_by_path("root/科技可研/经验4", '好好休息')
    print("5-1) 'root/科技可研/经验4' add后 (title):\n" + indent(root.get_tree_all_string(), "   "))

    # 绝对路径下add node
    root.add_node_by_path("root/资料管理/经验1", '好好吃瓜')
    print("5-2) 'root/资料管理/经验1' add后 (title):\n" + indent(root.get_tree_all_string(), "   "))

    # 相对路径下add node
    root.add_node_by_path("图纸设计/评审/经验1", '好好喝酒')
    print("5-3) '图纸设计/评审/经验1' add后 (title):\n" + indent(root.get_tree_all_string(), "   "))

    # 绝对路径下add node
    root.add_node_by_path("root/图纸设计/审图/经验1", '好好逛街')
    print("5-4) 'root/图纸设计/审图/经验1' add后 (title):\n" + indent(root.get_tree_all_string(), "   "))

    # 绝对路径下add node
    root.add_node_by_path("root/招投标/招标/标书编制/经验1", '好好逛街')
    print("5-5) 'root/招投标/招标/标书编制/经验1' add后 (title):\n" + indent(root.get_tree_all_string(), "   "))

    # 相对路径下add node
    root.add_node_by_path("招投标/招标/标书编制/技术部分/经验1", '好好游戏')
    print("5-6) 'root/招投标/招标/标书编制/经验1' add后 (title):\n" + indent(root.get_tree_all_string(), "   "))

    # 导出 JSON
    root.export_to_json_file("exp_tree.json")
    print("\n1) 已导出到 exp_tree.json")

    # 重新导入
    new_root = Experience.import_from_json_file("exp_tree.json")
    print("\n2) 重新导入后 (title):\n" + indent(new_root.get_tree_all_string(), "   "))

    # 断言两棵树结构一致（按 title 遍历）
    assert root.get_tree_all_string() == new_root.get_tree_all_string()
    print("\n全部断言通过，演示结束！🎉")