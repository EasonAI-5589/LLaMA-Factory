#!/usr/bin/env python3
"""
修复 v2 数据集，使其符合 v5 标准：
1. instruction 设为空
2. 列举类问题使用完整列表（从 v5 获取正确答案）
3. 去除有问题的数据
4. 保留确定性答案的数据
"""

import json
from pathlib import Path
from collections import defaultdict

# 品质等级排序（从高到低）
QUALITY_ORDER = ["轩辕", "黑鹰", "铁爪", "卓越", "精制", "改进", "完好", "修复", "破损"]

def load_v5_data():
    """加载 v5 数据作为参考"""
    v5_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/data/weapon_inventory_sft_v5.json")
    with open(v5_path, "r", encoding="utf-8") as f:
        v5_data = json.load(f)

    # 建立 input -> output 的映射
    v5_map = {}
    for item in v5_data:
        v5_map[item["input"]] = item["output"]

    return v5_map


def fix_v2_data():
    """修复 v2 数据"""
    v2_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/data/weapon_inventory_sft_v2.json")
    with open(v2_path, "r", encoding="utf-8") as f:
        v2_data = json.load(f)

    v5_map = load_v5_data()

    fixed_data = []
    skipped = defaultdict(int)
    fixed_count = defaultdict(int)

    for item in v2_data:
        task_type = item.get("task_type", "unknown")
        inp = item["input"]
        out = item["output"]

        # 1. item_info: 单武器查询 - 可以保留，但需要检查答案是否正确
        if task_type == "item_info":
            # 清空 instruction
            fixed_item = {
                "instruction": "",
                "input": inp,
                "output": out
            }
            fixed_data.append(fixed_item)
            fixed_count["item_info"] += 1

        # 2. quality_compare: 品质对比 - 答案确定，可以保留
        elif task_type == "quality_compare":
            fixed_item = {
                "instruction": "",
                "input": inp,
                "output": out
            }
            fixed_data.append(fixed_item)
            fixed_count["quality_compare"] += 1

        # 3. model_query: 型号查询 - 跳过，问法不规范（如"列出所有MK20"应该是"列出所有MK20-H射手步枪"）
        elif task_type == "model_query":
            # 这些数据问法不完整，跳过
            skipped["model_query_incomplete"] += 1

        # 4. category_query / quality_query / all_weapons: 列举类 - 跳过（v5已有完整版本）
        elif task_type in ["category_query", "quality_query", "all_weapons"]:
            # 这些是随机采样的列表，跳过
            skipped[task_type] += 1

        else:
            skipped["unknown"] += 1

    print("=== 修复统计 ===")
    print(f"保留的数据:")
    for k, v in fixed_count.items():
        print(f"  {k}: {v}")
    print(f"\n跳过的数据:")
    for k, v in skipped.items():
        print(f"  {k}: {v}")
    print(f"\n总计: 保留 {len(fixed_data)} 条, 跳过 {sum(skipped.values())} 条")

    return fixed_data


def main():
    fixed_data = fix_v2_data()

    # 去重
    seen_inputs = set()
    unique_data = []
    for item in fixed_data:
        if item["input"] not in seen_inputs:
            seen_inputs.add(item["input"])
            unique_data.append(item)

    print(f"\n去重后: {len(unique_data)} 条")

    # 保存
    output_path = Path("/Users/guoyichen/EasonAI/LLaMA-Factory/data/weapon_inventory_sft_v2_fixed.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_data, f, ensure_ascii=False, indent=2)

    print(f"\n已保存到: {output_path}")

    # 显示示例
    print("\n=== 数据示例 ===")
    for i, item in enumerate(unique_data[:5]):
        print(f"\n[{i+1}]")
        print(f"  input: {item['input']}")
        print(f"  output: {item['output'][:80]}...")


if __name__ == "__main__":
    main()
