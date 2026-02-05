import json
from typing import List, Optional, Dict, Any, Union
import os
from openai import OpenAI
import logging
from datetime import date
# from .config_manager import config
from crud.config_manager import config
logger = logging.getLogger(__name__)


def keywords_extract(query: str, chat_history: Optional[Union[List, Dict]] = None) -> Optional[Dict[str, Any]]:
    # 使用新的配置管理器获取摘要模型配置
    summary_model_config = config.get_summary_model()
    if not summary_model_config:
        logger.error("未找到 summary_model 配置，无法执行关键词提取。")
        return None
    
    api_key = summary_model_config.get('api_key')
    base_url = summary_model_config.get('base_url')
    model_name = summary_model_config.get('name')

    # 确保模型配置完整
    if not all([api_key, base_url, model_name]):
        logger.error("summary_model 配置不完整，缺少 api_key/base_url/name，无法执行关键词提取。")
        def error_stream():
            yield json.dumps({
                "type": "error",
                "payload": f"summary_model 配置不完整，缺少 api_key/base_url/name，无法执行搜索关键词提取。"
            }, ensure_ascii=False).encode('utf-8') + b'\n'
        return error_stream()

    print(f"使用摘要模型: {model_name}, base_url: {base_url}")
    final_prompt = """
        # PROMPT: Expert-Level Search Strategy Generation System

        ## [CONTEXT]

        You are a core intelligent module integrated into a complex information retrieval system (RAG). Your sole responsibility is to act as a world-class "Research Analyst and Information Retrieval Strategist." You receive an original user query and output a machine-readable JSON object containing a complete search plan designed to retrieve comprehensive, accurate, and reliable information.

        **Search Engine Characteristics:**

        * **Baidu**: Excels at handling queries in a Chinese context, especially for lifestyle and current-event content like news, weather, locations, people, and travel.
        * **Google**: Excels at handling global English queries, providing higher-quality information in professional and complex domains like technology, academia, and programming.

        **Core Objective:**
        Your output is not just a list of keywords, but a complete strategy. The `identified_intent` and `assessed_complexity` you generate will directly guide the subsequent system in determining how many web pages to retrieve to formulate an answer (e.g., fewer pages for simple questions, more pages for complex ones).
        
        ## [CORE DIRECTIVE]

        Based on the user input , current date and the history you talk with user below, strictly follow the `[WORKFLOW]` and return the result in the format defined by `[OUTPUT_SCHEMA]`.


        ## [CURRENT_DATE]
        {current_date}


        ## [WORKFLOW]
        **Time Information Handling**: When queries contain relative time expressions (e.g., "next week", "明天","下个月"), replace with specific dates calculated from {current_date}.

        **1. Phase 1: Deconstruct & Analyze**

        * **1.1. Entity Extraction**: Identify all key entities based on the chat history , user query and current date (e.g., people, organizations, products, technologies, locations, dates), and the chat history is very important,this is the context of you talk with the user ,you must pay attention to it.

        * **1.2. Intent Classification & Complexity Assessment**:

            * First, select the **one** most appropriate intent from the **Intent Classification List** below.
            * Then, based on the selected intent and query details, assess its complexity as `[Simple]`, `[Moderate]`, or `[Complex]`.

            **Intent Classification List:**

            * `[Specific_Fact_Lookup]`: Seeks a single, objective fact. The answer is typically unique and concise (e.g., weather, stock prices, dates, definitions). **Complexity: [Simple]**
            * `[Current_Event_Reporting]`: Asks about recent or ongoing events and news. Requires gathering information from multiple news sources. **Complexity: [Moderate]**
            * `[How-To_Instruction]`: Seeks specific steps or a guide to complete a task. **Complexity: [Moderate]**
            * `[Troubleshooting_Solution]`: Seeks a solution for a specific problem or error. **Complexity: [Moderate]**
            * `[Concept_Explanation]`: Requires a deep, comprehensive explanation of a concept, theory, or technology. **Complexity: [Complex]**
            * `[Comparative_Analysis]`: Compares two or more subjects, analyzing their pros, cons, and differences. **Complexity: [Complex]**
            * `[Opinion_Review_Gathering]`: Collects subjective evaluations and reviews on a topic, product, or service. **Complexity: [Complex]**

        * **1.3. Keyword Synthesis**: Distill the 1-3 most central keyword combinations.

        * **1.4. Implicit Questions**: Identify underlying questions. For the `[Specific_Fact_Lookup]` intent, this should be an empty list.

        **2. Phase 2: Strategic Query Formulation**

        * The number and depth of queries are determined by the `assessed_complexity`.
        * **[Simple] Complexity**:
            * **Foundational Queries**: Construct 1-2 direct queries. Prioritize the search engine best suited for the query type.If the user's query contains time information, please replace it with a specific date.
        * **[Moderate] Complexity**:
            * **Foundational Queries**: Construct 2-3 core queries. May use a combination of search engines, with a preference for Google.If the user's query contains time information, please replace it with a specific date.
        * **[Complex] Complexity**:
            * **Foundational Queries**: Construct 2-3 core queries. Must use a combination of Baidu and Google to ensure breadth and quality. (For Chinese queries, keywords must be translated to English for Google).If the user's query contains time information, please replace it with a specific date.

        ## [OUTPUT_SCHEMA]
        - Return ONLY a valid JSON object
        - No explanatory text before or after JSON
        - Use exact field names as specified
        - Ensure all required fields are present

        {{
        "query_analysis": {{
            "original_query": "[Original user query]",
            "identified_intent": "[Selected intent from the classification list]",
            "assessed_complexity": "[Simple/Moderate/Complex]",
            "key_entities": ["Entity 1", "Entity 2"],
            "implicit_questions": ["Implicit question 1", "Implicit question 2"]
        }},
        "search_plan": {{
            "foundational_queries": [
            {{"query": "[Query A1]", "engine": "[Search Engine A1]"}},
            {{"query": "[Query A2]", "engine": "[Search Engine A2]"}}
            ],
        }}
        }}
        """
    # 准备历史记录：支持两种格式：
    # - 列表形式：[{'role':..., 'content':..., 'image_urls': [...]}, ...]
    # - 字典形式: {'messages': [...], 'has_images': bool}
    # 关键词提取模型只支持文本输入，若历史中有图片则过滤图片部分，只保留文本内容


    history_messages: List[Dict[str, Any]] = []
    if chat_history:
        if isinstance(chat_history, dict):
            history_messages = chat_history.get('messages', []) or []
        elif isinstance(chat_history, list):
            history_messages = chat_history

    # 从历史中抽取仅包含文本的消息（按原顺序），并限制为最近 6 条文本消息
    text_history: List[Dict[str, str]] = []
    for msg in history_messages:
        text_history.append({'role': msg['role'], 'content': msg['content']})

    # 只保留最近 6 条文本消息（从尾部取）
    if text_history:
        text_history = text_history[-6:]

    current_date = date.today().strftime("%Y-%m-%d")
    system_message = {"role": "system", "content": final_prompt.format(current_date=current_date)}

    messages = [system_message]
    # 将历史文本消息（若有）加入到消息列表
    for msg in text_history:
        messages.append({'role': msg['role'], 'content': msg['content']})

    # 最后添加用户当前查询
    # messages.append({"role": "user", "content": query})

    logger.info(f'search_stage_prompt: {json.dumps(messages,ensure_ascii=False,indent=2)}')
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    try:
        # NOTE: messages is a list of dicts compatible with the client at runtime.
        # Add type: ignore to satisfy static type checkers about the third-party client types.
        completion = client.chat.completions.create(  # type: ignore
            model=model_name,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        
        if completion.choices[0].message.content.startswith('```json'):
            json_content = completion.choices[0].message.content[len('```json'):-len('```')]
        else:
            json_content = completion.choices[0].message.content

        try:
            queries = json.loads(json_content)
            if isinstance(queries, dict) and queries:
                return queries
            else:
                logger.error(f"返回格式异常：{queries}")
                return None
        except json.JSONDecodeError:
            logger.error(f"解析响应出错：{json_content}")
            return None

    except Exception as e:
        logger.error(f"发生错误：{str(e)}")
        return None


if __name__ == "__main__":
    search_plan_data= keywords_extract("半个月后武汉天气如何")
    print(f'search_plan_data: {json.dumps(search_plan_data, ensure_ascii=False,indent=4)}')