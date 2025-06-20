from typing import List, Dict, Any, Optional, Type
import httpx                     # pip install httpx

from agent.tools.protocol import Tool_Call_Paras
from agent.tools.base_tool import Base_Tool
from agent.tools.protocol import Registered_Remote_Tool_Data

# ========= server动态注册函数 =========
def generate_tool_class_dynamically(
    registered_remote_tool_data:Registered_Remote_Tool_Data
) -> Type[Base_Tool]:
    """
    生成并返回一个继承 Base_Tool 的新类；其 call() 为 @classmethod，
    会向指定 FastAPI 端点发送 HTTP 请求。
    """
    name = registered_remote_tool_data.name
    description = registered_remote_tool_data.description
    parameters = registered_remote_tool_data.parameters
    endpoint_url = registered_remote_tool_data.endpoint_url
    method = registered_remote_tool_data.method
    timeout = registered_remote_tool_data.timeout
    headers = registered_remote_tool_data.headers

    # ---------- classmethod 版本的 call ----------
    # def _call(cls, para_dict: Dict[str, Any]) -> Any:         # noqa: D401
    def _call(self, tool_call_paras:Tool_Call_Paras)->Any:
        """
        向远程 FastAPI 发送请求并返回 JSON（classmethod 形式）
        """
        para_dict = tool_call_paras.callback_tool_paras_dict
        try:
            print(f'-------------------已注册{name}.call()获得的参数----------------------')
            print(f'{para_dict}')
            print(f'------------------/已注册{name}.call()获得的参数----------------------')

            # 标准的 json 模块只认识 Python 原生类型（dict / list / str …），并不知道 Pydantic 的 BaseModel 要怎么变成可写入的 JSON 字符串
            # 因此要转为dict：Pydantic v2 用 model_dump()；v1 用 dict()
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                if method.upper() == "POST":
                    resp = client.post(endpoint_url, json=tool_call_paras.model_dump(), headers=headers)
                elif method.upper() == "GET":
                    resp = client.get(endpoint_url, params=tool_call_paras.model_dump(), headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                resp.raise_for_status()
                return resp.json()          # FastAPI 默认 JSON
        except Exception as exc:
            # 这里可以做统一的日志或错误包装
            raise RuntimeError(
                f"[{self.name}] remote call failed: {exc}"
            ) from exc

    # ---------- 组装类属性 ----------
    attrs = {
        # 显式保存配置，供其他类方法或调试用
        "_endpoint_url": endpoint_url,
        "_http_method": method.upper(),
        "_timeout": timeout,
        "_headers": headers or {},

        # 公共元数据
        "name": name,
        "description": description,
        "parameters": parameters,

        # classmethod; 不能直接写 "_call"，要用 `classmethod()` 包装
        "call": _call,
        # "call": classmethod(_call),

        "__doc__": f"Dynamically generated tool that proxies {endpoint_url}",
    }

    # ---------- 动态造类 ----------
    DynamicToolClass = type(name, (Base_Tool,), attrs)
    # DynamicToolClass = type(name, (Remote_Tool_Base,), attrs)

    return DynamicToolClass

def main_test_tool_call():
    from agent.core.agent_config import Agent_Config
    # 生成 “类”
    para = Registered_Remote_Tool_Data(
        name="Remote_Folder_Tool",
        description="返回远程服务器上指定文件夹下所有文件和文件夹的名字信息。",
        parameters=[{"name": "file_path", "type": "string"}],
        endpoint_url="http://localhost:5120/Folder_Tool",   # 'Folder_Tool'大小写必须正确
        # endpoint_url="http://localhost:5120/remote_folder_tool",
        method="POST",
        timeout=15,
    )
    Remote_Folder_Tool = generate_tool_class_dynamically(para)

    # 直接用类名调用 classmethod
    tool_call_paras = Tool_Call_Paras(
        callback_tool_paras_dict={"dir": "./"},     # 'dir'必需与Folder_Tool的parameters一致
        # callback_tool_paras_dict={"file_path": "./"},
        callback_agent_config=Agent_Config(),
        callback_agent_id='xxxxxxxx',
        callback_last_tool_ctx=None,
        callback_father_agent_exp='',
    )
    result = Remote_Folder_Tool().call(tool_call_paras)
    print(f"远端返回：{result!r}")

# ============= 示范用法 =============
if __name__ == "__main__":
    main_test_tool_call()
