# 星光练习室 · Phase 2.6 生命周期 / 成长节奏版

这版新增底层长期模拟规则，解决三个问题：

1. 练习生阶段与爱豆阶段日程结构不同。
2. 训练不再每回合直接让能力 +1，而是先进入隐藏经验条。
3. 出道和结局不再由 AI 随口决定，而是由 Python 的阈值 + 概率窗口触发。
4. 少女心事不再展示在 UI 面板中，但仍作为隐藏系统影响事件与叙事。

## 新增模块

```text
core/schedule_system.py
core/progression_system.py
core/skill_decay_system.py
core/debut_system.py
core/ending_system.py
data/modules/12_schedule_progression_debut_ending.md
```

## 核心规则

练习生阶段以训练、学校、考核和公司观察为主。  
爱豆阶段以回归、打歌、综艺、粉丝营业、巡演和公关为主，同时需要维持训练。

能力成长改为经验制：

```text
0—20：每 +1 需要 6 xp
21—40：每 +1 需要 10 xp
41—60：每 +1 需要 16 xp
61—80：每 +1 需要 24 xp
81—100：每 +1 需要 36 xp
```

长期不练习先掉手感，再影响正式属性。  
出道与结局使用窗口机制：达到门槛后打开候选窗口，再由系统概率决定结果。

## 测试

```bash
python test_phase2_6_lifecycle_growth.py
```
