"""Data loading & mode selection services.

职责：
- “模式选择”（runtime_custom/runtime_profession/mock）相关弹窗
- mock 数据集选择弹窗
- 启动时引导选择数据源并加载
- 按当前选择加载对局数据（含清理 UI 状态、初始化 runtime/mock）

约束：不改变 UX，仅做代码搬家与 main_ui 薄委托。
"""
