<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

const props = defineProps({
  modelValue: { type: String, default: '' },
  language: { type: String, default: 'cpp' },  // cpp | python3
  tabSize: { type: Number, default: 4 },
})

const emit = defineEmits(['update:modelValue'])

const textarea = ref(null)
const preEl = ref(null)
const showTabSetting = ref(false)
const localTabSize = ref(props.tabSize)

const langMap = { cpp: 'cpp', python3: 'python' }
const hlLang = computed(() => langMap[props.language] || 'cpp')

const highlighted = computed(() => {
  const code = props.modelValue || ''
  if (!code.trim()) return '<span style="opacity:.4">// 在此编写代码...</span>'
  try {
    const result = hljs.highlight(code, { language: hlLang.value })
    return result.value
  } catch {
    return code.replace(/</g, '&lt;').replace(/>/g, '&gt;')
  }
})

function syncScroll() {
  if (preEl.value && textarea.value) {
    preEl.value.scrollTop = textarea.value.parentElement.scrollTop
    preEl.value.scrollLeft = textarea.value.parentElement.scrollLeft
  }
}

function emitValue(val) {
  emit('update:modelValue', val)
}

// ---- 自动配对 ----
const PAIRS = { '(': ')', '[': ']', '{': '}', '"': '"', "'": "'" }

// 使用 setRangeText 插入文本（纳入浏览器原生撤销栈）
function insert(ta, text, cursorOffset) {
  ta.focus()
  ta.setRangeText(text, ta.selectionStart, ta.selectionEnd, 'end')
  if (cursorOffset != null) {
    const pos = ta.selectionStart + cursorOffset
    ta.selectionStart = ta.selectionEnd = pos
  }
  ta.dispatchEvent(new Event('input', { bubbles: true }))
}

function handleKeydown(e) {
  const ta = textarea.value
  if (!ta) return

  const { selectionStart, selectionEnd, value } = ta
  const tab = ' '.repeat(localTabSize.value)

  // Tab → 插入空格
  if (e.key === 'Tab' && !e.shiftKey) {
    e.preventDefault()
    insert(ta, tab, 0)
    return
  }

  // Shift+Tab → 当前行减少缩进
  if (e.key === 'Tab' && e.shiftKey) {
    e.preventDefault()
    const lineStart = value.lastIndexOf('\n', selectionStart - 1) + 1
    const lineEnd = value.indexOf('\n', selectionStart)
    const end = lineEnd === -1 ? value.length : lineEnd
    const currentLine = value.slice(lineStart, end)
    const leadingSpaces = currentLine.match(/^(\s*)/)[1]
    const removeCount = Math.min(leadingSpaces.length, localTabSize.value)
    if (removeCount > 0) {
      ta.setSelectionRange(lineStart, lineStart + removeCount)
      insert(ta, '', 0)
      // 光标跟随回退
      const newPos = selectionStart - removeCount
      if (newPos >= lineStart) ta.selectionStart = ta.selectionEnd = newPos
    }
    return
  }

  // Enter → 保持缩进 + 大括号展开（VS Code 风格）
  if (e.key === 'Enter') {
    e.preventDefault()
    const before = value.slice(0, selectionStart)
    const after = value.slice(selectionEnd)
    const lineStart = before.lastIndexOf('\n') + 1
    const currentLine = before.slice(lineStart)
    const indent = currentLine.match(/^(\s*)/)[1]
    const trimmed = currentLine.trimEnd()

    // {|} 场景：{ 行尾 + } 紧随光标 → 展开为三行，光标在中间行
    if (trimmed.endsWith('{') && after.startsWith('}')) {
      ta.setSelectionRange(selectionStart, selectionStart + 1) // 选中 }
      insert(ta, '\n' + indent + tab + '\n' + indent + '}', 0)
      // 光标回到中间行
      const pos = selectionStart + 1 + indent.length + tab.length
      nextTick(() => { ta.selectionStart = ta.selectionEnd = pos })
      return
    }

    // 普通换行
    const extra = trimmed.endsWith('{') ? tab : ''
    insert(ta, '\n' + indent + extra, 0)
    return
  }

  // 自动配对: 输入左括号/引号时补全右侧
  const char = e.key
  if (PAIRS[char]) {
    // 有选中文本 → 包裹选中内容
    if (selectionStart !== selectionEnd) {
      e.preventDefault()
      const selected = value.slice(selectionStart, selectionEnd)
      insert(ta, char + selected + PAIRS[char], -selected.length - 1)
      return
    }
    // 右侧已有相同括号（非引号）→ 仅移动光标跳过
    const nextChar = value[selectionStart]
    if (char === nextChar && char !== '"' && char !== "'") {
      e.preventDefault()
      ta.selectionStart = ta.selectionEnd = selectionStart + 1
      return
    }
    // 插入配对符号，光标留在中间
    e.preventDefault()
    insert(ta, char + PAIRS[char], -1)
    return
  }

  // Backspace → 成对删除配对符号
  if (e.key === 'Backspace') {
    const prev = value[selectionStart - 1]
    const next = value[selectionStart]
    if (PAIRS[prev] && PAIRS[prev] === next) {
      e.preventDefault()
      ta.setSelectionRange(selectionStart - 1, selectionStart + 1)
      insert(ta, '', 0)
      return
    }
  }
}

function handleInput(e) {
  emitValue(e.target.value)
  autoHeight(e.target)
}

function autoHeight(ta) {
  ta.style.height = 'auto'
  ta.style.height = Math.max(ta.scrollHeight, 320) + 'px'
}

function changeTabSize(size) {
  localTabSize.value = size
  showTabSetting.value = false
}

onMounted(() => {
  if (props.language === 'cpp') {
    localTabSize.value = props.tabSize
  }
  nextTick(() => {
    if (textarea.value) autoHeight(textarea.value)
  })
})
</script>

<template>
  <div class="code-editor-wrap">
    <!-- 语言标签 + 缩进设置 -->
    <div class="ce-toolbar">
      <span class="ce-lang-tag">{{ language === 'cpp' ? 'C++' : 'Python 3' }}</span>
      <span v-if="language === 'cpp'" class="ce-tab-settings">
        <button class="ce-tab-btn" @click="showTabSetting = !showTabSetting"
          title="缩进格数">Tab: {{ localTabSize }}</button>
        <div v-if="showTabSetting" class="ce-tab-dropdown">
          <button v-for="n in [2,4,8]" :key="n"
            :class="{ active: localTabSize === n }"
            @click="changeTabSize(n)">{{ n }} 格</button>
        </div>
      </span>
    </div>
    <!-- 编辑区 -->
    <div class="ce-body" @scroll="syncScroll">
      <pre ref="preEl" class="ce-highlight" aria-hidden="true"><code v-html="highlighted"></code></pre>
      <textarea
        ref="textarea"
        class="ce-textarea"
        :value="modelValue"
        spellcheck="false"
        @input="handleInput"
        @keydown="handleKeydown"
        @scroll="syncScroll"
      ></textarea>
    </div>
  </div>
</template>

<style scoped>
.code-editor-wrap {
  border: 1px solid var(--gray-300);
  border-radius: var(--radius);
  overflow: hidden;
  background: #f6f8fa;
}
.ce-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 10px;
  background: #e8eaed;
  border-bottom: 1px solid var(--gray-300);
}
.ce-lang-tag {
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-600);
  text-transform: uppercase;
}
.ce-tab-settings {
  position: relative;
}
.ce-tab-btn {
  font-size: 11px;
  background: #fff;
  border: 1px solid var(--gray-300);
  border-radius: 3px;
  padding: 1px 8px;
  cursor: pointer;
  color: var(--gray-600);
}
.ce-tab-btn:hover { background: var(--gray-100); }
.ce-tab-dropdown {
  position: absolute;
  right: 0;
  top: 100%;
  margin-top: 2px;
  background: #fff;
  border: 1px solid var(--gray-300);
  border-radius: 4px;
  box-shadow: var(--shadow-md);
  z-index: 10;
  display: flex;
  flex-direction: column;
}
.ce-tab-dropdown button {
  border: none;
  background: none;
  padding: 4px 16px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  text-align: left;
}
.ce-tab-dropdown button:hover { background: var(--primary-light); color: var(--primary); }
.ce-tab-dropdown button.active { background: var(--primary-light); color: var(--primary); font-weight: 600; }
.ce-body {
  position: relative;
  min-height: 320px;
  max-height: 520px;
  overflow: auto;
}
.ce-highlight,
.ce-textarea {
  font-family: 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.55;
  tab-size: 4;
  padding: 14px 16px;
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-wrap: break-word;
}
.ce-highlight {
  position: absolute;
  inset: 0;
  pointer-events: none;
  color: #24292e;
  background: transparent;
}
.ce-highlight :deep(code) {
  font-family: inherit;
  font-size: inherit;
  line-height: inherit;
}
.ce-textarea {
  position: relative;
  z-index: 1;
  width: 100%;
  min-height: 320px;
  border: none;
  outline: none;
  resize: none;
  overflow: hidden;
  color: transparent;
  caret-color: #24292e;
  background: transparent;
}
.ce-textarea::selection {
  background: rgba(79,70,229,.2);
}
</style>
