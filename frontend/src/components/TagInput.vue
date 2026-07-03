<script setup>
import { ref, watchEffect, watch } from 'vue'
import { tagsApi } from '../api/tags'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue'])

const input = ref('')
const tags = ref([])
const tip = ref('')
const suggestions = ref([])
const showDropdown = ref(false)
const selIdx = ref(-1)
let suppressWatch = false

watch(input, async (val) => {
  if (suppressWatch) { suppressWatch = false; return }
  selIdx.value = -1
  if (!val.trim()) { suggestions.value = []; showDropdown.value = false; return }
  try {
    const res = await tagsApi.getList({ keyword: val.trim() })
    if (res.code === 0) {
      // 过滤已选标签，最多 5 条
      suggestions.value = (res.data || [])
        .map(t => t.tag_name)
        .filter(n => !tags.value.includes(n))
        .slice(0, 5)
      showDropdown.value = suggestions.value.length > 0
    }
  } catch { /* ignore */ }
})

watchEffect(() => {
  const v = props.modelValue
  if (v && (v.length !== tags.value.length || v.some((t, i) => t !== tags.value[i]))) {
    tags.value = [...v]
  }
})

function showTip(msg) { tip.value = msg }

function sync() {
  emit('update:modelValue', [...tags.value])
}

function addTag(name) {
  const n = (name || input.value).trim()
  if (!n) return
  if (n.length > 12) { showTip('标签长度不能超过 12 个字符'); return }
  if (tags.value.length >= 6) { showTip('最多只能设置 6 个标签'); return }
  if (tags.value.includes(n)) return
  tags.value = [...tags.value, n]
  input.value = ''
  suggestions.value = []
  showDropdown.value = false
  sync()
}

function removeTag(name) {
  tags.value = tags.value.filter(t => t !== name)
  sync()
}

function onKeydown(e) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    selIdx.value = Math.min(selIdx.value + 1, suggestions.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    selIdx.value = Math.max(selIdx.value - 1, -1)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (selIdx.value >= 0 && suggestions.value[selIdx.value]) {
      suppressWatch = true
      input.value = suggestions.value[selIdx.value]
      showDropdown.value = false
    } else {
      addTag()
    }
  } else if (e.key === 'Escape') {
    showDropdown.value = false
  }
}
</script>

<template>
  <div class="tag-input-row">
    <div class="flex gap-1" style="align-items:flex-start">
      <div style="position:relative;flex:1;max-width:260px">
        <input
          v-model="input"
          class="form-input"
          placeholder="输入标签名，最多12字，限6个"
          maxlength="12"
          style="width:100%"
          @keydown="onKeydown"
          @focus="input && suggestions.length && (showDropdown = true)"
          @blur="showDropdown = false"
        />
        <div v-if="showDropdown" class="tag-dropdown">
          <div
            v-for="(s, i) in suggestions"
            :key="s"
            class="tag-suggestion"
            :class="{ active: i === selIdx }"
            @mousedown.prevent="suppressWatch = true; input = s; showDropdown = false"
          >{{ s }}</div>
        </div>
      </div>
      <button class="btn btn-outline btn-sm" @click="addTag()">添加</button>
    </div>
    <div v-if="tags.length" class="tag-list mt-1">
      <span v-for="t in tags" :key="t" class="tag-item">
        {{ t }}
        <button class="tag-remove" @click="removeTag(t)">×</button>
      </span>
    </div>

    <!-- 提示弹窗 -->
    <div v-if="tip" class="tip-overlay" @click.self="tip = ''">
      <div class="tip-card">
        <p class="mb-2">{{ tip }}</p>
        <button class="btn btn-primary btn-sm" @click="tip = ''">确定</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tag-list { display: flex; flex-wrap: wrap; gap: 6px; }
.tag-item {
  display: inline-flex; align-items: center; gap: 2px;
  background: var(--primary-light); color: var(--primary);
  padding: 3px 10px; border-radius: 4px; font-size: 13px; font-weight: 500;
}
.tag-remove {
  background: none; border: none; cursor: pointer;
  font-size: 15px; color: var(--primary); padding: 0 2px; line-height: 1;
}
.tag-remove:hover { color: var(--danger); }
.tag-dropdown {
  position: absolute; top: 100%; left: 0; right: 0;
  background: #fff; border: 1px solid var(--gray-200);
  border-radius: var(--radius); box-shadow: var(--shadow-md);
  z-index: 50; max-height: 180px; overflow-y: auto;
}
.tag-suggestion {
  padding: 6px 10px; font-size: 14px; cursor: pointer;
}
.tag-suggestion:hover, .tag-suggestion.active { background: var(--primary-light); color: var(--primary); }
.tip-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.3);
  display: flex; align-items: center; justify-content: center; z-index: 300;
}
.tip-card {
  background: #fff; border-radius: var(--radius); padding: 24px;
  width: 320px; text-align: center; box-shadow: var(--shadow-md);
}
</style>