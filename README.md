# KPOP 女团爱豆模拟器 · Phase 2.5.5 No Mock

这版移除了 Mock 引擎。正式回合只通过 DeepSeek API 生成剧情。

## 核心变化

- 删除 `MockProvider`
- 删除 `TurnEngine(use_mock=...)`
- 删除设置页的“使用 Mock 模式”
- 删除界面中的 Mock 调用提示
- 角色创建仍然是本地逻辑，不调用大模型
- 回合推进必须调用 DeepSeek
- 如果 DeepSeek API 调用失败，状态不会推进、存档不会写入、时间不会被错误消耗

## 运行

```bash
conda activate kpop_sim
python app.py
```

## 设置 DeepSeek

在设置页填写：

```text
DeepSeek API Key
Base URL: https://api.deepseek.com
模型策略：auto / flash / pro / custom
Flash Model
Pro Model
Custom Model
```

## 测试

离线全系统测试：

```bash
python test_phase2_5_5_no_mock_offline.py
```

可选 DeepSeek API 集成测试：

```bash
python test_deepseek_integration_optional.py
```

如果没有 API Key，集成测试会跳过真实调用。
