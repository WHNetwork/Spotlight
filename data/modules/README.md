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
- 公司生成 / 公司规模 / 公司风格：改 `03_company_generation.md`
- 健康伤病：改 `04_health_system.md`
- 回归风格 / 资源分配：改 `05_resource_and_comeback.md`
- 队内关系 / 镜头前和谐：改 `06_team_and_lens_harmony.md`
- 练习生日常 / 时间格 / 排挤霸凌：改 `07_trainee_daily_bullying.md`
- 粉圈 / 公关：改 `07_fandom_pr_system.md`
- 恋爱 / 私生：改 `08_love_and_safety.md`
- 市场成绩 / 打歌一位 / 颁奖：改 `09_market_score_system.md`
- 队友与重要 NPC 生成：改 `10_teammate_npc_generation.md`
- 职业分岔 / solo / 演员 / 维权退出：改 `13_career_branch_system.md`
- 品牌商业 / 金钱 / 合约续约：改 `14_brand_money_contract.md`
