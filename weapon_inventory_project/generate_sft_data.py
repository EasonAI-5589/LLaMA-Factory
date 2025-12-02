#!/usr/bin/env python3
"""
武器库存查询 SFT 数据集生成脚本

功能：
1. 解析 item_name.csv，构建结构化物品数据库
2. 严格区分武器/配件/弹药
3. 按类型生成多样化的问答对
4. 输出 Alpaca 格式的 JSON 文件
"""

import json
import random
import re
from pathlib import Path
from collections import defaultdict
from typing import Optional


# ==================== 配置 ====================

# 武器类型关键词
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

# 配件关键词
ACCESSORY_KEYWORDS = [
    "弹匣", "消音器", "枪口补偿器", "消焰器", "握把", "枪托(",
    "瞄准镜", "托腮板", "子弹袋", "战术枪托", "延长枪管",
    "鸭嘴枪口", "收束器", "激光瞄准器", "箭袋", "枪托(Micro",
    "快速弹匣", "扩容弹匣", "快速扩容弹匣"
]

# 弹药关键词
AMMO_KEYWORDS = ["子弹", "箭矢", "手雷", "燃烧瓶", "烟雾弹", "震爆弹"]

# 品质等级（从高到低）
QUALITY_ORDER = ["轩辕", "黑鹰", "铁爪", "卓越", "精制", "改进", "完好", "修复", "破损"]

# 品质等级分组
QUALITY_TIERS = {
    "顶级": ["轩辕", "黑鹰", "铁爪"],
    "高级": ["卓越"],
    "中级": ["精制", "改进", "完好"],
    "低级": ["修复", "破损"],
}

# 问题模板
CATEGORY_QUERY_TEMPLATES = [
    "武器库里有哪些{category}？",
    "告诉我所有的{category}",
    "库存中有什么{category}",
    "帮我查一下{category}",
    "列出所有{category}",
    "{category}有哪些型号？",
    "查询武器库的{category}",
    "武器库{category}清单",
]

QUALITY_QUERY_TEMPLATES = [
    "列出所有{quality}品质的武器",
    "有哪些{quality}级别的武器？",
    "武器库里{quality}品质的武器有哪些",
    "查询{quality}级武器",
    "告诉我所有{quality}品质的装备",
]

ITEM_INFO_TEMPLATES = [
    "{item}属于什么类型？",
    "{item}是什么武器？",
    "告诉我{item}的信息",
    "{item}的品质是什么？",
    "{item}属于哪个分类？",
]

MODEL_QUERY_TEMPLATES = [
    "武器库里有哪些{model}？",
    "查询所有{model}",
    "{model}有哪些版本？",
    "列出所有{model}",
]

QUALITY_COMPARE_TEMPLATES = [
    "{q1}和{q2}哪个品质更好？",
    "{q1}品质高还是{q2}品质高？",
    "对比{q1}和{q2}的品质",
]

ALL_WEAPONS_TEMPLATES = [
    "查询武器库所有武器",
    "列出完整的武器清单",
    "武器库里有什么武器？",
    "显示所有武器库存",
]


# ==================== 工具函数 ====================

def is_accessory_or_ammo(item_name: str) -> bool:
    """判断是否是配件或弹药"""
    for acc in ACCESSORY_KEYWORDS:
        if acc in item_name:
            return True
    for ammo in AMMO_KEYWORDS:
        if ammo in item_name:
            return True
    if "榴弹" in item_name and "发射器" not in item_name and "炮" not in item_name:
        return True
    if "口径霰弹" in item_name:
        return True
    return False


def get_weapon_category(item_name: str) -> Optional[str]:
    """获取武器所属类别"""
    if is_accessory_or_ammo(item_name):
        return None

    for category, keywords in WEAPON_TYPES.items():
        if any(kw in item_name for kw in keywords):
            return category
    return None


def extract_quality(item_name: str) -> Optional[str]:
    """从物品名称中提取品质"""
    # 匹配括号内的品质，如 M24狙击枪(卓越)
    match = re.search(r'\(([^)]+)\)$', item_name)
    if match:
        quality = match.group(1)
        if quality in QUALITY_ORDER:
            return quality
    return None


def extract_model(item_name: str) -> Optional[str]:
    """从物品名称中提取武器型号"""
    # 移除品质后缀
    name = re.sub(r'\([^)]+\)$', '', item_name).strip()
    # 移除武器类型
    for category in WEAPON_TYPES.keys():
        name = name.replace(category, '')
    # 移除特殊标记
    name = re.sub(r'[·\-].*$', '', name)
    return name.strip() if name.strip() else None


def parse_items(csv_path: str) -> dict:
    """解析物品CSV文件，构建结构化数据库"""
    weapons = defaultdict(list)
    accessories = []
    ammo = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 跳过表头
    for line in lines[1:]:
        item_name = line.strip()
        if not item_name:
            continue

        # 判断类型
        if is_accessory_or_ammo(item_name):
            if any(ammo_kw in item_name for ammo_kw in AMMO_KEYWORDS) or "榴弹" in item_name:
                ammo.append(item_name)
            else:
                accessories.append(item_name)
        else:
            category = get_weapon_category(item_name)
            if category:
                quality = extract_quality(item_name)
                model = extract_model(item_name)
                weapons[category].append({
                    "name": item_name,
                    "model": model,
                    "quality": quality
                })

    return {
        "weapons": dict(weapons),
        "accessories": accessories,
        "ammo": ammo
    }


def get_quality_rank(quality: str) -> int:
    """获取品质排名（数字越小越好）"""
    try:
        return QUALITY_ORDER.index(quality)
    except ValueError:
        return 999


def compare_quality(q1: str, q2: str) -> str:
    """比较两个品质的高低"""
    r1, r2 = get_quality_rank(q1), get_quality_rank(q2)
    if r1 < r2:
        return f"{q1}品质高于{q2}"
    elif r1 > r2:
        return f"{q2}品质高于{q1}"
    else:
        return f"{q1}和{q2}品质相同"


# ==================== 数据生成函数 ====================

def generate_category_queries(weapons: dict, count_per_category: int = 100) -> list:
    """生成分类查询数据"""
    data = []

    for category, weapon_list in weapons.items():
        weapon_names = [w["name"] for w in weapon_list]

        for _ in range(count_per_category):
            # 随机选择一部分武器作为"当前库存"
            sample_size = random.randint(3, min(15, len(weapon_names)))
            sampled = random.sample(weapon_names, sample_size)

            template = random.choice(CATEGORY_QUERY_TEMPLATES)
            question = template.format(category=category)
            answer = f"武器库中的{category}有：" + "、".join(sampled)

            data.append({
                "instruction": "查询武器库存",
                "input": question,
                "output": answer,
                "task_type": "category_query"
            })

    return data


def generate_quality_queries(weapons: dict, count_per_quality: int = 50) -> list:
    """生成品质查询数据"""
    data = []

    # 按品质分组所有武器
    quality_weapons = defaultdict(list)
    for category, weapon_list in weapons.items():
        for weapon in weapon_list:
            if weapon["quality"]:
                quality_weapons[weapon["quality"]].append(weapon["name"])

    for quality in QUALITY_ORDER:
        if quality not in quality_weapons:
            continue

        weapon_names = quality_weapons[quality]

        for _ in range(count_per_quality):
            sample_size = random.randint(3, min(10, len(weapon_names)))
            sampled = random.sample(weapon_names, sample_size)

            template = random.choice(QUALITY_QUERY_TEMPLATES)
            question = template.format(quality=quality)
            answer = f"{quality}品质的武器有：" + "、".join(sampled)

            data.append({
                "instruction": "按品质查询武器",
                "input": question,
                "output": answer,
                "task_type": "quality_query"
            })

    return data


def generate_item_info_queries(weapons: dict, count: int = 500) -> list:
    """生成物品归属查询数据"""
    data = []

    # 收集所有武器
    all_weapons = []
    for category, weapon_list in weapons.items():
        for weapon in weapon_list:
            all_weapons.append({**weapon, "category": category})

    for _ in range(count):
        weapon = random.choice(all_weapons)
        template = random.choice(ITEM_INFO_TEMPLATES)
        question = template.format(item=weapon["name"])

        quality_info = f"，品质为{weapon['quality']}级" if weapon["quality"] else ""
        answer = f"{weapon['name']}属于{weapon['category']}类别{quality_info}。"

        data.append({
            "instruction": "查询物品信息",
            "input": question,
            "output": answer,
            "task_type": "item_info"
        })

    return data


def generate_model_queries(weapons: dict, count: int = 400) -> list:
    """生成同型号查询数据"""
    data = []

    # 按型号分组
    model_weapons = defaultdict(list)
    for category, weapon_list in weapons.items():
        for weapon in weapon_list:
            if weapon["model"]:
                model_weapons[weapon["model"]].append({**weapon, "category": category})

    # 过滤出有多个版本的型号
    multi_version_models = {m: ws for m, ws in model_weapons.items() if len(ws) >= 2}

    if not multi_version_models:
        return data

    models = list(multi_version_models.keys())

    for _ in range(count):
        model = random.choice(models)
        weapon_list = multi_version_models[model]
        category = weapon_list[0]["category"]

        # 随机选择几个版本
        sample_size = min(len(weapon_list), random.randint(2, 6))
        sampled = random.sample(weapon_list, sample_size)
        weapon_names = [w["name"] for w in sampled]

        template = random.choice(MODEL_QUERY_TEMPLATES)
        question = template.format(model=model)
        answer = f"武器库中的{model}{category}有：" + "、".join(weapon_names) + "。"

        data.append({
            "instruction": "查询武器型号",
            "input": question,
            "output": answer,
            "task_type": "model_query"
        })

    return data


def generate_quality_compare_queries(count: int = 150) -> list:
    """生成品质对比数据"""
    data = []
    quality_order_str = " > ".join(["轩辕/黑鹰/铁爪"] + QUALITY_ORDER[3:])

    for _ in range(count):
        # 随机选两个品质
        q1, q2 = random.sample(QUALITY_ORDER, 2)

        template = random.choice(QUALITY_COMPARE_TEMPLATES)
        question = template.format(q1=q1, q2=q2)

        comparison = compare_quality(q1, q2)
        answer = f"{comparison}。品质从高到低依次为：{quality_order_str}。"

        data.append({
            "instruction": "对比武器品质",
            "input": question,
            "output": answer,
            "task_type": "quality_compare"
        })

    return data


def generate_all_weapons_queries(weapons: dict, count: int = 200) -> list:
    """生成综合库存查询数据"""
    data = []

    for _ in range(count):
        template = random.choice(ALL_WEAPONS_TEMPLATES)

        # 为每个类别随机选择一些武器
        output_parts = ["武器库清单如下："]
        for category, weapon_list in weapons.items():
            weapon_names = [w["name"] for w in weapon_list]
            sample_size = random.randint(2, min(5, len(weapon_names)))
            sampled = random.sample(weapon_names, sample_size)
            output_parts.append(f"{category}：" + "、".join(sampled))

        answer = "\n".join(output_parts)

        data.append({
            "instruction": "查询武器库存",
            "input": template,
            "output": answer,
            "task_type": "all_weapons"
        })

    return data


# ==================== 主函数 ====================

def main():
    # 路径配置
    base_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory")
    csv_path = base_path / "item_name.csv"
    output_path = base_path / "data" / "weapon_inventory_sft_v2.json"
    db_path = base_path / "weapon_inventory_project" / "item_database.json"

    print("=" * 50)
    print("武器库存 SFT 数据集生成")
    print("=" * 50)

    # 1. 解析物品数据
    print("\n[1/3] 解析物品数据...")
    item_db = parse_items(csv_path)

    # 保存结构化数据库
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(item_db, f, ensure_ascii=False, indent=2)
    print(f"  结构化数据库已保存: {db_path}")

    # 统计
    weapons = item_db["weapons"]
    total_weapons = sum(len(ws) for ws in weapons.values())
    print(f"  武器总数: {total_weapons}")
    for category, weapon_list in weapons.items():
        print(f"    - {category}: {len(weapon_list)}")
    print(f"  配件数: {len(item_db['accessories'])}")
    print(f"  弹药数: {len(item_db['ammo'])}")

    # 2. 生成训练数据
    print("\n[2/3] 生成训练数据...")
    all_data = []

    # 分类查询
    category_data = generate_category_queries(weapons, count_per_category=100)
    all_data.extend(category_data)
    print(f"  分类查询: {len(category_data)} 条")

    # 品质查询
    quality_data = generate_quality_queries(weapons, count_per_quality=50)
    all_data.extend(quality_data)
    print(f"  品质查询: {len(quality_data)} 条")

    # 物品归属查询
    item_info_data = generate_item_info_queries(weapons, count=500)
    all_data.extend(item_info_data)
    print(f"  物品归属查询: {len(item_info_data)} 条")

    # 型号查询
    model_data = generate_model_queries(weapons, count=400)
    all_data.extend(model_data)
    print(f"  型号查询: {len(model_data)} 条")

    # 品质对比
    compare_data = generate_quality_compare_queries(count=150)
    all_data.extend(compare_data)
    print(f"  品质对比: {len(compare_data)} 条")

    # 综合查询
    all_weapons_data = generate_all_weapons_queries(weapons, count=200)
    all_data.extend(all_weapons_data)
    print(f"  综合查询: {len(all_weapons_data)} 条")

    # 打乱数据
    random.shuffle(all_data)

    # 3. 保存数据
    print("\n[3/3] 保存数据...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"  训练数据已保存: {output_path}")
    print(f"  总数据量: {len(all_data)} 条")

    # 显示示例
    print("\n" + "=" * 50)
    print("数据示例")
    print("=" * 50)
    for i, sample in enumerate(all_data[:5], 1):
        print(f"\n[{i}] {sample['task_type']}")
        print(f"  Q: {sample['input']}")
        print(f"  A: {sample['output'][:100]}...")


if __name__ == "__main__":
    main()
