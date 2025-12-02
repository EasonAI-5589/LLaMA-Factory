#!/usr/bin/env python3
"""
修复武器库存SFT数据集中的问题：
1. 查询武器时不应返回配件
2. 区分武器本体和配件/弹药等
3. 处理 weapon_inventory_all 类型（查询所有武器）
"""

import json
import re
from pathlib import Path


# 武器类型关键词（武器本体）
WEAPON_TYPES = {
    "狙击枪": ["狙击枪"],
    "冲锋枪": ["冲锋枪"],
    "突击步枪": ["突击步枪"],
    "射手步枪": ["射手步枪"],
    "轻机枪": ["轻机枪"],
    "霰弹枪": ["霰弹枪"],
    "手枪": ["手枪"],
    "特殊武器": ["十字弩", "弩", "榴弹发射器", "榴弹炮", "猎弓", "火箭筒", "喷火器"],
}

# 配件关键词（需要排除的）
ACCESSORY_KEYWORDS = [
    "弹匣", "消音器", "枪口补偿器", "消焰器", "握把", "枪托(",
    "瞄准镜", "托腮板", "子弹袋", "战术枪托", "延长枪管",
    "鸭嘴枪口", "收束器", "激光瞄准器", "箭袋", "枪托(Micro",
    "快速弹匣", "扩容弹匣", "快速扩容弹匣"
]

# 弹药/投掷物关键词（注意：不能包含会匹配到武器名的词）
AMMO_KEYWORDS = ["子弹", "箭矢", "手雷", "燃烧瓶", "烟雾弹", "震爆弹"]


def is_accessory_or_ammo(item_name: str) -> bool:
    """判断是否是配件或弹药"""
    # 检查是否是配件
    for acc in ACCESSORY_KEYWORDS:
        if acc in item_name:
            return True

    # 检查是否是弹药
    for ammo in AMMO_KEYWORDS:
        if ammo in item_name:
            return True

    # 特殊情况：榴弹（如果不包含"发射器"/"炮"则是弹药）
    if "榴弹" in item_name and "发射器" not in item_name and "炮" not in item_name:
        return True

    # 特殊情况：口径霰弹（弹药）vs 霰弹枪（武器）
    if "口径霰弹" in item_name:
        return True

    return False


def is_weapon_body(item_name: str, weapon_type: str = None) -> bool:
    """
    判断物品是否是武器本体（而非配件）

    Args:
        item_name: 物品名称
        weapon_type: 武器类型（如 "冲锋枪", "狙击枪"），可选

    Returns:
        True 如果是武器本体，False 如果是配件
    """
    # 首先检查是否是配件或弹药 - 这个检查必须优先
    if is_accessory_or_ammo(item_name):
        return False

    # 如果没有指定武器类型，检查是否属于任何武器类型
    if weapon_type is None:
        for wtype, keywords in WEAPON_TYPES.items():
            if any(kw in item_name for kw in keywords):
                return True
        return False

    # 对于特殊武器，检查特定关键词
    if weapon_type == "特殊武器":
        special_keywords = WEAPON_TYPES["特殊武器"]
        return any(kw in item_name for kw in special_keywords)

    # 对于其他武器，必须包含武器类型关键词
    type_keywords = WEAPON_TYPES.get(weapon_type, [weapon_type])
    return any(kw in item_name for kw in type_keywords)


def get_weapon_type_of_item(item_name: str) -> str:
    """获取物品所属的武器类型"""
    if is_accessory_or_ammo(item_name):
        return None

    for wtype, keywords in WEAPON_TYPES.items():
        if any(kw in item_name for kw in keywords):
            return wtype
    return None


def extract_weapons_from_output(output: str) -> list:
    """从输出文本中提取武器列表"""
    # 移除前缀
    prefixes = ["武器库中的", "武器库清单：", "有：", "清单："]
    text = output
    for prefix in prefixes:
        if prefix in text:
            text = text.split(prefix, 1)[-1]

    # 分割武器
    weapons = []
    # 处理 、 和 ， 分隔
    items = re.split(r'[、，,]', text)
    for item in items:
        item = item.strip().strip('"').strip()
        if item:
            weapons.append(item)
    return weapons


def filter_weapons(weapons: list, weapon_type: str) -> list:
    """过滤出真正的武器本体"""
    return [w for w in weapons if is_weapon_body(w, weapon_type)]


def get_weapon_type_from_input(input_text: str) -> str:
    """从查询输入中识别武器类型"""
    for wtype in WEAPON_TYPES.keys():
        if wtype in input_text:
            return wtype
    return None


def fix_single_type_query(entry: dict) -> dict:
    """修复单一武器类型查询"""
    input_text = entry.get("input", "")
    output = entry.get("output", "")

    # 识别查询的武器类型
    weapon_type = get_weapon_type_from_input(input_text)

    if weapon_type is None:
        return entry

    # 提取武器列表
    weapons = extract_weapons_from_output(output)

    # 过滤出真正的武器
    filtered_weapons = filter_weapons(weapons, weapon_type)

    if not filtered_weapons:
        return entry

    # 重建输出
    new_output = f"武器库中的{weapon_type}有：" + "、".join(filtered_weapons)

    return {
        **entry,
        "output": new_output,
        "fixed": True
    }


def parse_items_with_quotes(items_str: str) -> list:
    """解析物品列表，正确处理引号内的逗号"""
    items = []
    current = ""
    in_quotes = False

    for char in items_str:
        if char == '"':
            in_quotes = not in_quotes
            current += char
        elif char in '、，,' and not in_quotes:
            if current.strip():
                items.append(current.strip().strip('"'))
            current = ""
        else:
            current += char

    if current.strip():
        items.append(current.strip().strip('"'))

    return items


def fix_all_weapons_query(entry: dict) -> dict:
    """修复查询所有武器的数据"""
    output = entry.get("output", "")

    # 解析分类结构
    # 格式: 武器库清单如下：\n冲锋枪：xxx、xxx；\n射手步枪：xxx、xxx；...
    if "武器库清单如下" not in output:
        return entry

    # 按类别分割
    categories = {}
    category_order = []

    # 提取各类别
    lines = output.split("\n")
    for line in lines:
        if "：" in line and "；" in line:
            # 格式: 冲锋枪：xxx、xxx；
            parts = line.split("：", 1)
            if len(parts) == 2:
                category = parts[0].strip()
                items_str = parts[1].rstrip("；").strip()
                items = parse_items_with_quotes(items_str)
                categories[category] = items
                category_order.append(category)
        elif "：" in line:
            # 最后一个类别可能没有分号
            parts = line.split("：", 1)
            if len(parts) == 2:
                category = parts[0].strip()
                items_str = parts[1].strip()
                items = parse_items_with_quotes(items_str)
                categories[category] = items
                if category not in category_order:
                    category_order.append(category)

    if not categories:
        return entry

    # 过滤每个类别中的配件
    filtered_categories = {}
    has_changes = False

    for category, items in categories.items():
        # 根据类别名确定武器类型
        weapon_type = None
        for wtype in WEAPON_TYPES.keys():
            if wtype in category:
                weapon_type = wtype
                break

        if weapon_type:
            filtered_items = [item for item in items if is_weapon_body(item, weapon_type)]
        else:
            # 未知类别，过滤掉明显的配件
            filtered_items = [item for item in items if not is_accessory_or_ammo(item)]

        if len(filtered_items) != len(items):
            has_changes = True

        if filtered_items:
            filtered_categories[category] = filtered_items

    if not has_changes:
        return entry

    # 重建输出
    output_parts = ["武器库清单如下："]
    for category in category_order:
        if category in filtered_categories and filtered_categories[category]:
            items_str = "、".join(filtered_categories[category])
            output_parts.append(f"{category}：{items_str}")

    new_output = "\n".join(output_parts)

    return {
        **entry,
        "output": new_output,
        "fixed": True
    }


def fix_entry(entry: dict) -> dict:
    """修复单条数据"""
    task_type = entry.get("task_type", "")

    if task_type == "weapon_inventory_query":
        return fix_single_type_query(entry)
    elif task_type == "weapon_inventory_all":
        return fix_all_weapons_query(entry)
    else:
        return entry


def analyze_dataset(data: list) -> dict:
    """分析数据集问题"""
    stats = {
        "total": len(data),
        "weapon_queries": 0,
        "weapon_all_queries": 0,
        "entries_with_accessories": 0,
        "accessory_examples": []
    }

    for entry in data:
        task_type = entry.get("task_type", "")
        output = entry.get("output", "")

        if task_type == "weapon_inventory_query":
            stats["weapon_queries"] += 1
        elif task_type == "weapon_inventory_all":
            stats["weapon_all_queries"] += 1

        if task_type in ["weapon_inventory_query", "weapon_inventory_all"]:
            for acc in ACCESSORY_KEYWORDS + AMMO_KEYWORDS:
                if acc in output:
                    stats["entries_with_accessories"] += 1
                    if len(stats["accessory_examples"]) < 5:
                        stats["accessory_examples"].append({
                            "input": entry.get("input", ""),
                            "output": output[:300] + "..." if len(output) > 300 else output,
                            "task_type": task_type
                        })
                    break

    return stats


def main():
    # 读取原始数据
    input_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/weapon_inventory_sft_20251201_153858.json")
    output_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/data/weapon_inventory_sft_fixed.json")

    print(f"读取数据: {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 分析问题
    print("\n=== 数据分析 ===")
    stats = analyze_dataset(data)
    print(f"总条目数: {stats['total']}")
    print(f"单类武器查询条目: {stats['weapon_queries']}")
    print(f"所有武器查询条目: {stats['weapon_all_queries']}")
    print(f"包含配件/弹药的条目: {stats['entries_with_accessories']}")

    if stats["accessory_examples"]:
        print("\n问题示例:")
        for i, ex in enumerate(stats["accessory_examples"], 1):
            print(f"\n{i}. [{ex['task_type']}] 输入: {ex['input']}")
            print(f"   输出: {ex['output']}")

    # 修复数据
    print("\n=== 开始修复 ===")
    fixed_count = 0
    fixed_data = []

    for entry in data:
        fixed_entry = fix_entry(entry)
        if fixed_entry.get("fixed"):
            fixed_count += 1
            del fixed_entry["fixed"]
        fixed_data.append(fixed_entry)

    print(f"修复条目数: {fixed_count}")

    # 保存修复后的数据
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(fixed_data, f, ensure_ascii=False, indent=2)

    print(f"\n修复后的数据已保存到: {output_path}")

    # 同时更新 data 目录下的文件
    data_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/data/weapon_inventory_sft.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(fixed_data, f, ensure_ascii=False, indent=2)
    print(f"已更新: {data_path}")

    # 显示修复示例
    print("\n=== 修复示例 ===")
    shown_single = 0
    shown_all = 0

    for orig, fixed in zip(data, fixed_data):
        if orig["output"] != fixed["output"]:
            task_type = orig.get("task_type", "")

            if task_type == "weapon_inventory_query" and shown_single < 2:
                shown_single += 1
                print(f"\n[单类查询] 输入: {orig['input']}")
                print(f"  修复前: {orig['output'][:150]}...")
                print(f"  修复后: {fixed['output'][:150]}...")

            elif task_type == "weapon_inventory_all" and shown_all < 2:
                shown_all += 1
                print(f"\n[所有武器查询] 输入: {orig['input']}")
                print(f"  修复前: {orig['output'][:300]}...")
                print(f"  修复后: {fixed['output'][:300]}...")

            if shown_single >= 2 and shown_all >= 2:
                break

    # 验证修复效果
    print("\n=== 验证修复效果 ===")
    remaining_issues = 0
    for entry in fixed_data:
        task_type = entry.get("task_type", "")
        if task_type in ["weapon_inventory_query", "weapon_inventory_all"]:
            output = entry.get("output", "")
            for acc in ACCESSORY_KEYWORDS:
                if acc in output:
                    remaining_issues += 1
                    break

    print(f"修复后仍包含配件的条目: {remaining_issues}")


if __name__ == "__main__":
    main()
