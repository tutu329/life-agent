from dataclasses import dataclass

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
