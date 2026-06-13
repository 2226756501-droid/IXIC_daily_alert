# -*- coding: utf-8 -*-
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

doc.add_heading("类型提示(Type Hints)与测试(Testing)入门指南", 0)

doc.add_paragraph("本文档介绍 Python 项目中两个重要的工程实践: 类型提示和测试。本项目的所有代码已加上类型提示和测试，本文帮助你理解它们是什么、为什么重要。")

# ==================== 第一部分 ====================
doc.add_heading("一、类型提示 (Type Hints)", 1)

doc.add_heading("1.1 什么是类型提示", 2)
doc.add_paragraph(
    "Python 是动态类型语言，变量的类型在运行时才确定。类型提示就是在函数参数和返回值上标注预期类型，"
    "它不会影响代码运行，但能让代码更清晰，让编辑器(如 VSCode)能自动补全和检查错误。"
)

doc.add_heading("1.2 为什么需要类型提示", 2)
p = doc.add_paragraph()
p.add_run("没有类型提示的问题:").bold = True
doc.add_paragraph("别人调用你的函数时，只能靠猜参数传什么类型", style="List Bullet")
doc.add_paragraph("编辑器不会自动补全，也没有错误提示", style="List Bullet")
doc.add_paragraph("自己写的代码，过一个月回来也忘了参数该传什么", style="List Bullet")

p2 = doc.add_paragraph()
p2.add_run("有类型提示的好处:").bold = True
doc.add_paragraph("函数签名自文档化，一看就知道怎么用", style="List Bullet")
doc.add_paragraph("编辑器悬停显示类型，自动补全参数", style="List Bullet")
doc.add_paragraph("配合 mypy/pyright 能静态检查类型错误", style="List Bullet")

doc.add_heading("1.3 具体例子", 2)
doc.add_paragraph("本项目的 analyzer.py:")

doc.add_paragraph("改之前(无类型提示):")
p = doc.add_paragraph()
p.style = doc.styles['Normal']
run = p.add_run("def calc_z_score(pcts):\n    window = pcts[:-1]\n    ...\n    return ...")
run.font.name = 'Courier New'
run.font.size = Pt(9)

doc.add_paragraph("改之后(加类型提示):")
p = doc.add_paragraph()
run = p.add_run("def calc_z_score(pcts: list[float]) -> float:\n    window = pcts[:-1]\n    ...\n    return ...")
run.font.name = 'Courier New'
run.font.size = Pt(9)

doc.add_paragraph("变化说明:")
doc.add_paragraph("pcts: list[float] -- 参数 pcts 应该传入一个浮点数列表", style="List Bullet")
doc.add_paragraph("-> float -- 函数返回一个浮点数", style="List Bullet")

doc.add_paragraph("再看一个更复杂的例子:")
p = doc.add_paragraph()
run = p.add_run("def record_abnormal(memory: dict, z: float, drops: int, close: float, pct: float, date: str) -> dict:")
run.font.name = 'Courier New'
run.font.size = Pt(9)

doc.add_heading("1.4 常见类型写法", 2)
doc.add_paragraph("int -- 整数", style="List Bullet")
doc.add_paragraph("float -- 浮点数", style="List Bullet")
doc.add_paragraph("str -- 字符串", style="List Bullet")
doc.add_paragraph("bool -- 布尔值(True/False)", style="List Bullet")
doc.add_paragraph("list[float] -- 浮点数列表", style="List Bullet")
doc.add_paragraph("dict[str, Any] -- 键为字符串的字典", style="List Bullet")
doc.add_paragraph("tuple[str, int] -- 元组", style="List Bullet")
doc.add_paragraph("Optional[str] -- 可能是字符串或 None", style="List Bullet")

doc.add_paragraph("注意: 类型提示只起提示作用，传入错误类型不会报错，需要配合 mypy 等工具才能真正检查。")

# ==================== 第二部分 ====================
doc.add_heading("二、测试 (Testing)", 1)

doc.add_heading("2.1 什么是测试", 2)
doc.add_paragraph(
    "测试就是写代码来验证你的代码是否正确。核心思想是: 给函数传入你事先知道答案的输入，然后用 assert 检查输出是否匹配预期。"
)

doc.add_heading("2.2 为什么需要测试", 2)
p3 = doc.add_paragraph()
p3.add_run("没有测试的风险:").bold = True
doc.add_paragraph("改了代码不知道有没有改坏，只能凭感觉", style="List Bullet")
doc.add_paragraph("边界情况(空列表、只有一个元素等)没人验证", style="List Bullet")
doc.add_paragraph("不敢重构，一改就怕崩", style="List Bullet")

p4 = doc.add_paragraph()
p4.add_run("有测试的好处:").bold = True
doc.add_paragraph("改完代码跑一下 pytest，立刻知道有没有改坏", style="List Bullet")
doc.add_paragraph("边界情况一次测好，以后永远自动验证", style="List Bullet")
doc.add_paragraph("敢于重构和优化，因为有测试兜底", style="List Bullet")

doc.add_heading("2.3 assert 是什么", 2)
doc.add_paragraph("assert 是 Python 的关键字，中文叫断言，意思是你断定某个条件为真，如果为假程序就崩溃报错。")
doc.add_paragraph("例子:")
p = doc.add_paragraph()
run = p.add_run(
    "assert 1 + 1 == 2   # 对，没事\n"
    "assert 1 + 1 == 3   # 错，报 AssertionError"
)
run.font.name = 'Courier New'
run.font.size = Pt(9)

doc.add_paragraph("测试就是用 assert 来检查函数返回值是否等于你预期的结果。")

doc.add_heading("2.4 测试例子", 2)
doc.add_paragraph("假设你有这个函数(来自 analyzer.py):")

p = doc.add_paragraph()
run = p.add_run(
    "def calc_z_score(pcts: list[float]) -> float:\n"
    "    window = pcts[:-1]\n"
    "    if len(window) < 2:\n"
    "        return 0.0\n"
    "    mu = sum(window) / len(window)\n"
    "    var = sum((x - mu) ** 2 for x in window) / (len(window) - 1)\n"
    "    std = var ** 0.5\n"
    "    return 0.0 if std == 0 else (pcts[-1] - mu) / std"
)
run.font.name = 'Courier New'
run.font.size = Pt(9)

doc.add_paragraph("你可以写测试来验证几种情况:")

p = doc.add_paragraph()
run = p.add_run(
    "# 测试1: 所有数字一样 -> Z=0\n"
    "assert calc_z_score([1.0, 1.0, 1.0, 1.0, 1.0]) == 0.0\n\n"
    "# 测试2: 最后一天大涨 -> Z为正\n"
    "assert calc_z_score([0.0, 0.0, 0.0, 0.0, 2.0]) > 0\n\n"
    "# 测试3: 只有1个数据 -> 返回0\n"
    "assert calc_z_score([42.0]) == 0.0\n\n"
    "# 测试4: 空列表 -> 返回0\n"
    "assert calc_z_score([]) == 0.0"
)
run.font.name = 'Courier New'
run.font.size = Pt(9)

doc.add_paragraph("注意: 测试使用的是同一个函数，没有重新实现算法。只是用你凭常识就能判断的简单输入来验证。")

doc.add_heading("2.5 测试组织", 2)
doc.add_paragraph("测试文件通常放在 tests/ 目录下，命名规则为 test_xxx.py。使用 pytest 框架运行。")
doc.add_paragraph("运行方式: pytest tests/")
doc.add_paragraph("输出示例: 8 passed in 0.32s")

doc.add_heading("2.6 测试注意事项", 2)
doc.add_paragraph("测试不是重新写算法，只用你知道答案的简单输入", style="List Bullet")
doc.add_paragraph("重点关注边界条件: 空列表、None、0、负数等", style="List Bullet")
doc.add_paragraph("测试应该独立，一个失败不影响其他", style="List Bullet")
doc.add_paragraph("改了代码后先跑测试，再提交", style="List Bullet")

# 结尾
doc.add_heading("三、本项目的改动", 1)
doc.add_paragraph("已为以下文件添加了完整的类型提示:")
doc.add_paragraph("modules/analyzer.py", style="List Bullet")
doc.add_paragraph("modules/data_fetcher.py", style="List Bullet")
doc.add_paragraph("modules/visualizer.py", style="List Bullet")
doc.add_paragraph("modules/config.py", style="List Bullet")
doc.add_paragraph("modules/drawdown.py", style="List Bullet")
doc.add_paragraph("modules/holidays.py", style="List Bullet")
doc.add_paragraph("modules/news_fetcher.py", style="List Bullet")
doc.add_paragraph("nasdaq.py", style="List Bullet")
doc.add_paragraph("app.py", style="List Bullet")
doc.add_paragraph("adjust_threshold.py", style="List Bullet")

doc.add_paragraph("已创建以下测试文件:")
doc.add_paragraph("tests/test_analyzer.py -- 测试 analyzer 模块", style="List Bullet")
doc.add_paragraph("tests/test_holidays.py -- 测试 holidays 模块", style="List Bullet")
doc.add_paragraph("tests/test_drawdown.py -- 测试 drawdown 模块", style="List Bullet")

doc.add_paragraph("运行方式(项目根目录):")
p = doc.add_paragraph()
run = p.add_run("D:\\ixic\\.venv\\Scripts\\python.exe -m pytest tests\\ -v")
run.font.name = 'Courier New'
run.font.size = Pt(9)

doc.save("D:\\ixic\\docs\\类型提示与测试入门指南.docx")
print("Word document generated successfully")
