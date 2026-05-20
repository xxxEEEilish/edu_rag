"""项目路径工具。

统一路径计算可以避免各模块依赖当前工作目录。后续导入文件、临时解析产物
和测试数据都应通过这里构造路径。
"""

from pathlib import Path


# 仓库根目录。`core/paths.py` 位于 core 下，因此 parents[1] 指向项目根。
ROOT_DIR = Path(__file__).resolve().parents[1]

# 临时数据目录用于后续解析中间产物、测试文件或本地缓存。
TEMP_DATA_DIR = ROOT_DIR / "temp_data"


def project_path(*parts: str) -> Path:
    """返回项目根目录下的路径。

    参数按路径片段传入，避免调用方手动拼接字符串导致跨平台分隔符问题。
    """
    return ROOT_DIR.joinpath(*parts)


def temp_path(*parts: str) -> Path:
    """返回临时数据目录下的路径。

    该函数只负责构造路径，不负责创建目录；是否创建由具体业务流程决定。
    """
    return TEMP_DATA_DIR.joinpath(*parts)
