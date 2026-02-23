"""Agent 工具定义 — 遵循 OpenAI Function Calling Schema"""

SEARCH_DOCUMENTS_TOOL = {
    "type": "function",
    "function": {
        "name": "search_documents",
        "description": (
            "在用户上传的文档或选定的知识库中搜索与查询相关的内容片段。"
            "当用户的问题需要参考文档中的具体信息时调用此工具。"
            "如果首次检索结果不够充分，可以调整查询文本重新搜索。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "用于检索的查询文本，应尽量精准地描述需要查找的信息",
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回的相关片段数量，默认为 5",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}
