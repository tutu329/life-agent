import base64
import requests
from PIL import Image
from io import BytesIO
import matplotlib.pyplot as plt

# 显示图片字节流
def show_image_from_bytes(image_bytes):
    img = Image.open(BytesIO(image_bytes))
    plt.imshow(img)
    plt.axis('off')  # 隐藏坐标轴
    plt.show()

# 显示本地图片
def show_local_image(image_path):
    img = Image.open(image_path)
    plt.imshow(img)
    plt.axis('off')  # 隐藏坐标轴
    plt.show()

# 返回本地图片的字节流
def get_local_image_bytes(image_path):
    img = Image.open(image_path)
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format=img.format)  # 使用图片的原始格式保存
    img_byte_arr.seek(0)  # 将指针移动到流的开始
    return img_byte_arr.getvalue()

# 显示URL图片
def show_url_image(image_url):
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))
    plt.imshow(img)
    plt.axis('off')  # 隐藏坐标轴
    plt.show()

# 返回URL图片的字节流
def get_url_image_bytes(image_url):
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format=img.format)  # 使用图片的原始格式保存
    img_byte_arr.seek(0)  # 将指针移动到流的开始
    return img_byte_arr.getvalue()

# 将图片字节流转换为 Base64 编码
def bytes_to_base64(image_bytes):
    base64_str = base64.b64encode(image_bytes).decode('utf-8')
    return base64_str

# 将 Base64 编码转换为图片字节流
def base64_to_bytes(base64_str):
    image_bytes = base64.b64decode(base64_str)
    return image_bytes

def main():
    url = 'https://picsum.photos/seed/picsum/200/300'
    path = 'd:\\512.jpg'
    # show_url_image(url)
    # show_local_image(path)
    show_image_from_bytes(base64_to_bytes(bytes_to_base64(get_local_image_bytes(path))))
    show_image_from_bytes(base64_to_bytes(bytes_to_base64(get_url_image_bytes(url))))

if __name__ == "__main__":
    main()