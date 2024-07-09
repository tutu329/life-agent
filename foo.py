import chardet

# 假设原始字符串为未知编码
original_string = "这是一个测试字符串"
print(f'original_string:{original_string}')

# 将原始字符串编码为字节对象
original_bytes = original_string.encode()
print(f'original_bytes:{original_bytes}')

# 检测原始字符串的编码格式
detected_encoding = chardet.detect(original_bytes)['encoding']
print(f'detected_encoding:{detected_encoding}')

# 将原始字符串从检测到的编码格式解码为Unicode
unicode_string = original_bytes.decode(detected_encoding)
print(f'unicode_string:{unicode_string}')

# 将Unicode字符串编码为UTF-8
utf8_string = unicode_string.encode('utf-8')
print(f'utf8_string:{utf8_string}')

