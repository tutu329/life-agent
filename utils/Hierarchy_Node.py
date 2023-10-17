from dataclasses import dataclass

@dataclass
class _test_node_data():
    level: int
    name: str
    text: str

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
        print(f'查找节点: {self.node_data.name}')
        if self.node_data.name == in_node_name:
            print(f'--------找到了node: {self.node_data.name}---------')
            return self # 返回所找到的node对象

        if self.children:
            print(f'准备进入子节点: [' + ', '.join([child.node_data.name for child in self.children]) + ']')
        for child in self.children:
            res = child.find(in_node_name)
            if res is not None:
                return res
        return None

def main():
    root = Hierarchy_Node(_test_node_data(0, '0', 'aaa'))
    node_1 = Hierarchy_Node(_test_node_data(1, '1', 'abc'))
    node_1_1 = Hierarchy_Node(_test_node_data(2, '1.1', 'cde'))
    node_1_2 = Hierarchy_Node(_test_node_data(2, '1.2', 'fea'))

    node_2 = Hierarchy_Node(_test_node_data(1, '2', 'abc'))
    node_2_1 = Hierarchy_Node(_test_node_data(2, '2.1', 'fhn'))
    node_2_2 = Hierarchy_Node(_test_node_data(2, '2.2', 'hww'))

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

if __name__ == "__main__":
    main()
