# 上传模型到 Hugging Face

## 1. 准备工作

### 1.1 创建 HF Token（首次使用）
1. 访问 https://huggingface.co/settings/tokens
2. 点击 **Create new token**
3. 选择 **Write** 权限
4. 复制保存 token

### 1.2 登录 HF
```bash
# 清除旧的环境变量（如果有）
unset HF_TOKEN
unset HUGGING_FACE_HUB_TOKEN

# 登录
hf auth login
# 粘贴你的 token
```

### 1.3 创建 Model Repo（首次使用）
1. 访问 https://huggingface.co/new
2. 填写 Model name（如 `weapon-inventory-lora`）
3. 选择 Public 或 Private
4. 点击 Create model

## 2. 上传模型

### 方式一：上传指定 checkpoint
```bash
hf upload <用户名>/<repo名> <本地路径>

# 示例
hf upload YICHEN013/weapon-inventory-lora ./saves/qwen2.5-7b/lora/weapon-inventory-sft/checkpoint-310
```

### 方式二：上传整个目录
```bash
hf upload YICHEN013/weapon-inventory-lora ./saves/qwen2.5-7b/lora/weapon-inventory-sft/
```

### 方式三：上传到子目录
```bash
# 上传到 repo 的 v8 子目录
hf upload YICHEN013/weapon-inventory-lora ./saves/qwen2.5-7b/lora/weapon-inventory-sft/checkpoint-310 --path-in-repo v8
```

## 3. 常见问题

### 403 Forbidden 错误
1. 清除缓存和环境变量：
```bash
unset HF_TOKEN
unset HUGGING_FACE_HUB_TOKEN
hf auth logout
```
2. 重新登录：
```bash
hf auth login
```
3. 重新上传

### 检查登录状态
```bash
hf whoami
```

### 查看 repo
上传成功后访问：`https://huggingface.co/<用户名>/<repo名>`

## 4. 下载模型

```bash
# 下载整个 repo
hf download YICHEN013/weapon-inventory-lora

# 下载到指定目录
hf download YICHEN013/weapon-inventory-lora --local-dir ./my-model
```

## 5. 在代码中使用

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

# 加载基座模型
base_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-7B-Instruct")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct")

# 加载 LoRA
model = PeftModel.from_pretrained(base_model, "YICHEN013/weapon-inventory-lora")
```
