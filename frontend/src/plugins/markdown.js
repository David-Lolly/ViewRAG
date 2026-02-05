// vue-renderer-markdown 全局配置
import { setCustomComponents, MarkdownCodeBlockNode } from 'vue-renderer-markdown';

let configured = false;

export function setupMarkdownRenderer() {
  if (configured) return;
  
  try {
    // 配置使用 Shiki 高亮的代码块组件
    setCustomComponents({
      code_block: MarkdownCodeBlockNode,
    });
    
    console.log('[Markdown] vue-renderer-markdown configured with Shiki');
    configured = true;
  } catch (error) {
    console.error('[Markdown] Failed to configure vue-renderer-markdown:', error);
  }
}
