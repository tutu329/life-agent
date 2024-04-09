import uuid

def string_to_id(in_string):
    return str(uuid.uuid3(uuid.NAMESPACE_DNS, in_string))
def main():
    # 定义字符串
    string = "Hello, World!"

    # 使用字符串来生成UUID
    custom_uuid = uuid.uuid3(uuid.NAMESPACE_DNS, string)

    print(custom_uuid)
    print(string_to_id(string))

if __name__ == "__main__" :
    main()