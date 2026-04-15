# THUAI9-Test-Viz
我们的测试开发路径在THUAI9-Test-Viz\THUAI9-Backend-master\client\client_gRPC\dev_test

目前运行方式是在对应环境下直接运行THUAI9-Backend-master\client\client_gRPC\dev_test\ui\main_ui.py
而main.py只能打开终端界面，后续会将main_ui.py和main.py整合到一起，作为项目入口，方便后续开发和测试

简要文件框架

client_gRPC/dev_test/           # 《开发测试》主文件夹

    ├── data/           # 存放测试用的log、proto等数据文件
    ├── core/           # 数据解析与事件驱动核心代码
    │   ├── decoder.py   # 解析log、proto等数据
    │   ├── events.py   # 事件驱动与接口定义
    ├── ui/             # Tkinter可视化界面代码
    │   ├── main_ui.py  # 主界面入口（目前主要逻辑写在此）
    │   ├── components.py  # 自定义控件（如棋盘、角色等）
    ├── logic/          # 交互逻辑（回合切换、暂停等）
    │   ├── controller.py # 控制回合、暂停、步进等
    │   ├── test_mock_gameplay.py    # 测试端独立写的玩法规则（如濒死）
    ├── proto/          # 存放proto文件
    ├── tests/          # 功能测试用例
    │   ├── test_cases.py
    ├── utils/          # 工具函数（如类型转换、辅助方法）
    │   ├── converter.py
    ├── README.md       # 项目说明与开发分工
    └── main.py         # 项目入口，整合各模块


受限于开发时间，目前项目主要由AI编程实现，项目暂时比较臃肿，正在集中进行重构，逐步优化代码结构。