import json
import os
from pathlib import Path
from typing import Any, Dict


class DataProvider:
    """数据提供器：优先从后端获取，失败则回退到 mock JSON 文件。"""

    def __init__(self, data_dir: str = None, backend_host: str = "localhost", backend_port: int = 50051):
        self.backend_host = backend_host
        self.backend_port = backend_port
        base = data_dir or Path(__file__).resolve().parents[1]
        self.data_dir = Path(base) / "data"
        self.mock_path = self.data_dir / "log.json"

    def load_from_backend(self) -> Dict[str, Any]:
        """尝试从真实后端加载游戏数据，后端不可用时抛出异常。"""
        try:
            import grpc
            from grpc_client import message_pb2, message_pb2_grpc

            target = f"{self.backend_host}:{self.backend_port}"
            with grpc.insecure_channel(target) as channel:
                stub = message_pb2_grpc.GameServiceStub(channel)
                # 这里使用 SendInit 接口进行探测。真实接口根据后端定义调整。
                init_request = message_pb2._InitRequest(message="ping")
                response = stub.SendInit(init_request)

                # if response is valid,后端正常
                return {
                    "backend_alive": True,
                    "init_response": {
                        "id": response.id if hasattr(response, 'id') else -1,
                        "message": getattr(response, 'message', '')
                    }
                }
        except Exception as e:
            raise ConnectionError(f"无法连接到后端 {self.backend_host}:{self.backend_port}，原因: {e}")

    def load_from_mock(self) -> Dict[str, Any]:
        """从本地 mock 数据文件加载游戏日志，供可视化开发使用。"""
        if not self.mock_path.exists():
            raise FileNotFoundError(f"Mock 数据文件未找到: {self.mock_path}")

        with open(self.mock_path, 'r', encoding='utf-8') as f:
            text = f.read()
            if not text.strip():
                raise ValueError("Mock 数据文件为空")
            return json.loads(text)

    def get_game_data(self, prefer_backend: bool = True) -> Dict[str, Any]:
        """获取游戏数据：优先后端，再 mock。"""
        if prefer_backend:
            try:
                return self.load_from_backend()
            except Exception:
                # 后端连不上，使用本地 mock
                return self.load_from_mock()
        else:
            return self.load_from_mock()
