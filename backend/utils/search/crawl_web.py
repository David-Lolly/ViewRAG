import httpx
import fitz  # PyMuPDF
from readability import Document
from bs4 import BeautifulSoup
import chardet  # 添加用于检测编码的库
from selectolax.parser import HTMLParser as SelectolaxParser
import re
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple, Any
import logging
import copy

logger = logging.getLogger(__name__)

class Crawl:

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    '   Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',

    ]
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes

    def __init__(
            self,
            max_workers: int = 10,
            max_retries: int = 3,
            timeout_config: Tuple[float, float, float, float] = (3.0, 5.0, 5.0, 5.0),
    ):
        self.MAX_WORKERS = max_workers
        self.MAX_RETRIES = max_retries
        self.TIMEOUT = httpx.Timeout(
            timeout_config[0], read=timeout_config[1], write=timeout_config[2], pool=timeout_config[3]
        )
        self.client = httpx.Client(http2=True, follow_redirects=True, timeout=self.TIMEOUT)


    def _get_random_user_agent(self) -> str:
        return random.choice(self.USER_AGENTS)

    def _clean_text(self, text: str) -> str:
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = text.replace('\t', ' ')
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        text = re.sub(r'([.,!?;:，。！？；：、])\1+', r'\1', text)
        
        return text.strip()
    
    

    def _parse_html_with_selectolax(self, response: httpx.Response, url: str) -> str:
        try:
            
            doc = Document(response.text)
            summary_html = doc.summary(html_partial=True)
            
            if not summary_html or len(summary_html) < 100:
                logger.warning(f"Readability extraction failed, using body tag for {url}")
                summary_html = response.text

            tree = SelectolaxParser(summary_html)
            tags =  ['script', 'style', 'nav', 'footer', 'header', 'aside', 'a', 'form', 'iframe', 'noscript','img', 'video', 'audio', 'figure', 'embed', 'object']
            ad_selectors = [
                '[class*="ad"]', '[class*="advertisement"]', '[class*="banner"]',
                '[class*="sidebar"]', '[class*="popup"]', '[class*="modal"]',
                '[id*="ad"]', '[id*="advertisement"]', '[id*="banner"]'
            ]
            tree.strip_tags(tags)
            for selector in ad_selectors:
                for node in tree.css(selector):
                    node.decompose()
            main_text = ""
            if tree.body:
                main_text = tree.body.text(separator=' ')
            else:
                main_text = tree.text(separator=' ')
            cleaned_text = self._clean_text(main_text)
            
            return cleaned_text
        except Exception as e:
            logger.error(f"Error parsing HTML for {url}: {e}", exc_info=True)
            return ""

    def _extract_pdf_content(self, pdf_bytes: bytes, url: str) -> str:
        try:
            full_text = []
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                for page in doc:
                    full_text.append(page.get_text()) # type: ignore
            return self._clean_text(" ".join(full_text))
        except Exception as e:
            print(f"Error extracting PDF content for {url}: {e}")
            logger.error(f"Error extracting PDF content for {url}: {e}")
            return ""

    def _fetch_one(self, web_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        link = web_info.get('link')
        query_key = web_info.get('query_key')

        if not link or not isinstance(link, str) or not link.startswith('http'):
            logger.error(f"Skipping invalid link for query '{query_key}': {link}")
            return None

        for attempt in range(self.MAX_RETRIES):
            try:
                headers = {
                    'User-Agent': self._get_random_user_agent(),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0'
                }
                response = self.client.get(link, headers=headers)
                
                if 400 <= response.status_code < 500:
                    logger.error(f"Client error {response.status_code} for {link}. Won't retry.")
                    return None
                    
                response.raise_for_status()
                if len(response.content) > self.MAX_FILE_SIZE:
                    logger.warning(f"Skipping large response ({len(response.content)/1024/1024:.1f}MB > {self.MAX_FILE_SIZE/1024/1024}MB): {link}")
                    return None
                content_type = response.headers.get('Content-Type', '').lower()
                if any(media_type in content_type for media_type in ['image/', 'audio/', 'video/', 'application/zip', 'application/x-rar', 'application/octet-stream']):
                    logger.info(f"Skipping media content {content_type}: {link}")
                    return None
                if 'pdf' in content_type or str(response.url).lower().endswith('.pdf'):
                    content = self._extract_pdf_content(response.content, str(response.url))
                elif 'text/plain' in content_type:
                    try:
                        text = response.text
                        content = self._clean_text(text)
                    except Exception as e:
                        logger.error(f"Error decoding plain text: {e}")
                        encoding = chardet.detect(response.content[:10000])['encoding']
                        if encoding:
                            text = response.content.decode(encoding, errors='replace')
                            content = self._clean_text(text)
                        else:
                            return None
                else:
                    content = self._parse_html_with_selectolax(response, str(response.url))
                if content and len(content) > 20:
                    return {
                        'id': web_info['id'],
                        'title': web_info.get('title', ''),
                        'link': link,
                        'content': content,
                        'query_key': query_key
                    }
                else:
                    logger.warning(f"Content for {link} is too short or empty after cleaning")
                    return None
                    
            except httpx.RequestError as e:
                logger.error(f"Attempt {attempt + 1}/{self.MAX_RETRIES}: Network error for {link}: {type(e).__name__}")
                if attempt < self.MAX_RETRIES - 1:
                    sleep_time = (2 ** attempt) + random.uniform(0.5, 1.0)
                    time.sleep(sleep_time)
                else:
                    logger.error(f"FAIL: Max retries reached for {link}. Error: {e}")
                    return None
            except Exception as e:
                logger.error(f"An unexpected error occurred for {link}: {e}", exc_info=True)
                return None
                
        return None

    def crawl(self, search_results: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """
        search_results: {query: [{'id': 0, 'title': 'title', 'link': 'link'}, {'id': 1, 'title': 'title', 'link': 'link'}]}
        """
        crawled_results = {query: [] for query in search_results.keys()}
        tasks = []

        for query_key, items in search_results.items():
            for item in items:
                task_item = item.copy()
                task_item['query_key'] = query_key
                tasks.append(task_item)

        with ThreadPoolExecutor(max_workers=max(1,min(self.MAX_WORKERS, len(tasks)))) as executor:
            future_to_task = {executor.submit(self._fetch_one, task): task for task in tasks}

            for future in as_completed(future_to_task):
                result = future.result()
                if result:
                    original_query = result.pop('query_key')
                    crawled_results[original_query].append(result)
        
        for query in crawled_results:
            crawled_results[query] = sorted(crawled_results[query], key=lambda x: x['id'])
        # Truncate content to first 500 characters for each crawled page
        crawled_results_copy = copy.deepcopy(crawled_results)
        for query in crawled_results_copy:
            for result in crawled_results_copy[query]:
                if 'content' in result and result['content']:
                    result['content'] = result['content'][:500]
                    if len(result['content']) >= 500:
                        result['content'] += '...'
        logger.info(f'crawled_results: {json.dumps(crawled_results_copy,ensure_ascii=False,indent=2)}')

        return crawled_results

    def close(self):
        self.client.close()

if __name__ == '__main__':
    sample_search_data = {
        "武汉天气预报": [
            {
                "id": 0, "title": "武汉天气预报15天", "link": "https://www.weather.com.cn/weather15d/101200101.shtml"
            },
            {
                "id": 1, "title": "武汉天气-中国天气网", "link": "http://www.weather.com.cn/weather/101200101.shtml"
            },
            {
                "id": 2, "title": "Invalid link test", "link": "/some/relative/path"
            }
        ],
        "python tutorial": [
            {
                "id": 0, "title": "Python Tutorial - W3Schools", "link": "https://www.w3schools.com/python/"
            },
            {
                "id": 1, "title": "The Python Tutorial — Python 3.12.4 documentation", "link": "https://docs.python.org/3/tutorial/"
            },
            {
                "id": 2, "title": "Python For Beginners", "link": "https://www.python.org/about/gettingstarted/"
            },
            {
                "id": 3, "title": "Real Python: Python Tutorials", "link": "https://realpython.com/"
            },
            {
                "id": 4, "title": "Learn Python - Free Interactive Course", "link": "https://www.python-httpx.org/quickstart/"
            },
            {
                "id": 5, "title": "Python HTTPX Documentation", "link": "https://www.weather.com.cn/weather/101200101.shtml"
            }
        ]
    }

    crawler = Crawl(max_workers=10)
    
    start_time = time.time()
    final_results = crawler.crawl(sample_search_data)
    end_time = time.time()
    
    crawler.close()
    print(json.dumps(final_results, ensure_ascii=False, indent=4))
    
    print(f"\nCrawling complete.")
    print(f"Total time taken: {end_time - start_time:.2f} seconds.")
