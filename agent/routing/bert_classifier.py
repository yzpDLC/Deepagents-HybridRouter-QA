"""
BERT 分类器：加载微调模型进行意图分类
无模型文件时返回低置信度兜底，规则引擎正常运作
"""
import torch
import logging
import os
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent #使用Path类解决路径问题
_MODEL_DIR = _PROJECT_ROOT / settings.bert_model_path
_MAX_LENGTH = settings.bert_max_length

ID2LABEL = {0: "NEO4J_QUERY", 1: "WEB_QUERY"}


class BertIntentClassifier:
    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._ready = False

    def predict(self, query: str, history_context: str = "") -> dict:
        """预测意图

        Returns:
            dict: {"intent": str, "confidence": float, "model": str}
        """
        if not self._ready:
            self._lazy_init()

        if not self._ready:
            return {"intent": "NEO4J_QUERY", "confidence": 0.0, "model": "not_available"}

        return self._predict_finetuned(query, history_context)

    def _lazy_init(self):
        if self._ready:
            return        #如果加载了就直接返回
        else:
            self._ready = self._try_load_finetuned() #否则尝试加载

        if self._ready:
            logger.info(f"BERT 分类器: 已加载微调模型 ({_MODEL_DIR})")
        else:
            logger.info("BERT 分类器: 无微调模型, 跳过 (规则引擎正常运作)")

    def _try_load_finetuned(self) -> bool:
        """尝试加载微调后的分类模型"""
        model_path = str(_MODEL_DIR)
        if not os.path.isdir(model_path):  #路径检测，避免加载不存在的路径
            return False
        try:
            from transformers import BertForSequenceClassification, BertTokenizerFast
            self._tokenizer = BertTokenizerFast.from_pretrained(model_path)
            self._model = BertForSequenceClassification.from_pretrained(model_path)
            self._model.eval()
            return True
        except Exception as e:
            logger.warning(f"加载微调模型失败: {e}")
            return False

    def _predict_finetuned(self, query: str, history_context: str) -> dict:
        """微调 BERT 分类推理"""
        try:
            text = f"{history_context}\n[当前]query:{query}" if history_context else query

            inputs = self._tokenizer(
                text, return_tensors="pt", truncation=True,
                padding=True, max_length=_MAX_LENGTH,
            )

            with torch.no_grad():
                outputs = self._model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1).squeeze(0)

            pred_id = int(torch.argmax(probs))

            return {
                "intent": ID2LABEL[pred_id],
                "confidence": float(probs[pred_id]),
                "model": "finetuned_bert",
            }
        except Exception as e:
            logger.error(f"BERT 推理失败: {e}")
            return {"intent": "NEO4J_QUERY", "confidence": 0.0, "model": "inference_error"}
