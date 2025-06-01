def safe_encode(text):
    """安全编码文本，处理特殊字符(如：110kV��������������ͼ.jpg)"""
    # 用于解决报错：UnicodeEncodeError: 'utf-8' codec can't encode characters in position 71-78: surrogates not allowed
    if isinstance(text, str):
        # 移除或替换代理对字符
        try:
            # 尝试编码为UTF-8并解码，清理无效字符
            text = text.encode('utf-8', 'ignore').decode('utf-8')
            # 替换代理对字符
            text = text.encode('utf-8', 'replace').decode('utf-8')
        except Exception:
            text = repr(text)  # 如果还有问题，转为字符串表示
    return text