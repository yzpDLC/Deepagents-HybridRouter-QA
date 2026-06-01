"""
BERT 微调训练脚本
在终端中运行: python -m agent.routing.train.train

前提: 先运行 generate_data.py 生成 training_data.jsonl
输出: agent/routing/model/ 下的微调模型文件
"""

import json
import logging
import sys
from pathlib import Path

import numpy as np
from sklearn.model_selection import train_test_split

# 确保项目根目录在 sys.path 中
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 路径
DATA_PATH = Path(__file__).resolve().parent / "training_data.jsonl"
MODEL_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "model"
_BERT_MODEL_NAME = "bert-base-chinese"
_MAX_LENGTH = 128
_EPOCHS = 3
_BATCH_SIZE = 16
_LEARNING_RATE = 2e-5

LABEL2ID = {"NEO4J_QUERY": 0, "WEB_QUERY": 1}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}


def load_data(path: Path) -> tuple[list[str], list[int]]:
    """加载训练数据"""
    texts, labels = [], []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            query = record["query"]
            intent = record["intent"]

            # 如果有历史上下文，拼进去
            history = record.get("history_context", "")
            if history:
                text = f"{history}\n[当前]query:{query}"
            else:
                text = query

            texts.append(text)
            labels.append(LABEL2ID[intent])

    return texts, labels


def train():
    """训练 BERT 分类模型"""
    if not DATA_PATH.exists():
        logger.error(f"训练数据不存在: {DATA_PATH}")
        logger.error("请先运行: python -m agent.routing.train.generate_data")
        return

    logger.info(f"加载数据: {DATA_PATH}")
    texts, labels = load_data(DATA_PATH)
    logger.info(f"共 {len(texts)} 条数据")
    logger.info(f"标签分布: NEO4J_QUERY={labels.count(0)}, WEB_QUERY={labels.count(1)}")

    # 划分数据集
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels,
    )
    logger.info(f"训练集: {len(train_texts)} 验证集: {len(val_texts)}")

    # 导入 transformers（局部导入避免在未安装时影响整个应用）
    from transformers import (
        BertForSequenceClassification,
        BertTokenizerFast,
        Trainer,
        TrainingArguments,
        DataCollatorWithPadding,
    )
    import torch

    # 加载 tokenizer 和模型
    tokenizer = BertTokenizerFast.from_pretrained(_BERT_MODEL_NAME)
    model = BertForSequenceClassification.from_pretrained(
        _BERT_MODEL_NAME,
        num_labels=len(LABEL2ID),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    # 构造 Dataset
    class IntentDataset(torch.utils.data.Dataset):
        def __init__(self, texts, labels, tokenizer, max_length):
            self.encodings = tokenizer(
                texts, truncation=True, padding=True,
                max_length=max_length, return_tensors="pt",
            )
            self.labels = torch.tensor(labels)

        def __getitem__(self, idx):
            item = {k: v[idx] for k, v in self.encodings.items()}
            item["labels"] = self.labels[idx]
            return item

        def __len__(self):
            return len(self.labels)

    train_dataset = IntentDataset(train_texts, train_labels, tokenizer, _MAX_LENGTH)
    val_dataset = IntentDataset(val_texts, val_labels, tokenizer, _MAX_LENGTH)

    # 训练参数
    output_dir = str(MODEL_OUTPUT_DIR)
    MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=_EPOCHS,
        per_device_train_batch_size=_BATCH_SIZE,
        per_device_eval_batch_size=_BATCH_SIZE * 2,
        learning_rate=_LEARNING_RATE,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_dir=output_dir,
        logging_steps=10,
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        save_total_limit=2,
        remove_unused_columns=False,
    )

    # 评估指标
    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=-1)
        accuracy = (predictions == labels).mean()
        return {"accuracy": accuracy}

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=compute_metrics,
    )

    # 训练
    logger.info("开始训练...")
    trainer.train()

    # 保存模型
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    logger.info(f"模型已保存至: {output_dir}")

    # 最终评估
    eval_result = trainer.evaluate()
    logger.info(f"验证集评估: accuracy={eval_result['eval_accuracy']:.4f}")


if __name__ == "__main__":
    train()
