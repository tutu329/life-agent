import json5

def parse_note_json(data_list):
    i=0
    total=0
    c_list = []
    sub_list = []

    # for item in x:
    #     i += 1
    #     print(f'{item}')
    #     for k,v in item.items():
    #         #if True:
    #         if k=='content' or k=='parent_comment_id' or k=='comment_id':
    #             print(f'{k}:{v}')
    #     print()


    for item in data_list:
        total += 1
        for k,v in item.items():
            if k=='parent_comment_id' and v==0:
                i += 1
                c_list.append(item)

    sub1=0
    for item in data_list:
        for k,v in item.items():
            if k=='parent_comment_id' and v!=0:
                sub1 += 1
                sub_list.append(item)

    sub2=0
    index=0
    for item in c_list:
        index += 1
        print(f'{index}) {item["nickname"]}: {item["content"]}')
        for sub in sub_list:
            if sub['parent_comment_id'] == item['comment_id']:
                sub2 += 1
                print(f'\t {sub["nickname"]}:{sub["content"]}')
                for subsub in sub_list:
                    if subsub['parent_comment_id'] == sub['comment_id']:
                        print(f'\t\t {subsub["nickname"]}:{subsub["content"]}')

    print(f'total={total}')
    print(f'parent={i}')
    print(f'sub1={sub1}')
    print(f'sub2={sub2}')


def main():

    # 读取文件a.json中的JSON数据
    # with open(r'C:\Users\tutu\MediaCrawler\data\xhs\json\search_contents_2024-07-02.json', 'r', encoding='utf-8') as file:
    # with open(r'C:\Users\tutu\MediaCrawler\data\xhs\json\creator_creator_2024-07-02.json', 'r', encoding='utf-8') as file:
    # with open(r'C:\Users\tutu\MediaCrawler\data\xhs\json\creator_contents_2024-07-02.json', 'r', encoding='utf-8') as file:
    # with open(r'creator_contents_2024-07-02-hdstudio.json', 'r', encoding='utf-8') as file:
    with open(r'creator_contents_2024-07-02-摘菌大婶.json', 'r', encoding='utf-8') as file:
        data = json5.load(file)

    parse_note_json(data_list=data)
    # parse_json(data_list=x)

    for item in data:
        print(item)
        for k,v in item.items():
            # if k=='title':
            print(f'\t{k}:{v}')

if __name__ == "__main__":
    main()
