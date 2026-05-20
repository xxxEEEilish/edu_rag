"""题目 Schema。

题目是教育知识库区别于普通文档 RAG 的核心对象。它需要完整保存题干、选项、
答案和解析，后续题库检索和题目答疑都依赖这些字段。
"""

from pydantic import BaseModel, Field


class Question(BaseModel):
    """结构化题目对象。

    当前模型保持格式兼容性：选择题可以使用 options，简答题或编程题可以没有
    options；answer 既支持字符串，也支持多答案列表。
    """

    question_id: str
    question_code: str | None = None
    question_bank_name: str | None = None
    question_type: str
    stem: str
    options: list[str] = Field(default_factory=list)
    answer: str | list[str] | None = None
    analysis: str | None = None
    difficulty: str | None = None
    course_id: str | None = None
    course_name: str | None = None
    chapter_id: str | None = None
    chapter_name: str | None = None
    knowledge_points: list[str] = Field(default_factory=list)
    tenant_id: str = "default"
