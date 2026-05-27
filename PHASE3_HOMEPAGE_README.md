# Phase 3 Homepage UI

已将 App 名称改为《星光练习室》，并完成主页视觉重制。

新增资源：
- assets/backgrounds/home_bg.png：浅色梦幻练习室主页背景
- assets/icons/*.png：主页与系统图标
- assets/icons_svg/*.svg：图标 SVG 备份

主页特点：
- 白色为基础色
- 浅藕荷、玉色、胭脂粉、黛蓝作为辅助色
- 玻璃拟态卡片
- 中央标题 + 四个主菜单按钮
- 顶部快捷入口
- 左上角 profile card
- 左下角星光日报
- 右下角文案区

运行：
```bash
python app.py
```


## 兼容修复

已将 Flet 0.85 下不兼容的 `ft.border.all(...)` 改为 `ft.Border.all(...)`，将 `ft.alignment.center` 改为 `ft.Alignment.CENTER`，入口改为 `ft.run(...)`。
