<script setup>
import { computed, ref, watch, onMounted, nextTick } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js'
import katex from 'katex'
import 'highlight.js/styles/github.css'
import 'katex/dist/katex.min.css'

marked.setOptions({
  breaks: true,
  gfm: true,
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  },
})

const props = defineProps({
  content: { type: String, default: '' },
})

// 允许 KaTeX 生成的标签通过 DOMPurify
DOMPurify.addHook('uponSanitizeElement', (node, data) => {
  if (data.tagName && /^(math|semantics|mrow|mi|mo|mn|mtext|mspace|mstyle|merror|mpadded|mphantom|mfrac|msqrt|mroot|mtable|mtr|mtd|malign|maligngroup|malignmark|maction|menclose|mover|munder|msub|msup|msubsup|mmultiscripts|mprescripts|none|munderover|annotation|annotation-xml)$/i.test(data.tagName)) {
    node.setAttribute('xmlns', 'http://www.w3.org/1998/Math/MathML')
  }
})

const container = ref(null)

function injectCopyButtons() {
  if (!container.value) return
  container.value.querySelectorAll('pre').forEach((pre) => {
    if (pre.querySelector('.copy-btn')) return
    const btn = document.createElement('button')
    btn.className = 'copy-btn'
    btn.textContent = '复制'
    btn.onclick = () => {
      const code = pre.querySelector('code')?.textContent || pre.textContent || ''
      navigator.clipboard.writeText(code).then(() => {
        btn.textContent = '已复制'
        setTimeout(() => { btn.textContent = '复制' }, 1500)
      }).catch(() => {
        // fallback
        const ta = document.createElement('textarea')
        ta.value = code; ta.style.position = 'fixed'; ta.style.opacity = '0'
        document.body.appendChild(ta); ta.select()
        document.execCommand('copy'); document.body.removeChild(ta)
        btn.textContent = '已复制'
        setTimeout(() => { btn.textContent = '复制' }, 1500)
      })
    }
    pre.style.position = 'relative'
    pre.appendChild(btn)
  })
}

const html = computed(() => {
  if (!props.content) return ''
  const text = String(props.content)

  // 保护 code 块中的 $ 不被当作公式
  const codeBlocks = []
  const safe = text
    .replace(/```[\s\S]*?```/g, (m) => { codeBlocks.push(m); return `\x00CODE${codeBlocks.length - 1}\x00` })
    .replace(/`[^`]+`/g, (m) => { codeBlocks.push(m); return `\x00CODE${codeBlocks.length - 1}\x00` })

  // 提取 Latex：先 $$...$$ 再 $...$
  const mathBlocks = []
  let processed = safe
    .replace(/\$\$([\s\S]*?)\$\$/g, (_, formula) => {
      mathBlocks.push({ type: 'display', formula })
      return `\x00MATH${mathBlocks.length - 1}\x00`
    })
    .replace(/\$(.+?)\$/g, (_, formula) => {
      mathBlocks.push({ type: 'inline', formula })
      return `\x00MATH${mathBlocks.length - 1}\x00`
    })

  // 恢复 code 块
  processed = processed.replace(/\x00CODE(\d+)\x00/g, (_, i) => codeBlocks[+i])

  // Markdown → HTML
  let raw = marked.parse(processed)

  // 恢复 Latex 公式
  raw = raw.replace(/\x00MATH(\d+)\x00/g, (_, i) => {
    const { type, formula } = mathBlocks[+i]
    try {
      return katex.renderToString(formula, {
        displayMode: type === 'display',
        throwOnError: false,
      })
    } catch {
      return `<code>${formula}</code>`
    }
  })

  return DOMPurify.sanitize(raw)
})

onMounted(() => injectCopyButtons())
watch(html, () => nextTick(() => setTimeout(injectCopyButtons, 0)))
</script>

<template>
  <div ref="container" class="markdown-body" v-html="html"></div>
</template>

<style>
.markdown-body {
  font-size: 15px; line-height: 1.75; color: var(--gray-800);
}
.markdown-body h1 { font-size: 1.6em; margin: 1.2em 0 .6em; border-bottom: 2px solid var(--gray-200); padding-bottom: .3em; }
.markdown-body h2 { font-size: 1.35em; margin: 1.1em 0 .5em; border-bottom: 1px solid var(--gray-200); padding-bottom: .2em; }
.markdown-body h3 { font-size: 1.15em; margin: 1em 0 .4em; }
.markdown-body p { margin: .6em 0; }
.markdown-body ul, .markdown-body ol { padding-left: 2em; margin: .5em 0; }
.markdown-body li { margin: .2em 0; }
.markdown-body code {
  background: var(--gray-100); padding: 2px 6px; border-radius: 4px;
  font-size: .9em; font-family: 'Fira Code', 'Cascadia Code', Consolas, monospace;
}
.markdown-body pre {
  background: #f6f8fa; border: 1px solid var(--gray-200);
  border-radius: var(--radius); padding: 16px; overflow-x: auto; margin: .8em 0;
}
.markdown-body pre code { background: none; padding: 0; font-size: 13px; line-height: 1.5; }
.markdown-body table { border-collapse: collapse; margin: .8em 0; }
.markdown-body th, .markdown-body td { border: 1px solid var(--gray-300); padding: 8px 12px; }
.markdown-body th { background: var(--gray-100); }
.markdown-body img { max-width: 100%; border-radius: var(--radius); }
.markdown-body blockquote {
  border-left: 4px solid var(--primary); padding: 4px 16px; margin: .8em 0;
  color: var(--gray-600); background: var(--primary-light);
  border-radius: 0 var(--radius) var(--radius) 0;
}
.markdown-body hr { border: none; border-top: 1px solid var(--gray-200); margin: 1.2em 0; }

/* KaTeX tweaks */
.markdown-body .katex { font-size: 1.05em; }
.markdown-body .katex-display { margin: .8em 0; overflow-x: auto; }

/* Copy button */
.markdown-body .copy-btn {
  position: absolute; top: 6px; right: 8px;
  padding: 2px 10px; font-size: 12px; font-family: inherit;
  background: var(--gray-100); color: var(--gray-600);
  border: 1px solid var(--gray-300); border-radius: 4px;
  cursor: pointer;
}
.markdown-body .copy-btn:hover { background: var(--gray-200); color: var(--gray-800); }
</style>