# 项目入口文件
# 负责整合各模块，启动测试界面

import sys
import os
from typing import Optional

# 添加当前目录到路径，便于导入模块
sys.path.append(os.path.dirname(__file__))

from logic.controller import Controller


def main(mode: str = "manual", prefer_backend: bool = True):
    controller = Controller(mode=mode)

    try:
        game_data = controller.load_game_data(prefer_backend=prefer_backend)
        print(f"已加载游戏数据，回合数 = {len(game_data.get('rounds', []))}")
    except Exception as e:
        print(f"加载游戏数据失败：{e}")
        return

    controller.run_loop()


if __name__ == "__main__":
    # 1. 全局手动对战: mode=manual
    # 2. 半自动（单人操作/机器对手）: mode=half-auto
    main(mode="manual", prefer_backend=True)
