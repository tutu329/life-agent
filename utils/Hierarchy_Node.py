from dataclasses import dataclass
from utils.Fuzzy_Search import like_match, wratio, partial_match

Hierarchy_Node_DEBUG = False

def dprint(*args, **kwargs):
    if Hierarchy_Node_DEBUG:
        print(*args, **kwargs)

@dataclass
class _test_node_data():
    level: int      # 必需属性：如: 1, 2, 3
    name: str       # 必需属性：如: '1.1.3'
    heading: str    # 必需属性：如: '建设必要性'
    text: str       # 如: '本项目建设是必要的...'

class Hierarchy_Node:
    def __init__(self, node_data):
        self.node_data = node_data
        self.children = []

    def __str__(self):
        members = type(self.node_data).__annotations__  # 获取dataclass类型的所有属性
        members_str = []                                # 获取dataclass类型的所有属性数据，如 level: 2, name: 2.2, text: hww
        for k, v in members.items():
            members_str.append(k + ': ' + str(getattr(self.node_data, k)))

        if hasattr(self.node_data, 'name'):
            members_str.append('children: [' + ', '.join([child.node_data.name for child in self.children]) + ']')
        return ', '.join(members_str)

    def add_child(self, child):
        self.children.append(child)

    def find_similar_by_head(self, in_toc_heading_has_index, in_node_name):
        dprint(f'查找节点: {self.node_data.heading}')
        # if self.node_data.heading == in_node_name:

        # 通常这时已统计判断过self.toc_heading_has_index
        if in_toc_heading_has_index == True:
            simi = wratio(self.node_data.heading, in_node_name)
            print(f'--------node: "{self.node_data.heading}"-相似度: {simi}--------')
        else:
            # head = self.node_data.name + ' ' + self.node_data.heading
            # simi = like_match(head, in_node_name)
            simi = wratio(self.node_data.heading, in_node_name) # 最后发现中文similar比较，"8 投资估算 8.2 投资概算"这样的标题和"8.2 投资概算"比较，不如和“投资概算”比较准确，且需要用wrato而不是simple_match
            print(f'--------node: "{self.node_data.heading}"-相似度: {simi}--------')

        # simi = wratio(self.node_data.heading, in_node_name)
        # if in_node_name.replace('"', '') in self.node_data.heading :
        # if in_node_name.replace('"', '').replace("'", "") in self.node_data.heading :
        if in_node_name.replace('"', '').replace("'", "") in self.node_data.heading or simi>=60 :
            return self # 返回所找到的node对象

        if self.children:
            dprint(f'准备进入子节点: [' + ', '.join([child.node_data.name for child in self.children]) + ']')
        for child in self.children:
            # print('##################################################################################')
            res = child.find_similar_by_head(in_toc_heading_has_index, in_node_name)
            if res is not None:
                return res
        return None

    def find_similar_node_by_head_and_ask_llm(self, in_toc_heading_has_index, in_node_name):
        inout_similar_node_list = []
        self._find_all_similar_nodes_by_head(
            inout_similar_node_list,
            in_toc_heading_has_index,
            in_node_name
        )

        for node in inout_similar_node_list:
            print(f'node: "{node.node_data.name + " " + node.node_data.heading}"--------')

    def _find_all_similar_nodes_by_head(self, inout_similar_node_list, in_toc_heading_has_index, in_node_name):
        # ===========将"一次性返回相似度>60的node"，改为"返回子字符串或者模糊相关度大于0的所有node"，然后再问llm选取chapter===========
        dprint(f'查找节点: {self.node_data.name + " " + self.node_data.heading}')
        # if self.node_data.heading == in_node_name:

        # 通常这时已统计判断过self.toc_heading_has_index
        if in_toc_heading_has_index == True:
            simi = wratio(self.node_data.heading, in_node_name)
            print(f'--------node: "{self.node_data.heading}"-相似度: {simi}--------')
        else:
            simi = wratio(self.node_data.name + " " + self.node_data.heading, in_node_name) # 最后发现中文similar比较，"8 投资估算 8.2 投资概算"这样的标题和"8.2 投资概算"比较，不如和“投资概算”比较准确，且需要用wrato而不是simple_match
            print(f'--------node: "{self.node_data.name + " " + self.node_data.heading}"-相似度: {simi}--------')

        if in_node_name.replace('"', '').replace("'", "") in self.node_data.heading or simi > 0 :
            inout_similar_node_list.append(self)
            # return self

        if self.children:
            dprint(f'准备进入子节点: [' + ', '.join([child.node_data.name for child in self.children]) + ']')
        for child in self.children:
            # print('##################################################################################')
            res = child._find_all_similar_nodes_by_head(inout_similar_node_list, in_toc_heading_has_index, in_node_name)
            if res is not None:
                return res
        return None
    def find(self, in_node_name):
        dprint(f'查找节点: {self.node_data.name}')
        if self.node_data.name == in_node_name:
            dprint(f'--------找到了node: {self.node_data.name}---------')
            return self # 返回所找到的node对象

        if self.children:
            dprint(f'准备进入子节点: [' + ', '.join([child.node_data.name for child in self.children]) + ']')
        for child in self.children:
            res = child.find(in_node_name)
            if res is not None:
                return res
        return None

    def find_by_head(self, in_head_name):
        dprint(f'查找节点: {self.node_data.heading}')
        if in_head_name in self.node_data.heading:
            dprint(f'--------找到了node: {self.node_data.heading}---------')
            return self # 返回所找到的node对象

        if self.children:
            dprint(f'准备进入子节点: [' + ', '.join([child.node_data.heading for child in self.children]) + ']')
        for child in self.children:
            res = child.find_by_head(in_head_name)
            if res is not None:
                return res
        return None

    # 获取node下目录(table of content)的md格式
    def get_toc_md_for_tool(
            self,
            inout_toc_md_list,
            in_node='root',
            in_max_level=3,
            in_if_head_has_index=True,  # 标题中是否有1.1.3
            in_if_render=False,         # 是否输出缩进和高亮
            in_if_md_head=True,         # 是否增加'### '
    ):
        if in_if_render:
            blank_str = '&emsp;'
            highlight_mark = '<mark>'
            highlight_mark_end = '</mark>'
        else:
            blank_str = ''
            highlight_mark = ''
            highlight_mark_end = ''

        # 如果输入'1.1.3'这样的字符串
        if type(in_node)==str:
            node_s = in_node
            in_node = self.find(node_s)
            if in_node is None:
                print(f'节点"{node_s}"未找到.')
                inout_toc_md_list = []
                return

        # 如果输入Hierarchy_Node对象
        if in_node is None:
            inout_toc_md_list = []
            return
        else:
            node = in_node

        dprint(f'进入节点{node.node_data.name}')

        # 处理当前node的数据
        if node.node_data.level > 0:
            if node.node_data.level==1:
                color_string = highlight_mark
                # color_string = '<<table><tr><td bgcolor="grey">'
                color_string_end = highlight_mark_end
                # color_string_end = '</td></tr></table>'
            else:
                color_string = color_string_end = ''

            if in_if_md_head==True:
                md_index_head = '#'*node.node_data.level + ' '
            else:
                md_index_head = ''

            if in_if_head_has_index==True:
                # 标题为"1.1.3 建设规模"
                inout_toc_md_list.append(
                    # f'<font size={10-node.node_data.level}>' + ' ' + '&emsp;'*(node.node_data.level-1) +        # 注意中间那个空格' '必须有。'&emsp;'用于写入硬的空格
                    md_index_head + color_string + blank_str*(node.node_data.level-1) +        # 注意md_index_head的那个空格' '必须有。'&emsp;'用于写入硬的空格
                    # node.node_data.name.strip() + ' ' +
                    node.node_data.heading.strip() + color_string_end
                    # node.node_data.heading.strip() + '</font>'
                )
            else:
                # 标题为"建设规模"
                inout_toc_md_list.append(
                    # f'<font size={10-node.node_data.level}>' + ' ' + '&emsp;'*(node.node_data.level-1) +        # 注意中间那个空格' '必须有。'&emsp;'用于写入硬的空格
                    md_index_head + color_string + blank_str * (node.node_data.level-1) +  # 注意md_index_head的那个空格' '必须有。'&emsp;'用于写入硬的空格
                    node.node_data.name.strip() + ' ' +
                    node.node_data.heading.strip() + color_string_end
                    # node.node_data.heading.strip() + '</font>'
                )

        if node.node_data.level < in_max_level:
            child_list = []
            # 遍历child node
            for child in node.children:
                self.get_toc_md_for_tool(child_list, child, in_max_level, in_if_head_has_index=in_if_head_has_index, in_if_render=in_if_render)
            if child_list != []:
                inout_toc_md_list += child_list    # 这里和get_toc_list_json（）的list1.append(list2)形成[1.1, 1.2, [1.2.1, 1.2.2]]不一样，这里是形成[#1.1, #1.2, ##1.2.1, ##1.2.2]

        return

    # 获取node下目录(table of content)的json格式，list形式，节省字符串长度
    def get_toc_list_json(self, inout_toc_json_list, in_node='root', in_max_level=3):
        # 如果输入'1.1.3'这样的字符串
        if type(in_node)==str:
            node_s = in_node
            in_node = self.find(node_s)
            if in_node is None:
                print(f'节点"{node_s}"未找到.')
                inout_toc_json_list = []
                return

        # 如果输入Hierarchy_Node对象
        if in_node is None:
            inout_toc_json_list = []
            return
        else:
            node = in_node

        dprint(f'进入节点{node.node_data.name}')

        # 处理当前node的数据
        inout_toc_json_list.append(node.node_data.name + ' ' + node.node_data.heading)
        # inout_toc_json_list.append(node.node_data.heading)

        if node.node_data.level < in_max_level:
            child_list = []
            # 遍历child node
            for child in node.children:
                self.get_toc_list_json(child_list, child, in_max_level)
            if child_list != []:
                inout_toc_json_list.append(child_list)

        return

    # 获取node下目录(table of content)的json格式，dict形式，比较占用字符串长度
    def get_toc_dict_json(self, inout_toc_json_dict, in_node='root', in_max_level=3):
        # 如果输入'1.1.3'这样的字符串
        if type(in_node)==str:
            node_s = in_node
            in_node = self.find(node_s)
            if in_node is None:
                print(f'节点"{node_s}"未找到.')
                inout_toc_json_dict = {}
                return

        # 如果输入Hierarchy_Node对象
        if in_node is None:
            inout_toc_json_dict = {}
            return
        else:
            node = in_node

        dprint(f'进入节点{node.node_data.name}')

        # 处理当前node的数据
        inout_toc_json_dict['name'] = node.node_data.name + ' ' + node.node_data.heading
        # inout_toc_json_dict['head'] = node.node_data.heading
        inout_toc_json_dict['ch'] = []

        if node.node_data.level < in_max_level:
            # 遍历child node
            for child in node.children:
                child_dict = {}
                self.get_toc_dict_json(child_dict, child, in_max_level)
                inout_toc_json_dict['ch'].append(child_dict)

        if inout_toc_json_dict['ch'] == []:
            del inout_toc_json_dict['ch']

        return

def main():
    root = Hierarchy_Node(_test_node_data(0, '0', '标题0', 'aaa'))
    node_1 = Hierarchy_Node(_test_node_data(1, '1', '标题1', 'abc'))
    node_1_1 = Hierarchy_Node(_test_node_data(2, '1.1','标题2',  'cde'))
    node_1_2 = Hierarchy_Node(_test_node_data(2, '1.2', '标题2', 'fea'))

    node_2 = Hierarchy_Node(_test_node_data(1, '2', '标题1', 'abc'))
    node_2_1 = Hierarchy_Node(_test_node_data(2, '2.1', '标题2', 'fhn'))
    node_2_2 = Hierarchy_Node(_test_node_data(2, '2.2', '标题2', 'hww'))

    root.add_child(node_1)
    root.add_child(node_2)
    node_1.add_child(node_1_1)
    node_1.add_child(node_1_2)
    node_2.add_child(node_2_1)
    node_2.add_child(node_2_2)

    print(root)
    print(node_1)
    print(node_1_1)
    print(node_1_2)
    print(node_2)
    print(node_2_1)
    print(node_2_2)
    print('=' * 80)


    res = root.find('1.2')
    print(f'res: {res}')

    toc = {}
    root.get_toc_dict_json(toc, root)

    import json
    print(json.dumps(toc, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
