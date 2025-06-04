from typing import List, Dict, Any, Optional, Type
import httpx                     # pip install httpx

# ========= 你的基础抽象类 =========
class Remote_Tool_Base:
    name: str
    description: str
    parameters: List[Dict]

    # 这里保留空实现，子类会覆写为 classmethod
    def call(self, para_dict: Dict[str, Any]) -> Any:  # type: ignore[override]
        raise NotImplementedError


# ========= 动态注册函数 =========
def generate_tool_class_dynamically(
        name: str,
        description: str,
        parameters: List[Dict],
        *,
        endpoint_url: str,
        method: str = "POST",
        timeout: float = 10.0,
        headers: Optional[Dict[str, str]] = None,
) -> Type[Remote_Tool_Base]:
    """
    生成并返回一个继承 Base_Tool 的新类；其 call() 为 @classmethod，
    会向指定 FastAPI 端点发送 HTTP 请求。
    """

    # ---------- classmethod 版本的 call ----------
    # def _call(cls, para_dict: Dict[str, Any]) -> Any:         # noqa: D401
    def _call(
        self,
        callback_tool_paras_dict,
        callback_agent_config,
        callback_agent_id,
        callback_last_tool_ctx,
        callback_father_agent_exp,
    ) -> Any:         # noqa: D401
        """
        向远程 FastAPI 发送请求并返回 JSON（classmethod 形式）
        """
        para_dict = callback_tool_paras_dict
        try:
            print(f'-------------------已注册Remote_Tool_Class.call()的参数----------------------')
            print(f'{para_dict}')
            print(f'------------------/已注册Remote_Tool_Class.call()的参数----------------------')
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                if method.upper() == "POST":
                    resp = client.post(endpoint_url, json=para_dict, headers=headers)
                elif method.upper() == "GET":
                    resp = client.get(endpoint_url, params=para_dict, headers=headers)
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
    DynamicToolClass = type(name, (Remote_Tool_Base,), attrs)

    return DynamicToolClass

def main():
    # 生成 “类”
    Remote_Folder_Tool = generate_tool_class_dynamically(
        name="Remote_Folder_Tool",
        description="返回远程服务器上指定文件夹下所有文件和文件夹的名字信息。",
        parameters=[{"name": "file_path", "type": "string"}],
        endpoint_url="http://localhost:5120/remote_tool_call",
        method="POST",
        timeout=15,
    )

    # 直接用类名调用 classmethod
    result = Remote_Folder_Tool().call(
        callback_tool_paras_dict={"file_path": "./"},
        callback_agent_config=None,
        callback_agent_id=None,
        callback_last_tool_ctx=None,
        callback_father_agent_exp=None,
    )
    # result = Remote_Folder_Tool().call({"file_path": "./"})
    print(f"远端返回：{result!r}")
    # print(result['result_str'])

# ============= 示范用法 =============
if __name__ == "__main__":
    main()
