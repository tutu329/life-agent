# 递归将dict数据由byte转为utf-8的str（其中，图片的byte不转）
def data_convert_from_byte_to_str(data):
    if isinstance(data, dict):
        if b'chunk_use_byte' in data and data[b'chunk_use_byte'] == b'1':
            # 例如，如果为image的byte数据，该dict中的chunk的v不转为utf-8 string
            rtn = {}
            for k, v in data.items():
                if k==b'chunk':
                    rtn[data_convert_from_byte_to_str(k)] = v
                else:
                    rtn[data_convert_from_byte_to_str(k)] = data_convert_from_byte_to_str(v)
            return rtn
        else:
            return {data_convert_from_byte_to_str(k): data_convert_from_byte_to_str(v) for k, v in data.items()}

    elif isinstance(data, list):
        return [data_convert_from_byte_to_str(item) for item in data]
    elif isinstance(data, bytes):
        return data.decode('utf-8')
    else:
        return data

def main():
    data = [b'my string', b'heihei']
    # data = {b'key1': b'value1', b'key2': b'value2'}
    print(data)
    print(data_convert_from_byte_to_str(data))

if __name__ == "__main__":
    main()