import { marked } from 'marked'
import katex from 'katex'
import DOMPurify from 'dompurify'
import type { RendererObject, Renderer } from 'marked'

// 默认的 Markdown 渲染配置
const defaultOptions = {
  breaks: true, // 允许换行
  gfm: true,    // 启用 GitHub 风格的 Markdown
  headerIds: true, // 为标题添加 id
  mangle: false,   // 不转义标题中的 HTML
  // 注意: 已移除 sanitize: false，由 DOMPurify 负责 XSS 净化
}

/**
 * DOMPurify 白名单配置
 * 允许 KaTeX 渲染所需的标签和属性，同时阻止危险内容
 */
const DOMPURIFY_CONFIG = {
  ALLOWED_TAGS: [
    // 基础 HTML 标签
    'p', 'br', 'hr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'blockquote', 'pre', 'code',
    'a', 'img', 'strong', 'em', 'del', 's', 'sub', 'sup',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'div', 'span',
    // KaTeX 渲染所需标签
    'math', 'semantics', 'mrow', 'mi', 'mo', 'mn', 'msup', 'msub',
    'mfrac', 'munderover', 'msqrt', 'mroot', 'mtext', 'mspace',
    'annotation', 'mtable', 'mtr', 'mtd',
  ],
  ALLOWED_ATTR: [
    'class', 'id', 'style', 'href', 'target', 'rel',
    'src', 'alt', 'width', 'height', 'title',
    'colspan', 'rowspan', 'align',
    // KaTeX 所需属性
    'xmlns', 'encoding', 'mathvariant', 'stretchy', 'fence',
    'separator', 'lspace', 'rspace', 'accent', 'accentunder',
    'displaystyle', 'scriptlevel', 'columnalign',
  ],
  // 禁止 javascript: 协议等危险 URI
  ALLOW_DATA_ATTR: false,
  // 允许 data:image 用于内联图片展示
  ADD_DATA_URI_TAGS: ['img'],
}

/**
 * HTML 特殊字符转义，防止 XSS 注入
 * @param str 需要转义的字符串
 * @returns 转义后的安全字符串
 */
function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
}

/**
 * 清理图片 src 路径，防止路径遍历攻击
 * - 过滤 .. 路径遍历
 * - 过滤绝对路径（以 / 或盘符开头）
 * - 允许 http(s):// 和 data:image/ 前缀
 * @param src 原始图片路径
 * @returns 清理后的安全路径，不安全时返回空字符串
 */
function sanitizeImageSrc(src: string): string {
  const trimmed = src.trim()

  // 允许 http(s) 协议的绝对 URL
  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed
  }

  // 允许 data:image/ 内联图片（base64 编码）
  if (/^data:image\//i.test(trimmed)) {
    return trimmed
  }

  // 阻止路径遍历: 包含 .. 的路径
  if (/\.\./.test(trimmed)) {
    return ''
  }

  // 阻止绝对路径: 以 / 开头或 Windows 盘符（如 C:\）
  if (/^\//.test(trimmed) || /^[a-zA-Z]:/.test(trimmed)) {
    return ''
  }

  // 阻止危险协议: javascript:, vbscript:, file: 等
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(trimmed)) {
    return ''
  }

  // 相对路径，允许通过
  return trimmed
}

// 当前任务 ID，用于图片路径拼接
let currentTaskId = ''

/**
 * 设置当前任务 ID，供图片路径预处理使用
 * 应在进入任务详情页时调用，避免依赖 localStorage
 * @param taskId 任务 ID
 */
export function setCurrentTaskId(taskId: string): void {
  currentTaskId = taskId
}

// 处理数学公式
const renderMath = (tex: string, displayMode = false) => {
  try {
    return katex.renderToString(tex, {
      displayMode: displayMode,
      throwOnError: false,
      strict: false
    })
  } catch (err) {
    if (import.meta.env.DEV) {
      console.error('KaTeX rendering error:', err)
    }
    return escapeHtml(tex)
  }
}

// 创建自定义渲染器
const renderer: Partial<RendererObject> = {
  paragraph(this: Renderer, token: { text: string }) {
    let text = token.text

    // 先处理图片链接，避免被误识别为数学公式
    const imagePattern = /!\[(.*?)\]\((.*?)\)/g
    const images: Array<[string, string, string]> = []
    let imageIndex = 0
    text = text.replace(imagePattern, (match, alt, src) => {
      images.push([match, alt, src])
      return `__IMAGE_PLACEHOLDER_${imageIndex++}__`
    })

    // 处理块级公式（使用 \[...\] 包裹）
    text = text.replace(/\\\[([\s\S]*?)\\\]/g, (_, tex) => {
      return `<div class="math-block">${renderMath(tex.trim(), true)}</div>`
    })

    // 处理块级公式（使用 $$ 包裹）
    const blockMathPattern = /\$\$([\s\S]*?)\$\$/g
    text = text.replace(blockMathPattern, (_, tex) => {
      return `<div class="math-block">${renderMath(tex.trim(), true)}</div>`
    })

    // 处理行内公式（使用 \( \) 包裹）
    text = text.replace(/\\\((.*?)\\\)/g, (_, tex) => renderMath(tex.trim(), false))

    // 还原图片占位符，对 alt 和 src 进行安全处理
    text = text.replace(/__IMAGE_PLACEHOLDER_(\d+)__/g, (_, index) => {
      const [, alt, src] = images[parseInt(index)]
      // alt 属性进行 HTML 转义防止 XSS
      const safeAlt = escapeHtml(alt)
      // src 路径进行清理防止路径遍历
      const safeSrc = sanitizeImageSrc(src)
      if (!safeSrc) {
        // 不安全的路径，不渲染图片
        return `<span class="text-muted-foreground">[图片路径不安全: ${safeAlt}]</span>`
      }
      return `<img src="${safeSrc}" alt="${safeAlt}" class="max-w-full h-auto" />`
    })

    return `<p>${text}</p>`
  }
}

// 配置 marked
marked.use({ renderer })

// 配置图片处理：将相对路径的图片转换为 API 静态资源路径
marked.use({
  hooks: {
    preprocess(markdown) {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
      // 优先使用模块级变量，回退到 localStorage（兼容旧逻辑）
      const taskId = currentTaskId || window.localStorage.getItem('currentTaskId') || ''

      return markdown.replace(
        /!\[(.*?)\]\(((?!http[s]?:\/\/).*?\.(?:png|jpg|jpeg|gif|bmp|webp))\)/g,
        (_, alt, src) => {
          // 对相对路径进行安全检查
          const safeSrc = sanitizeImageSrc(src)
          if (!safeSrc) return `![${alt}]()`
          return `![${alt}](${baseUrl}/static/${taskId}/${safeSrc})`
        }
      )
    }
  }
})

/**
 * 渲染 Markdown 文本为安全的 HTML
 * 所有输出均经过 DOMPurify 净化，防止 XSS 攻击
 * @param content Markdown 文本
 * @param options 可选的 marked 配置项
 * @returns 净化后的安全 HTML
 */
export const renderMarkdown = async (content: string, options = {}) => {
  // 预处理内容，确保数学公式正确换行
  content = content.replace(/\\\[\s*\n/g, '\\[')
    .replace(/\n\s*\\\]/g, '\\]')
  const rawHtml = await marked.parse(content, { ...defaultOptions, ...options })
  // 使用 DOMPurify 净化 HTML 输出，防止 XSS
  return DOMPurify.sanitize(rawHtml, DOMPURIFY_CONFIG)
}

/**
 * 净化任意 HTML 字符串（用于非 Markdown 的 HTML 内容）
 * 适用于后端返回的 HTML 结果、代码执行输出等场景
 * @param html 需要净化的 HTML 字符串
 * @returns 净化后的安全 HTML
 */
export const sanitizeHtml = (html: string): string => {
  return DOMPurify.sanitize(html, DOMPURIFY_CONFIG)
}

/**
 * 计算 Markdown 文本的行数
 * @param content Markdown 文本
 * @returns 行数
 */
export const getMarkdownLines = (content: string) => {
  return content.split('\n').length
}

// 导出 marked 以备需要直接使用
export { marked }
