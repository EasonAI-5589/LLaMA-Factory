# 模型评估指南

## 测试数据集

`data/weapon_inventory_test_100.json` 包含 101 条测试样本：

| 问题类型 | 数量 | 说明 |
|---------|------|------|
| 类型识别 | 15 | XX是什么类型的武器？ |
| 品质比较 | 15 | XX和YY哪个品质更高？ |
| 品质+类型列举 | 15 | 有哪些XX品质的YY？ |
| 三武器对比(正) | 15 | A、B、C是同一类武器吗？(是) |
| 三武器对比(反) | 20 | A、B、C是同一类武器吗？(否) |
| 描述/介绍 | 16 | 介绍一下XX |
| 品质分类 | 5 | XX属于什么品质级别？ |

## 运行评估

### 方式一：LLaMA-Factory CLI

```bash
# 使用训练好的 LoRA 模型评估
llamafactory-cli eval \
    --model_name_or_path Qwen/Qwen2.5-7B-Instruct \
    --adapter_name_or_path ./saves/qwen2.5-7b/lora/weapon-inventory-sft \
    --template qwen \
    --task weapon_eval \
    --eval_dataset weapon_inventory_test_100
```

### 方式二：vLLM 批量推理

```bash
python weapon_inventory_project/eval_vllm.py \
    --model_path ./saves/qwen2.5-7b/lora/weapon-inventory-sft \
    --test_file data/weapon_inventory_test_100.json \
    --output_file eval_results.json
```

### 方式三：手动测试

```bash
# 启动 CLI 对话
llamafactory-cli chat \
    --model_name_or_path Qwen/Qwen2.5-7B-Instruct \
    --adapter_name_or_path ./saves/qwen2.5-7b/lora/weapon-inventory-sft \
    --template qwen
```

然后手动输入测试问题进行验证。

## 重点关注

训练后需重点验证：

1. **三武器类型对比** - 正例应答"是的，...都是XX"，反例应答"不是，...它们不是同一类武器"
2. **品质+类型列举** - 返回的武器必须是正确的类型（如问狙击枪不能返回机枪）
3. **类型识别** - 准确识别 7 种枪械类型
