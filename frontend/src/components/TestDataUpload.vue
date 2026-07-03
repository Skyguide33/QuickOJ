<script setup>
import { ref } from 'vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  existingPairs: { type: Array, default: () => [] },
  problemType: { type: String, default: 'traditional' },
})

const emit = defineEmits(['update:modelValue', 'update:excludedRoots'])

const fileInput = ref(null)
const pairs = ref([])          // 新上传: [{ root, inFile?, outFile? }]
const excludedRoots = ref([])  // 标记排除的已有样例

function triggerUpload() { fileInput.value?.click() }

function handleFiles(e) {
  const files = Array.from(e.target.files || [])
  const inMap = {}, outMap = {}
  for (const f of files) {
    const name = f.name
    const dot = name.lastIndexOf('.')
    if (dot <= 0 || dot > 3) continue
    const root = name.substring(0, dot)
    const ext = name.substring(dot).toLowerCase()
    if (ext === '.in') inMap[root] = f
    else if (ext === '.out' || ext === '.ans') outMap[root] = f
  }
  const newPairs = []
  if (props.problemType === 'traditional') {
    for (const root of Object.keys(inMap)) {
      if (outMap[root]) {
        const idx = pairs.value.findIndex(p => p.root === root)
        if (idx >= 0) pairs.value.splice(idx, 1)
        newPairs.push({ root, inFile: inMap[root], outFile: outMap[root] })
      }
    }
  } else {
    for (const root of Object.keys(outMap)) {
      const idx = pairs.value.findIndex(p => p.root === root)
      if (idx >= 0) pairs.value.splice(idx, 1)
      newPairs.push({ root, outFile: outMap[root] })
    }
  }
  pairs.value = [...pairs.value, ...newPairs].slice(0, 120)
  syncAll()
}

function removeNew(root) {
  pairs.value = pairs.value.filter(p => p.root !== root)
  syncAll()
}

function toggleExclude(root) {
  const i = excludedRoots.value.indexOf(root)
  if (i >= 0) excludedRoots.value.splice(i, 1)
  else excludedRoots.value.push(root)
  syncAll()
}

function syncAll() {
  const files = []
  for (const p of pairs.value) {
    if (p.inFile) files.push(p.inFile)
    if (p.outFile) files.push(p.outFile)
  }
  emit('update:modelValue', files)
  emit('update:excludedRoots', [...excludedRoots.value])
}
</script>

<template>
  <div class="testdata-upload">
    <div class="flex gap-1 mb-1" style="align-items:center">
      <button class="btn btn-outline btn-sm" @click="triggerUpload">上传样例数据</button>
      <span class="text-sm text-muted">
        {{ problemType === 'traditional' ? '.in/.out 成对上传' : '.out 文件' }}
        · 文件名 ≤3 字符 · 最多 120 组
      </span>
      <input ref="fileInput" type="file" accept=".in,.out,.ans" multiple
        style="position:fixed;left:-9999px" @change="handleFiles($event)" />
    </div>

    <!-- 已有样例（problems/ 中的） -->
    <div v-if="existingPairs.length" class="mb-1">
      <span class="text-sm text-muted">已有：</span>
      <span v-for="r in existingPairs" :key="'e'+r"
        class="test-chip" :class="{ excluded: excludedRoots.includes(r) }"
        @click="toggleExclude(r)"
        :title="excludedRoots.includes(r) ? '点击恢复' : '点击排除'"
      >
        {{ r }}
        <span class="chip-mark">{{ excludedRoots.includes(r) ? '⊘' : '×' }}</span>
      </span>
    </div>

    <!-- 新上传样例 -->
    <div v-if="pairs.length" class="mb-1">
      <span class="text-sm text-muted">新上传：</span>
      <span v-for="p in pairs" :key="p.root" class="test-chip new">
        {{ p.root }}
        <button class="chip-del" @click="removeNew(p.root)">×</button>
      </span>
    </div>
  </div>
</template>

<style scoped>
.test-chip {
  display: inline-flex; align-items: center; gap: 2px;
  background: #dcfce7; color: #166534;
  padding: 2px 8px; border-radius: 4px; font-size: 13px; font-weight: 500;
  margin: 2px; cursor: pointer;
}
.test-chip.excluded {
  background: #fee2e2; color: #991b1b; text-decoration: line-through;
}
.test-chip.new { background: #fef9c3; color: #854d0e; cursor: default; }
.chip-mark { font-size: 11px; margin-left: 2px; }
.chip-del {
  background: none; border: none; cursor: pointer;
  font-size: 14px; color: inherit; padding: 0 2px; line-height: 1;
}
.chip-del:hover { opacity: .7; }
</style>