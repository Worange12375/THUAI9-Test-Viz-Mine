# THUAI9-Test-Viz
我们的测试开发路径在THUAI9-Test-Viz\THUAI9-Backend-master\client\client_gRPC\dev_test

大家辛苦，注意注释与沟通！

简要文件框架

client_gRPC/dev_test/           # 《开发测试》主文件夹

    ├── data/           # 存放测试用的log、proto等数据文件
    ├── core/           # 数据解析与事件驱动核心代码
    │   ├── decoder.py   # 解析log、proto等数据
    │   ├── events.py   # 事件驱动与接口定义
    ├── ui/             # Tkinter可视化界面代码
    │   ├── main_ui.py  # 主界面入口
    │   ├── components.py  # 自定义控件（如棋盘、角色等）
    ├── logic/          # 交互逻辑（回合切换、暂停等）
    │   ├── controller.py # 控制回合、暂停、步进等
    ├── tests/          # 功能测试用例
    │   ├── test_cases.py
    ├── utils/          # 工具函数（如类型转换、辅助方法）
    │   ├── converter.py
    ├── README.md       # 项目说明与开发分工
    └── main.py         # 项目入口，整合各模块


