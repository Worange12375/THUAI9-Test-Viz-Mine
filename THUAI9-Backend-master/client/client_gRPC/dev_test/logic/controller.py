import os
import sys
from typing import List, Optional, Dict, Any

# 需要让 dev_test 调用上层 client_gRPC 的 env, local_input, grpc_client 等模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.data_provider import DataProvider
from core.decoder import GameDataDecoder


class DummyEnvironment:
    """占位环境类，用于 UI/逻辑验证。"""
    def __init__(self):
        self.board = None


class Controller:
    """游戏控制器：混合后端/Mock数据、游戏运营、回合管理"""

    def __init__(self, mode: str = "manual"):
        self.environment: Optional[Environment] = None
        self.input_manager: Optional[InputMethodManager] = None
        self.game_mode: str = mode
        self.current_round: int = 0
        self.game_data: Optional[Dict[str, Any]] = None

    def load_game_data(self, prefer_backend: bool = True):
        provider = DataProvider()
        raw_data = provider.get_game_data(prefer_backend=prefer_backend)

        if isinstance(raw_data, dict) and "map" not in raw_data:
            self.game_data = GameDataDecoder.decode(raw_data)
        else:
            self.game_data = raw_data

        return self.game_data

    def select_mode(self, mode: str):
        if mode not in ("manual", "half-auto", "auto"):
            raise ValueError("mode must be manual/half-auto/auto")
        self.game_mode = mode

    def create_environment(self) -> DummyEnvironment:
        self.environment = DummyEnvironment()
        return self.environment

    def run_round(self):
        if self.game_data is None:
            raise RuntimeError("game_data not loaded")

        if self.current_round >= len(self.game_data.get("rounds", [])):
            print("回合已结束，当前无更多回合")
            return False

        round_info = self.game_data["rounds"][self.current_round]
        print(f"执行第 {round_info['roundNumber']} 回合，动作数量: {len(round_info['actions'])}")
        self.current_round += 1
        return True

    def run_loop(self):
        print(f"开始执行模式: {self.game_mode}")
        while self.run_round():
            pass


if __name__ == "__main__":
    ctrl = Controller(mode="manual")
    print("尝试优先后端数据加载")
    try:
        game_data = ctrl.load_game_data(prefer_backend=True)
        print("加载游戏数据成功，回合数", len(game_data.get('rounds', [])))
    except Exception as e:
        print("后端加载失败，降级到 mock 数据：", e)
        game_data = ctrl.load_game_data(prefer_backend=False)

    ctrl.run_loop()
