# 01 输出契约

只返回 JSON，不得在 JSON 外写任何文字。

{
  "narrative": "本回合正文剧情",
  "npc_reactions": [{"name": "NPC 名称", "role": "NPC 身份，可省略", "age": 18, "reaction": "NPC 反应"}],
  "choices": [
    {"id": "A", "text": "选项 A"},
    {"id": "B", "text": "选项 B"},
    {"id": "C", "text": "选项 C"},
    {"id": "D", "text": "选项 D"},
    {"id": "E", "text": "自定义行动"}
  ],
  "suggested_diff": {"身体状态.体力": -3},
  "new_flags": [],
  "resolved_flags": [],
  "public_summary": "一句话总结",
  "private_notes": "隐藏记录"
}

要求：
- choices 至少 4 个，最后一个允许自定义。
- suggested_diff 必须使用“分类.变量名”格式。
- npc_reactions 中出现明确新人物时，应尽量提供 role；后端会用它建立 NPC 与关系档案。
- Python 后端负责公司、时间格、关系、市场成绩、职业分岔、品牌合同等系统结算；模型不得直接宣布这些判定型结果必然成功。
- 不要输出 Markdown 代码块。
