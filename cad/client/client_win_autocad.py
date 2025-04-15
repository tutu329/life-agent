import win32com.client
from config import dred, dyellow, dgreen, dblue, dcyan

def main():
    dgreen('正在打开CAD...')

    # 连接到 AutoCAD 实例，如果没有打开 AutoCAD，会启动一个新的实例
    acad = win32com.client.Dispatch("AutoCAD.Application")
    acad.Visible = True  # 设置AutoCAD界面可见
    dgreen('CAD实例已启动.')

    # 打开一个现有的 CAD 文件
    file_name = r'C:\Mac\Home\Desktop\cad\附图1 电气主接线图-5-5.dwg'
    try:
        # 使用Open方法打开文件
        doc = acad.Documents.Open(file_name)
    except Exception as e:
        dred(f'CAD文件打开出错："{e}"')
        dblue('可能需要默认忽视外部参考.')  # 可能解决这个报错：property 'ActiveDocument' of 'Autocad' object has no setter
        exit()

    dgreen(f'CAD文件 {file_name} 已打开.')

    # 获取当前文档的模型空间
    model_space = doc.ModelSpace

    # 存储所有矩形对象的边界
    rectangles = []

    # 遍历模型空间中的所有对象
    # ==========================这种遍历方式极慢，一个简单的电气主接线图，几分钟也遍历不完========================================
    for obj in model_space:
        try:
            # print(f"正在处理对象：{obj.ObjectName}")
            if obj.ObjectName == "AcDbLine":
                start_point = obj.StartPoint
                end_point = obj.EndPoint

                # 判断是否为水平或垂直线段（矩形的四条边）
                if start_point[0] == end_point[0] or start_point[1] == end_point[1]:
                    print(f'x: {start_point[0]}, y: {start_point[1]}')
                    rectangles.append(obj)
        except Exception as e:
            dblue(f'无法访问对象：{e}')
    # ==========================这种遍历方式极慢，一个简单的电气主接线图，几分钟也遍历不完========================================

    # 打印矩形的坐标
    for rect in rectangles:
        print(f'x: {rect.StartPoint[0]}, y: {rect.StartPoint[1]}')

if __name__ == "__main__":
    main()
