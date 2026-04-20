"""Action services package.

职责：处理 UI 中“行动提交/预览”相关的纯业务逻辑（move/attack/spell），供 main_ui 薄委托调用。
边界：不负责 Tk 组件装配，不持有 MainUI 状态；需要的上下文由调用方传入。
"""
