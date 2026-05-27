# 规则执行说明

本项目从 v4 开始采用“模块化 Markdown 总设定模式”。

## 规则来源

```text
data/system_prompt.md          # 入口说明与最高原则
data/modules/*.md              # 具体系统模块
```

`core/prompts.py` 会在每回合自动读取上述 Markdown 文件，并按文件名顺序拼接成完整 system prompt。

## 为什么这样做

原 PDF 只是最初承载设定的格式。程序真正执行的是 Markdown 规则文本。拆成模块后，可以更清楚地维护：健康、资源、粉圈、公关、恋爱、公司、市场、续约等系统。

## 如何确保规则被执行

1. 每回合读取所有 Markdown 模块。
2. 每回合传入完整 GameState。
3. 每回合传入 Python 预计算 base_diff。
4. 每回合传入阈值预警。
5. DeepSeek 必须返回固定 JSON。
6. Python 校验并应用 diff，不让模型随意改状态。
7. SQLite 保存每回合结果、长期 flag 和存档状态。

规则不是靠 PDF 格式保证的，而是靠“Markdown 模块 + GameState + Python diff 校验 + SQLite 存档”保证的。


## 模型路由

本版本支持 DeepSeek Flash / Pro / 自动路由。模型只决定生成质量和调用成本，不决定游戏状态。GameState、diff 校验、长期 flag 与 SQLite 存档仍由 Python 控制。
