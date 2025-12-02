#!/usr/bin/env python3
"""
武器库存SFT数据集生成脚本 v5
核心改进：
1. 移除所有多答案问题（列举类）
2. instruction 设为空，input 包含完整问题
3. 每个问题只有一个确定性答案
4. 统一回答格式
"""

import json
import random
from pathlib import Path
from collections import defaultdict

# 品质等级排序（从高到低）
QUALITY_ORDER = ["轩辕", "黑鹰", "铁爪", "卓越", "精制", "改进", "完好", "修复", "破损"]

# 防具品质排序（从高到低，仅4-7级有）
ARMOR_QUALITY_ORDER = ["轩辕", "黑鹰", "铁爪"]

# 防具等级
ARMOR_LEVELS = [1, 2, 3, 4, 5, 6, 7]

# 武器类型定义
WEAPON_TYPES = {
    "狙击枪": ["狙击枪"],
    "冲锋枪": ["冲锋枪"],
    "突击步枪": ["突击步枪"],
    "射手步枪": ["射手步枪"],
    "轻机枪": ["轻机枪"],
    "霰弹枪": ["霰弹枪"],
    "手枪": ["手枪"],
    "特殊武器": ["十字弩", "弩", "榴弹发射器", "火箭筒", "喷火器", "猎弓"],
}

ALL_WEAPON_TYPES = list(WEAPON_TYPES.keys())

# 配件关键词
ACCESSORY_KEYWORDS = [
    "弹匣", "消音器", "枪口补偿器", "消焰器", "握把", "枪托(",
    "瞄准镜", "托腮板", "子弹袋", "战术枪托", "延长枪管",
    "鸭嘴枪口", "收束器", "激光瞄准器", "箭袋", "枪托(Micro",
]

# 弹药关键词
AMMO_KEYWORDS = ["子弹", "箭矢", "手雷", "燃烧瓶", "烟雾弹", "震爆弹"]


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


def get_weapon_type(item_name: str) -> str:
    """获取武器类型"""
    if is_accessory_or_ammo(item_name):
        return None
    for wtype, keywords in WEAPON_TYPES.items():
        if any(kw in item_name for kw in keywords):
            return wtype
    return None


def extract_quality(item_name: str) -> str:
    """提取品质"""
    for quality in QUALITY_ORDER:
        if f"({quality})" in item_name:
            return quality
    return None


def extract_model(item_name: str) -> str:
    """提取武器型号"""
    name = item_name
    for quality in QUALITY_ORDER:
        name = name.replace(f"({quality})", "")
    for wtype in ["狙击枪", "冲锋枪", "突击步枪", "射手步枪", "轻机枪", "霰弹枪", "手枪"]:
        name = name.replace(wtype, "")
    return name.strip()


def parse_weapons_from_csv(csv_path: str) -> dict:
    """解析CSV文件，返回结构化的武器数据"""
    weapons_by_type = defaultdict(list)
    weapons_by_quality = defaultdict(list)
    weapons_by_model = defaultdict(list)
    weapons_by_type_quality = defaultdict(list)
    all_weapons = []

    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            item_name = line.strip()
            if not item_name:
                continue

            weapon_type = get_weapon_type(item_name)
            if weapon_type is None:
                continue

            quality = extract_quality(item_name)
            model = extract_model(item_name)

            weapon_info = {
                "name": item_name,
                "type": weapon_type,
                "quality": quality,
                "model": model
            }

            all_weapons.append(weapon_info)
            weapons_by_type[weapon_type].append(weapon_info)
            if quality:
                weapons_by_quality[quality].append(weapon_info)
                weapons_by_type_quality[(weapon_type, quality)].append(weapon_info)
            if model:
                weapons_by_model[model].append(weapon_info)

    return {
        "all": all_weapons,
        "by_type": dict(weapons_by_type),
        "by_quality": dict(weapons_by_quality),
        "by_model": dict(weapons_by_model),
        "by_type_quality": dict(weapons_by_type_quality)
    }


# ============ 武器问答生成（确定性答案） ============

def generate_single_weapon_qa(weapon: dict) -> list:
    """为单个武器生成问答对 - 每个问题只有一个固定答案"""
    name = weapon["name"]
    wtype = weapon["type"]
    quality = weapon["quality"]

    qa_pairs = []

    # 品质查询（固定答案格式）
    if quality:
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是什么品质？",
            "output": f"{name}是{quality}品质。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}的品质是什么？",
            "output": f"{name}的品质是{quality}。"
        })

    # 类型查询（固定答案格式）
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}属于什么类型？",
        "output": f"{name}属于{wtype}。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是什么类型的武器？",
        "output": f"{name}是{wtype}。"
    })
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是哪种武器？",
        "output": f"{name}是{wtype}。"
    })

    # 综合查询（类型+品质）
    if quality:
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}的信息",
            "output": f"{name}是{quality}品质的{wtype}。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"介绍一下{name}",
            "output": f"{name}是{quality}品质的{wtype}。"
        })

    return qa_pairs


def generate_type_confirm_qa(weapon: dict) -> list:
    """生成类型确认问答（是/不是）"""
    name = weapon["name"]
    wtype = weapon["type"]

    qa_pairs = []

    # 正确类型确认
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是{wtype}吗？",
        "output": f"是的，{name}是{wtype}。"
    })

    # 错误类型否定（只选2个其他类型）
    other_types = [t for t in ALL_WEAPON_TYPES if t != wtype]
    for wrong_type in other_types[:2]:
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是{wrong_type}吗？",
            "output": f"不是，{name}是{wtype}，不是{wrong_type}。"
        })

    return qa_pairs


def generate_quality_confirm_qa(weapon: dict) -> list:
    """生成品质确认问答（是/不是）"""
    name = weapon["name"]
    quality = weapon["quality"]

    if not quality:
        return []

    qa_pairs = []

    # 正确品质确认
    qa_pairs.append({
        "instruction": "",
        "input": f"{name}是{quality}品质吗？",
        "output": f"是的，{name}是{quality}品质。"
    })

    # 错误品质否定（只选2个其他品质）
    other_qualities = [q for q in QUALITY_ORDER if q != quality]
    for wrong_quality in other_qualities[:2]:
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是{wrong_quality}品质吗？",
            "output": f"不是，{name}是{quality}品质，不是{wrong_quality}品质。"
        })

    return qa_pairs


def generate_quality_comparison_qa() -> list:
    """生成品质对比问答 - 固定答案"""
    qa_pairs = []
    quality_str = "轩辕 > 黑鹰 > 铁爪 > 卓越 > 精制 > 改进 > 完好 > 修复 > 破损"

    for i, q1 in enumerate(QUALITY_ORDER):
        for j, q2 in enumerate(QUALITY_ORDER):
            if i >= j:
                continue

            # q1 排在前面，品质更高
            qa_pairs.append({
                "instruction": "",
                "input": f"{q1}和{q2}哪个品质更好？",
                "output": f"{q1}品质更好。品质从高到低：{quality_str}。"
            })
            qa_pairs.append({
                "instruction": "",
                "input": f"{q2}和{q1}哪个品质更好？",
                "output": f"{q1}品质更好。品质从高到低：{quality_str}。"
            })

    return qa_pairs


def generate_model_comparison_qa(weapons_by_type: dict) -> list:
    """生成同类型不同型号对比问答"""
    qa_pairs = []

    for wtype, weapons in weapons_by_type.items():
        models = list(set(w["model"] for w in weapons if w["model"]))
        if len(models) < 2:
            continue

        # 两两对比（限制数量）
        for i, model1 in enumerate(models):
            for model2 in models[i+1:]:
                full_name1 = f"{model1}{wtype}"
                full_name2 = f"{model2}{wtype}"

                qa_pairs.append({
                    "instruction": "",
                    "input": f"{full_name1}和{full_name2}有什么区别？",
                    "output": f"{full_name1}和{full_name2}都是{wtype}，但它们是不同的武器型号。"
                })

                qa_pairs.append({
                    "instruction": "",
                    "input": f"{full_name1}是{full_name2}吗？",
                    "output": f"不是，{full_name1}和{full_name2}是两种不同的{wtype}。"
                })

    return qa_pairs


def generate_type_difference_qa(weapons_by_type: dict) -> list:
    """生成不同类型武器区分问答"""
    qa_pairs = []
    type_list = list(weapons_by_type.keys())

    for i, type1 in enumerate(type_list):
        for type2 in type_list[i+1:]:
            qa_pairs.append({
                "instruction": "",
                "input": f"{type1}和{type2}有什么区别？",
                "output": f"{type1}和{type2}是两种不同的武器类型。"
            })

            # 取一个型号问类型
            models1 = list(set(w["model"] for w in weapons_by_type[type1] if w["model"]))[:1]
            models2 = list(set(w["model"] for w in weapons_by_type[type2] if w["model"]))[:1]

            if models1:
                full_name = f"{models1[0]}{type1}"
                qa_pairs.append({
                    "instruction": "",
                    "input": f"{full_name}是{type1}还是{type2}？",
                    "output": f"{full_name}是{type1}。"
                })

            if models2:
                full_name = f"{models2[0]}{type2}"
                qa_pairs.append({
                    "instruction": "",
                    "input": f"{full_name}是{type1}还是{type2}？",
                    "output": f"{full_name}是{type2}。"
                })

    return qa_pairs


def generate_similar_weapon_clarify_qa() -> list:
    """生成相似武器澄清问答"""
    qa_pairs = []

    similar_pairs = [
        ("M416", "M417", "突击步枪", "射手步枪"),
        ("M24", "M249", "狙击枪", "轻机枪"),
        ("MK12", "MK14", "射手步枪", "射手步枪"),
        ("P90", "P92", "冲锋枪", "手枪"),
        ("P18C", "P1911", "手枪", "手枪"),
    ]

    for m1, m2, t1, t2 in similar_pairs:
        full_name1 = f"{m1}{t1}"
        full_name2 = f"{m2}{t2}"

        if t1 == t2:
            qa_pairs.append({
                "instruction": "",
                "input": f"{full_name1}和{full_name2}是同一种武器吗？",
                "output": f"不是，{full_name1}和{full_name2}是两种不同的{t1}。"
            })
        else:
            qa_pairs.append({
                "instruction": "",
                "input": f"{full_name1}和{full_name2}是同一种武器吗？",
                "output": f"不是，{full_name1}是{t1}，{full_name2}是{t2}。"
            })
            qa_pairs.append({
                "instruction": "",
                "input": f"{full_name1}和{full_name2}有什么区别？",
                "output": f"{full_name1}是{t1}，{full_name2}是{t2}，它们是不同类型的武器。"
            })

    return qa_pairs


def generate_combo_existence_qa(weapons_by_type_quality: dict) -> list:
    """生成组合条件存在性问答（有/没有）"""
    qa_pairs = []

    all_combos = set(weapons_by_type_quality.keys())

    # 存在的组合
    for (wtype, quality), weapons in weapons_by_type_quality.items():
        if weapons:
            weapon = weapons[0]  # 固定取第一个作为例子
            qa_pairs.append({
                "instruction": "",
                "input": f"有{quality}品质的{wtype}吗？",
                "output": f"有，{weapon['name']}就是{quality}品质的{wtype}。"
            })

    # 不存在的组合
    for wtype in ALL_WEAPON_TYPES:
        for quality in QUALITY_ORDER:
            if (wtype, quality) not in all_combos:
                qa_pairs.append({
                    "instruction": "",
                    "input": f"有{quality}品质的{wtype}吗？",
                    "output": f"没有，武器库中没有{quality}品质的{wtype}。"
                })

    return qa_pairs


def generate_type_definition_qa(weapons_by_type: dict) -> list:
    """生成武器类型定义问答"""
    qa_pairs = []

    all_types = "、".join(list(weapons_by_type.keys()))
    qa_pairs.append({
        "instruction": "",
        "input": "武器库有哪些武器类型？",
        "output": f"武器库中的武器类型包括：{all_types}。"
    })

    qa_pairs.append({
        "instruction": "",
        "input": "武器有几种类型？",
        "output": f"武器库中有{len(weapons_by_type)}种武器类型：{all_types}。"
    })

    return qa_pairs


def generate_full_list_qa(weapons_by_type_quality: dict, weapons_by_type: dict, weapons_by_quality: dict) -> list:
    """生成完整列举问答 - 列出所有符合条件的武器（答案唯一确定）"""
    qa_pairs = []

    # 1. 列出某类型+某品质的所有武器（如：所有轩辕品质的狙击枪）
    for (wtype, quality), weapons in weapons_by_type_quality.items():
        if not weapons:
            continue
        # 去重并按名称排序确保顺序固定
        unique_names = sorted(set(w["name"] for w in weapons))
        weapon_names = "、".join(unique_names)
        count = len(unique_names)

        # 多种问法，同一个答案
        qa_pairs.append({
            "instruction": "",
            "input": f"列出所有{quality}品质的{wtype}",
            "output": f"{quality}品质的{wtype}共有{count}个：{weapon_names}。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"有哪些{quality}品质的{wtype}？",
            "output": f"{quality}品质的{wtype}有：{weapon_names}。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"武器库里{quality}品质的{wtype}有哪些？",
            "output": f"武器库中{quality}品质的{wtype}包括：{weapon_names}。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{quality}{wtype}有哪些？",
            "output": f"{quality}品质的{wtype}有：{weapon_names}。"
        })

    # 2. 列出某品质的所有武器（如：所有轩辕品质的武器）
    for quality, weapons in weapons_by_quality.items():
        if not weapons:
            continue
        unique_names = sorted(set(w["name"] for w in weapons))
        weapon_names = "、".join(unique_names)
        count = len(unique_names)

        qa_pairs.append({
            "instruction": "",
            "input": f"列出所有{quality}品质的武器",
            "output": f"{quality}品质的武器共有{count}个：{weapon_names}。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"有哪些{quality}品质的武器？",
            "output": f"{quality}品质的武器有：{weapon_names}。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"武器库里有哪些{quality}级武器？",
            "output": f"武器库中{quality}品质的武器包括：{weapon_names}。"
        })

    # 3. 列出某类型的所有武器（如：所有狙击枪）
    for wtype, weapons in weapons_by_type.items():
        if not weapons:
            continue
        unique_names = sorted(set(w["name"] for w in weapons))
        weapon_names = "、".join(unique_names)
        count = len(unique_names)

        qa_pairs.append({
            "instruction": "",
            "input": f"列出所有{wtype}",
            "output": f"武器库中的{wtype}共有{count}个：{weapon_names}。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"有哪些{wtype}？",
            "output": f"武器库中的{wtype}有：{weapon_names}。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"武器库里有哪些{wtype}？",
            "output": f"武器库中的{wtype}包括：{weapon_names}。"
        })

    # 4. 统计数量类问题
    for (wtype, quality), weapons in weapons_by_type_quality.items():
        count = len(set(w["name"] for w in weapons))
        qa_pairs.append({
            "instruction": "",
            "input": f"有多少{quality}品质的{wtype}？",
            "output": f"武器库中有{count}个{quality}品质的{wtype}。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{quality}品质的{wtype}有几个？",
            "output": f"{quality}品质的{wtype}有{count}个。"
        })

    for quality, weapons in weapons_by_quality.items():
        count = len(set(w["name"] for w in weapons))
        qa_pairs.append({
            "instruction": "",
            "input": f"有多少{quality}品质的武器？",
            "output": f"武器库中有{count}个{quality}品质的武器。"
        })

    for wtype, weapons in weapons_by_type.items():
        count = len(set(w["name"] for w in weapons))
        qa_pairs.append({
            "instruction": "",
            "input": f"有多少{wtype}？",
            "output": f"武器库中有{count}个{wtype}。"
        })

    return qa_pairs


# ============ 防具相关函数 ============

def parse_armor_items(csv_path: str) -> dict:
    """解析防具数据（头盔和防弹衣）"""
    import re

    helmets = []
    vests = []
    helmets_by_level = defaultdict(list)
    vests_by_level = defaultdict(list)
    helmets_by_quality = defaultdict(list)
    vests_by_quality = defaultdict(list)

    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            item_name = line.strip()
            if not item_name:
                continue

            if "礼包" in item_name or "物资箱" in item_name:
                continue
            if item_name.startswith("子物品-"):
                continue

            if "头盔" in item_name and "级头盔" in item_name:
                armor_info = parse_single_armor(item_name, "头盔")
                if armor_info:
                    helmets.append(armor_info)
                    helmets_by_level[armor_info["level"]].append(armor_info)
                    if armor_info["quality"]:
                        helmets_by_quality[armor_info["quality"]].append(armor_info)

            elif "防弹衣" in item_name and "级防弹衣" in item_name:
                armor_info = parse_single_armor(item_name, "防弹衣")
                if armor_info:
                    vests.append(armor_info)
                    vests_by_level[armor_info["level"]].append(armor_info)
                    if armor_info["quality"]:
                        vests_by_quality[armor_info["quality"]].append(armor_info)

    return {
        "helmets": helmets,
        "vests": vests,
        "helmets_by_level": dict(helmets_by_level),
        "vests_by_level": dict(vests_by_level),
        "helmets_by_quality": dict(helmets_by_quality),
        "vests_by_quality": dict(vests_by_quality),
        "all_armors": helmets + vests
    }


def parse_single_armor(item_name: str, armor_type: str) -> dict:
    """解析单个防具的信息"""
    import re

    level_match = re.search(r"(\d)级", item_name)
    if not level_match:
        return None
    level = int(level_match.group(1))

    quality = None
    for q in ARMOR_QUALITY_ORDER:
        if f"({q})" in item_name:
            quality = q
            break

    is_special = "·" in item_name
    special_name = None
    if is_special:
        special_match = re.search(r"·(.+)$", item_name)
        if special_match:
            special_name = special_match.group(1)

    return {
        "name": item_name,
        "type": armor_type,
        "level": level,
        "quality": quality,
        "is_special": is_special,
        "special_name": special_name
    }


def generate_armor_level_qa(armor_data: dict) -> list:
    """生成防具等级查询问答"""
    qa_pairs = []

    for armor in armor_data["all_armors"]:
        name = armor["name"]
        level = armor["level"]
        atype = armor["type"]

        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是几级{atype}？",
            "output": f"{name}是{level}级{atype}。"
        })
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是什么等级？",
            "output": f"{name}是{level}级。"
        })

    return qa_pairs


def generate_armor_quality_qa(armor_data: dict) -> list:
    """生成防具品质查询问答"""
    qa_pairs = []

    for armor in armor_data["all_armors"]:
        name = armor["name"]
        quality = armor["quality"]

        if quality:
            answer = f"{name}是{quality}品质。"
        else:
            answer = f"{name}是普通品质。"

        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是什么品质？",
            "output": answer
        })

    return qa_pairs


def generate_armor_type_qa(armor_data: dict) -> list:
    """生成防具类型识别问答"""
    qa_pairs = []

    for armor in armor_data["all_armors"]:
        name = armor["name"]
        atype = armor["type"]
        other_type = "防弹衣" if atype == "头盔" else "头盔"

        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是头盔还是防弹衣？",
            "output": f"{name}是{atype}。"
        })

        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是{atype}吗？",
            "output": f"是的，{name}是{atype}。"
        })

        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是{other_type}吗？",
            "output": f"不是，{name}是{atype}，不是{other_type}。"
        })

    return qa_pairs


def generate_armor_level_confirm_qa(armor_data: dict) -> list:
    """生成防具等级确认问答"""
    qa_pairs = []

    for armor in armor_data["all_armors"]:
        name = armor["name"]
        level = armor["level"]
        atype = armor["type"]

        # 正确等级确认
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是{level}级{atype}吗？",
            "output": f"是的，{name}是{level}级{atype}。"
        })

        # 错误等级否定（只选2个）
        other_levels = [l for l in ARMOR_LEVELS if l != level][:2]
        for wrong_level in other_levels:
            qa_pairs.append({
                "instruction": "",
                "input": f"{name}是{wrong_level}级{atype}吗？",
                "output": f"不是，{name}是{level}级{atype}。"
            })

    return qa_pairs


def generate_armor_quality_confirm_qa(armor_data: dict) -> list:
    """生成防具品质确认问答"""
    qa_pairs = []

    for armor in armor_data["all_armors"]:
        name = armor["name"]
        quality = armor["quality"]

        if not quality:
            continue

        # 正确品质确认
        qa_pairs.append({
            "instruction": "",
            "input": f"{name}是{quality}品质吗？",
            "output": f"是的，{name}是{quality}品质。"
        })

        # 错误品质否定
        other_qualities = [q for q in ARMOR_QUALITY_ORDER if q != quality]
        for wrong_quality in other_qualities:
            qa_pairs.append({
                "instruction": "",
                "input": f"{name}是{wrong_quality}品质吗？",
                "output": f"不是，{name}是{quality}品质，不是{wrong_quality}品质。"
            })

    return qa_pairs


def generate_armor_level_compare_qa(armor_data: dict) -> list:
    """生成防具等级对比问答（限制数量）"""
    qa_pairs = []

    # 头盔对比
    helmets = armor_data["helmets"]
    pairs_added = 0
    for i, h1 in enumerate(helmets):
        if pairs_added >= 100:
            break
        for h2 in helmets[i+1:]:
            if h1["level"] == h2["level"]:
                continue
            if pairs_added >= 100:
                break

            name1, level1 = h1["name"], h1["level"]
            name2, level2 = h2["name"], h2["level"]

            if level1 > level2:
                higher = name1
            else:
                higher = name2

            qa_pairs.append({
                "instruction": "",
                "input": f"{name1}和{name2}哪个等级更高？",
                "output": f"{higher}等级更高。"
            })
            pairs_added += 1

    # 防弹衣对比
    vests = armor_data["vests"]
    pairs_added = 0
    for i, v1 in enumerate(vests):
        if pairs_added >= 100:
            break
        for v2 in vests[i+1:]:
            if v1["level"] == v2["level"]:
                continue
            if pairs_added >= 100:
                break

            name1, level1 = v1["name"], v1["level"]
            name2, level2 = v2["name"], v2["level"]

            if level1 > level2:
                higher = name1
            else:
                higher = name2

            qa_pairs.append({
                "instruction": "",
                "input": f"{name1}和{name2}哪个等级更高？",
                "output": f"{higher}等级更高。"
            })
            pairs_added += 1

    return qa_pairs


def generate_armor_quality_compare_qa(armor_data: dict) -> list:
    """生成防具品质对比问答"""
    qa_pairs = []
    quality_order = {"轩辕": 0, "黑鹰": 1, "铁爪": 2}

    for level in ARMOR_LEVELS:
        # 头盔
        helmets_at_level = armor_data["helmets_by_level"].get(level, [])
        quality_helmets = [h for h in helmets_at_level if h["quality"]]

        for i, h1 in enumerate(quality_helmets):
            for h2 in quality_helmets[i+1:]:
                if h1["quality"] == h2["quality"]:
                    continue

                name1, q1 = h1["name"], h1["quality"]
                name2, q2 = h2["name"], h2["quality"]

                if quality_order[q1] < quality_order[q2]:
                    better = name1
                else:
                    better = name2

                qa_pairs.append({
                    "instruction": "",
                    "input": f"{name1}和{name2}哪个品质更好？",
                    "output": f"{better}品质更好。"
                })

        # 防弹衣
        vests_at_level = armor_data["vests_by_level"].get(level, [])
        quality_vests = [v for v in vests_at_level if v["quality"]]

        for i, v1 in enumerate(quality_vests):
            for v2 in quality_vests[i+1:]:
                if v1["quality"] == v2["quality"]:
                    continue

                name1, q1 = v1["name"], v1["quality"]
                name2, q2 = v2["name"], v2["quality"]

                if quality_order[q1] < quality_order[q2]:
                    better = name1
                else:
                    better = name2

                qa_pairs.append({
                    "instruction": "",
                    "input": f"{name1}和{name2}哪个品质更好？",
                    "output": f"{better}品质更好。"
                })

    return qa_pairs


def generate_armor_definition_qa(armor_data: dict) -> list:
    """生成防具定义问答"""
    qa_pairs = []

    qa_pairs.append({
        "instruction": "",
        "input": "武器库有哪些防具类型？",
        "output": "武器库中的防具类型包括：头盔和防弹衣。"
    })

    qa_pairs.append({
        "instruction": "",
        "input": "防具有哪些种类？",
        "output": "防具分为两种：头盔和防弹衣。"
    })

    helmet_levels = sorted(armor_data["helmets_by_level"].keys())
    if helmet_levels:
        min_level, max_level = min(helmet_levels), max(helmet_levels)
        qa_pairs.append({
            "instruction": "",
            "input": "头盔有哪些等级？",
            "output": f"头盔有{min_level}级到{max_level}级。"
        })

    vest_levels = sorted(armor_data["vests_by_level"].keys())
    if vest_levels:
        min_level, max_level = min(vest_levels), max(vest_levels)
        qa_pairs.append({
            "instruction": "",
            "input": "防弹衣有哪些等级？",
            "output": f"防弹衣有{min_level}级到{max_level}级。"
        })

    qa_pairs.append({
        "instruction": "",
        "input": "防具有哪些品质？",
        "output": "防具品质从高到低为：轩辕 > 黑鹰 > 铁爪。"
    })

    return qa_pairs


def main():
    csv_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/item_name.csv")
    weapons_data = parse_weapons_from_csv(csv_path)

    print(f"解析到 {len(weapons_data['all'])} 个武器")
    print(f"类型+品质组合数: {len(weapons_data['by_type_quality'])}")

    all_qa = []

    # 1. 单武器问答
    print("\n生成单武器问答...")
    for weapon in weapons_data["all"]:
        all_qa.extend(generate_single_weapon_qa(weapon))
    print(f"  单武器问答: {len(all_qa)} 条")

    # 2. 类型确认（是/不是）
    print("生成类型确认...")
    type_confirm_count = len(all_qa)
    for weapon in weapons_data["all"]:
        all_qa.extend(generate_type_confirm_qa(weapon))
    print(f"  类型确认: {len(all_qa) - type_confirm_count} 条")

    # 3. 品质确认（是/不是）
    print("生成品质确认...")
    quality_confirm_count = len(all_qa)
    for weapon in weapons_data["all"]:
        all_qa.extend(generate_quality_confirm_qa(weapon))
    print(f"  品质确认: {len(all_qa) - quality_confirm_count} 条")

    # 4. 品质对比
    print("生成品质对比...")
    quality_compare_qa = generate_quality_comparison_qa()
    all_qa.extend(quality_compare_qa)
    print(f"  品质对比: {len(quality_compare_qa)} 条")

    # 5. 型号对比
    print("生成型号对比...")
    model_compare_qa = generate_model_comparison_qa(weapons_data["by_type"])
    all_qa.extend(model_compare_qa)
    print(f"  型号对比: {len(model_compare_qa)} 条")

    # 6. 类型区分
    print("生成类型区分...")
    type_diff_qa = generate_type_difference_qa(weapons_data["by_type"])
    all_qa.extend(type_diff_qa)
    print(f"  类型区分: {len(type_diff_qa)} 条")

    # 7. 相似武器澄清
    print("生成相似武器澄清...")
    similar_qa = generate_similar_weapon_clarify_qa()
    all_qa.extend(similar_qa)
    print(f"  相似武器澄清: {len(similar_qa)} 条")

    # 8. 组合条件存在性
    print("生成组合条件存在性...")
    combo_qa = generate_combo_existence_qa(weapons_data["by_type_quality"])
    all_qa.extend(combo_qa)
    print(f"  组合条件存在性: {len(combo_qa)} 条")

    # 9. 类型定义
    print("生成类型定义...")
    type_def_qa = generate_type_definition_qa(weapons_data["by_type"])
    all_qa.extend(type_def_qa)
    print(f"  类型定义: {len(type_def_qa)} 条")

    # 10. 完整列举（所有轩辕狙击枪等）
    print("生成完整列举...")
    full_list_qa = generate_full_list_qa(
        weapons_data["by_type_quality"],
        weapons_data["by_type"],
        weapons_data["by_quality"]
    )
    all_qa.extend(full_list_qa)
    print(f"  完整列举: {len(full_list_qa)} 条")

    # ============ 防具问答 ============
    print("\n" + "="*50)
    print("开始生成防具数据...")
    print("="*50)

    armor_data = parse_armor_items(csv_path)
    print(f"解析到 {len(armor_data['helmets'])} 个头盔")
    print(f"解析到 {len(armor_data['vests'])} 个防弹衣")

    # 10. 防具等级查询
    print("\n生成防具等级查询...")
    armor_level_qa = generate_armor_level_qa(armor_data)
    all_qa.extend(armor_level_qa)
    print(f"  防具等级查询: {len(armor_level_qa)} 条")

    # 11. 防具品质查询
    print("生成防具品质查询...")
    armor_quality_qa = generate_armor_quality_qa(armor_data)
    all_qa.extend(armor_quality_qa)
    print(f"  防具品质查询: {len(armor_quality_qa)} 条")

    # 12. 防具类型识别
    print("生成防具类型识别...")
    armor_type_qa = generate_armor_type_qa(armor_data)
    all_qa.extend(armor_type_qa)
    print(f"  防具类型识别: {len(armor_type_qa)} 条")

    # 13. 防具等级确认
    print("生成防具等级确认...")
    armor_level_confirm_qa = generate_armor_level_confirm_qa(armor_data)
    all_qa.extend(armor_level_confirm_qa)
    print(f"  防具等级确认: {len(armor_level_confirm_qa)} 条")

    # 14. 防具品质确认
    print("生成防具品质确认...")
    armor_quality_confirm_qa = generate_armor_quality_confirm_qa(armor_data)
    all_qa.extend(armor_quality_confirm_qa)
    print(f"  防具品质确认: {len(armor_quality_confirm_qa)} 条")

    # 15. 防具等级对比
    print("生成防具等级对比...")
    armor_level_compare_qa = generate_armor_level_compare_qa(armor_data)
    all_qa.extend(armor_level_compare_qa)
    print(f"  防具等级对比: {len(armor_level_compare_qa)} 条")

    # 16. 防具品质对比
    print("生成防具品质对比...")
    armor_quality_compare_qa = generate_armor_quality_compare_qa(armor_data)
    all_qa.extend(armor_quality_compare_qa)
    print(f"  防具品质对比: {len(armor_quality_compare_qa)} 条")

    # 17. 防具定义
    print("生成防具定义...")
    armor_def_qa = generate_armor_definition_qa(armor_data)
    all_qa.extend(armor_def_qa)
    print(f"  防具定义: {len(armor_def_qa)} 条")

    # 去重
    print("\n去重处理...")
    seen_inputs = set()
    unique_qa = []
    for qa in all_qa:
        inp = qa.get("input", "")
        if inp not in seen_inputs:
            seen_inputs.add(inp)
            unique_qa.append(qa)
    print(f"  去重前: {len(all_qa)} 条")
    print(f"  去重后: {len(unique_qa)} 条")
    all_qa = unique_qa

    # 打乱顺序
    random.shuffle(all_qa)

    print(f"\n总数据量: {len(all_qa)} 条")

    # 保存
    output_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/data/weapon_inventory_sft_v5.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_qa, f, ensure_ascii=False, indent=2)

    print(f"\n数据已保存到: {output_path}")

    # 显示示例
    print("\n=== 数据示例 ===")
    for i, qa in enumerate(all_qa[:10]):
        print(f"\n[{i+1}]")
        print(f"  instruction: \"{qa['instruction']}\"")
        print(f"  input: {qa['input']}")
        print(f"  output: {qa['output']}")


if __name__ == "__main__":
    main()
