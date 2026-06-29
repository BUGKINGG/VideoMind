from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Callable, TypeVar


T = TypeVar("T")


@dataclass
class LocalReranker:
    """
    轻量级本地重排序器，在向量粗召回后进行术语匹配精排。

    工作原理：
    1. 将查询和候选文本都切分为术语（英文单词 + 中文字符 + 中文二元组）
    2. 对每个候选项计算 recall（匹配术语占查询术语的比例）和 density（匹配术语密度）
    3. 综合分数 = recall * 0.8 + density * 0.2，额外加上微小的位置偏置
    4. 按分数降序返回 top-K

    设计为可替换：生产环境中可替换为真正的交叉编码器（如 bge-reranker、Cohere Rerank 等）。
    """

    def rerank(
        self,
        query: str,
        items: list[T],
        text_getter: Callable[[T], str],
        limit: int,
    ) -> list[T]:
        """
        对候选列表进行重排序，返回 top-K。

        Args:
            query:       用户查询文本
            items:       候选项目列表
            text_getter: 从候选项提取文本的函数
            limit:       返回的最大数量

        Returns:
            重排序后的 top-K 候选项列表
        """
        if not items or limit <= 0:
            return []

        # 提取查询术语
        query_terms = self._terms(query)
        if not query_terms:
            return items[:limit]

        query_set = set(query_terms)
        scored_items: list[tuple[float, int, T]] = []

        for index, item in enumerate(items):
            text = text_getter(item)
            item_terms = self._terms(text)
            score = self._score(query_set=query_set, item_terms=item_terms)
            # 位置偏置：相同的匹配分数，原始排序靠前的优先
            score += 0.02 / (index + 1)
            scored_items.append((score, index, item))

        # 按分数降序排列（分数相同时按原始位置靠前的优先）
        scored_items.sort(key=lambda row: (row[0], -row[1]), reverse=True)
        return [item for _, _, item in scored_items[:limit]]

    def _score(self, query_set: set[str], item_terms: list[str]) -> float:
        """
        计算单条候选项与查询的匹配分数。

        recall  = 匹配术语数 / 查询术语数（候选覆盖了查询的多少）
        density = 匹配术语数 / sqrt(候选术语数)（匹配术语在候选中的密度）
        """
        if not item_terms:
            return 0.0

        item_set = set(item_terms)
        matched_terms = query_set & item_set
        recall = len(matched_terms) / max(len(query_set), 1)
        density = len(matched_terms) / math.sqrt(max(len(item_terms), 1))
        return recall * 0.8 + density * 0.2

    def _terms(self, text: str) -> list[str]:
        """
        将文本切分为术语列表：
        - 英文/数字词（如 "video", "123"）
        - 中文字符（单个字）
        - 中文二元组（相邻两字组成的词组，用于捕捉词级匹配）
        """
        lowered = text.lower()
        words = re.findall(r"[a-z0-9]+", lowered)
        chinese_chars = re.findall(r"[一-鿿]", lowered)
        chinese_bigrams = [
            "".join(chinese_chars[index : index + 2])
            for index in range(max(len(chinese_chars) - 1, 0))
        ]
        return words + chinese_chars + chinese_bigrams
