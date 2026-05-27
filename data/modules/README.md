# data/modules 说明

这里存放《KPOP 女团爱豆模拟器》的模块化规则。

程序会在每回合自动读取本目录下所有 `.md` 文件，并按文件名排序拼接到系统提示词中。

命名建议：

```text
00_core_rules.md
01_output_contract.md
02_state_and_diff.md
...
```

新增规则时，直接新建 `.md` 文件即可。不要把所有内容塞回 `data/system_prompt.md`。

修改建议：

- 文风要求：改 `00_core_rules.md`
- JSON 输出格式：改 `01_output_contract.md`
- 状态表 / diff / 阈值：改 `02_state_and_diff.md`
- 随机事件 / 延迟后果：改 `03_event_engine.md`
- 健康伤病：改 `04_health_system.md`
- 回归风格 / 资源分配：改 `05_resource_and_comeback.md`
- 队内关系 / 镜头前和谐：改 `06_team_and_lens_harmony.md`
- 粉圈 / 公关：改 `07_fandom_pr_system.md`
- 恋爱 / 私生：改 `08_love_and_safety.md`
