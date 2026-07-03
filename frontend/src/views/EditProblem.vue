<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TagInput from '../components/TagInput.vue'
import TestDataUpload from '../components/TestDataUpload.vue'
import { problemsApi } from '../api/problems'

const route = useRoute()
const router = useRouter()

const fetchId = route.params.identifier
let numericId = null
const backId = ref('')
const loading = ref(true)
const errorMsg = ref('')
const msg = ref(null)
const saving = ref(false)

const form = ref({
  problem_name: '',
  statement: '',
  difficulty: 1000,
  time_limit: 1000,
  memory_limit: 256,  // MB，提交时转为 KB
  sample_download_policy: 'none',
  source: '',
  tags: [],
})

const testDataFiles = ref([])
const excludedRoots = ref([])
const existingTestPairs = ref([])
const images = ref([])

async function fetchProblem() {
  try {
    const res = await problemsApi.getDetail(fetchId)
    if (res.code === 0) {
      const p = res.data
      numericId = p.problem_id
      backId.value = p.problem_number || 'p' + p.problem_id
      document.title = `编辑 ${p.problem_name} - QuickOJ`
      existingTestPairs.value = p.test_cases || []
      Object.assign(form.value, {
        problem_name: p.problem_name || '',
        statement: p.statement || '',
        difficulty: p.difficulty || 1000,
        time_limit: p.time_limit || 1000,
        memory_limit: Math.round((p.memory_limit || 256000) / 1024),  // KB → MB
        sample_download_policy: p.sample_download_policy || 'none',
        source: p.source || '',
        tags: p.tags || [],
      })
    } else {
      errorMsg.value = res.message
    }
  } catch (e) {
    errorMsg.value = e.message
  }
  loading.value = false
}

async function handleUpdate() {
  msg.value = null
  saving.value = true
  try {
    const fd = new FormData()
    if (form.value.problem_name) fd.append('problem_name', form.value.problem_name)
    if (form.value.statement) fd.append('statement', form.value.statement)
    if (form.value.difficulty != null) fd.append('difficulty', form.value.difficulty)
    if (form.value.time_limit != null) fd.append('time_limit', form.value.time_limit)
    if (form.value.memory_limit != null) fd.append('memory_limit', form.value.memory_limit * 1024)  // MB → KB
    if (form.value.sample_download_policy) fd.append('sample_download_policy', form.value.sample_download_policy)
    if (form.value.source) fd.append('source', form.value.source)
    if (form.value.tags.length) fd.append('tags', JSON.stringify(form.value.tags))
    if (excludedRoots.value.length) fd.append('excluded_roots', JSON.stringify(excludedRoots.value))
    for (const f of testDataFiles.value) fd.append('test_data', f)
    for (const img of images.value) fd.append('images', img)

    const res = await problemsApi.update(numericId, fd)
    if (res.code === 0) {
      msg.value = { type: 'success', text: res.message }
      setTimeout(() => router.push(`/problems/${backId.value}`), 1500)
    } else {
      msg.value = { type: 'error', text: res.message }
    }
  } catch (e) {
    msg.value = { type: 'error', text: e.message }
  }
  saving.value = false
}

onMounted(fetchProblem)
</script>

<template>
  <div>
    <div class="page-header">
      <h1>编辑题目</h1>
      <router-link :to="`/problems/${backId}`" class="btn btn-outline">← 返回题目</router-link>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="errorMsg" class="card">
      <div class="alert alert-error">{{ errorMsg }}</div>
    </div>

    <div v-else class="card">
      <div v-if="msg" :class="msg.type === 'success' ? 'alert alert-success' : 'alert alert-error'">
        {{ msg.text }}
      </div>

      <div class="form-group">
        <label class="form-label">题名</label>
        <input v-model="form.problem_name" class="form-input" maxlength="50" />
      </div>

      <div class="form-group">
        <label class="form-label">题面 <span class="text-muted">(Markdown)</span></label>
        <textarea v-model="form.statement" class="form-textarea" rows="14"></textarea>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label class="form-label">难度</label>
          <input v-model.number="form.difficulty" class="form-input" type="number" />
        </div>
        <div class="form-group">
          <label class="form-label">时间限制 (ms)</label>
          <input v-model.number="form.time_limit" class="form-input" type="number" />
        </div>
        <div class="form-group">
          <label class="form-label">内存限制 (MB)</label>
          <input v-model.number="form.memory_limit" class="form-input" type="number" />
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label class="form-label">样例下载策略</label>
          <select v-model="form.sample_download_policy" class="form-select">
            <option value="all">全部可下载</option>
            <option value="none">全部不可下载</option>
            <option value="first_failed">仅第一个出错点</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">来源</label>
          <input v-model="form.source" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">标签</label>
          <TagInput v-model="form.tags" />
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">测试数据 <span class="text-muted">(修改后将进入重新审核)</span></label>
        <TestDataUpload v-model="testDataFiles" :existing-pairs="existingTestPairs"
          :problem-type="form.problem_type"
          @update:excluded-roots="v => excludedRoots = v" />
      </div>

      <div class="form-group">
        <label class="form-label">替换题面图片</label>
        <input type="file" accept="image/*" multiple @change="images = Array.from($event.target.files)" />
      </div>

      <button class="btn btn-primary btn-lg" :disabled="saving" @click="handleUpdate">
        {{ saving ? '保存中...' : '保存修改' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}
.ml-1 { margin-left: 8px; }
</style>
