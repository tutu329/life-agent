from typing import List, Dict, Any, Optional, Type
import httpx                     # pip install httpx

# ========= 你的基础抽象类 =========
class Dynamic_Tool_Base:
    name: str
    description: str
    parameters: List[Dict]

    # 这里保留空实现，子类会覆写为 classmethod
    def call(self, para_dict: Dict[str, Any]) -> Any:  # type: ignore[override]
        raise NotImplementedError


# ========= 动态注册函数 =========
def register_tool_class(
        name: str,
        description: str,
        parameters: List[Dict],
        *,
        endpoint_url: str,
        method: str = "POST",
        timeout: float = 10.0,
        headers: Optional[Dict[str, str]] = None,
) -> Type[Dynamic_Tool_Base]:
    """
    生成并返回一个继承 Base_Tool 的新类；其 call() 为 @classmethod，
    会向指定 FastAPI 端点发送 HTTP 请求。
    """

    # ---------- classmethod 版本的 call ----------
    def _call(cls, para_dict: Dict[str, Any]) -> Any:         # noqa: D401
        """
        向远程 FastAPI 发送请求并返回 JSON（classmethod 形式）
        """
        try:
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
            raise RuntimeError(f"[{cls.name}] remote call failed: {exc}") from exc

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
        "call": classmethod(_call),

        "__doc__": f"Dynamically generated tool that proxies {endpoint_url}",
    }

    # ---------- 动态造类 ----------
    DynamicToolClass = type(f"{name.replace(' ', '')}Tool", (Dynamic_Tool_Base,), attrs)

    return DynamicToolClass

def main():
    # 生成 “类”
    Remote_Folder_Tool = register_tool_class(
        name="Remote_Folder_Tool",
        description="返回远程服务器上指定文件夹下所有文件和文件夹的名字信息。",
        parameters=[{"name": "file_path", "type": "string"}],
        endpoint_url="http://localhost:5120/remote_tool_call",
        method="POST",
        timeout=15,
    )

    # 直接用类名调用 classmethod
    result = Remote_Folder_Tool.call({"file_path": "./"})
    print(f"远端返回：{result!r}")
    print(result['result_str'])

# ============= 示范用法 =============
if __name__ == "__main__":
    main()
