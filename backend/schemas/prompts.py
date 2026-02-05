""""Prompt templates for different types of content analysis."""

from typing import Dict, Optional


PROMPTS: Dict[str, str] = {
    "image_prompt": """You are a professional analyst tasked with analyzing images for a knowledge base.

        **FIRST**, determine if this image contains meaningful information for knowledge retrieval:
        
        **SKIP these types of images** (respond with "[SKIP] reason"):
        - Portrait photos (headshots, author photos, speaker photos)
        - Decorative images (backgrounds, dividers, logos, icons)
        - Scenery/landscape photos without informational content
        - Stock photos or generic illustrations
        
        **ANALYZE these types of images** (provide full analysis):
        - Charts, graphs, diagrams
        - Flowcharts, architecture diagrams
        - Tables, data visualizations
        - Infographics with data or processes
        - Screenshots with meaningful content
        - Technical illustrations
        
        **If the image should be SKIPPED**, respond ONLY with:
        [SKIP] Brief reason (e.g., "[SKIP] Portrait photo of author")
        
        **If the image should be ANALYZED**, provide a Chinese summary following this structure:
        
        Topic: A concise title that captures the main subject of the image.
        Key Points:
            The first major point, finding, or piece of evidence.
            The second major point, finding, or piece of evidence.
            ... (Continue for all significant points)
        Conclusion: A one-sentence summary of the image's main conclusion or the key message the audience should remember.

        **Instructions for analysis**:
        - Be direct and factual.
        - Extract all important text, numbers, and concepts.
        - Do not comment on the image's design, layout, or aesthetics.""",

    "table_prompt": """You are a professional analyst tasked with summarizing a presentation table for a knowledge base. Your summary must be in Chinese and structured to be easily searchable and understandable.

        Please analyze the provided table and generate a summary following this exact structure:

        Topic: A concise title that captures the main subject of the table.
        Key Points:
            The first major point, finding, or piece of evidence.
            The second major point, finding, or piece of evidence.
            ... (Continue for all significant points)
        Conclusion: A one-sentence summary of the table's main conclusion or the key message the audience should remember.

        Instructions:
        - Be direct and factual.
        - Extract all important text, numbers, and concepts.""",

    "slide_prompt": """You are a professional analyst tasked with summarizing a presentation slide for a knowledge base. Your summary must be in Chinese and structured to be easily searchable and understandable.

        Please analyze the provided slide and generate a summary following this exact structure:

        Topic: A concise title that captures the main subject of the slide.
        Key Points:
            The first major point, finding, or piece of evidence.
            The second major point, finding, or piece of evidence.
            ... (Continue for all significant points)
        Conclusion: A one-sentence summary of the slide's main conclusion or the key message the audience should remember.

        Instructions:
        - Be direct and factual.
        - Extract all important text, numbers, and concepts.
        - Do not comment on the slide's design, layout, or aesthetics."""
}


def get_prompt(name: str) -> Optional[str]:
    """获取指定名称的提示词内容，若不存在返回 None"""
    return PROMPTS.get(name)



