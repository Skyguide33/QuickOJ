<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import TagInput from '../components/TagInput.vue'
import TestDataUpload from '../components/TestDataUpload.vue'
import { problemsApi } from '../api/problems'

const router = useRouter()

const form = ref({
  problem_name: '',
  statement: '',
  problem_type: 'traditional',
  difficulty: 1000,
  time_limit: 1000,
  memory_limit: 256,  // MB，提交时转为 KB
  sample_download_policy: 'none',
  source: '',
  tags: [],
})

const testDataFiles = ref([])
const images = ref([])
const msg = ref(null)
const loading = ref(false)

async function handleCreate() {
  msg.value = null
  if (!form.value.problem_name || !form.value.statement) {
    msg.value = { type: 'error', text: '请填写题名和题面' }
    return
  }
  if (!testDataFiles.value.length) {
    msg.value = { type: 'error', text: '请上传测试数据' }
    return
  }

  loading.value = true
  try {
    const fd = new FormData()
    fd.append('problem_name', form.value.problem_name)
    fd.append('statement', form.value.statement)
    fd.append('problem_type', form.value.problem_type)
    fd.append('difficulty', form.value.difficulty)
    fd.append('time_limit', form.value.time_limit)
    fd.append('memory_limit', form.value.memory_limit * 1024)  // MB → KB
    fd.append('sample_download_policy', form.value.sample_download_policy)
    if (form.value.source) fd.append('source', form.value.source)
    if (form.value.tags.length) fd.append('tags', JSON.stringify(form.value.tags))
    for (const f of testDataFiles.value) {
      fd.append('test_data', f)
    }
    for (const img of images.value) {
      fd.append('images', img)
    }

    const res = await problemsApi.create(fd)
    if (res.code === 0) {
      msg.value = { type: 'success', text: res.message }
      setTimeout(() => router.push(`/problems/${res.data.problem_number || 'p' + res.data.problem_id}`), 1500)
    } else {
      msg.value = { type: 'error', text: res.message }
    }
  } catch (e) {
    msg.value = { type: 'error', text: e.message }
  }
  loading.value = false
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1>上传题目</h1>
      <router-link to="/problems" class="btn btn-outline">← 返回题库</router-link>
    </div>

    <div v-if="msg" :class="msg.type === 'success' ? 'alert alert-success' : 'alert alert-error'">
      {{ msg.text }}
    </div>

    <div class="card">
      <div class="form-group">
        <label class="form-label">题名 <span class="text-danger">*</span></label>
        <input v-model="form.problem_name" class="form-input" maxlength="50" placeholder="不超过50字符" />
      </div>

      <div class="form-group">
        <label class="form-label">题面 <span class="text-danger">*</span> <span class="text-muted">(Markdown 格式)</span></label>
        <textarea v-model="form.statement" class="form-textarea" rows="14" placeholder="支持 Markdown 格式..."></textarea>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label class="form-label">题型 <span class="text-danger">*</span></label>
          <select v-model="form.problem_type" class="form-select">
            <option value="traditional">传统题</option>
            <option value="interactive">交互题</option>
            <option value="output-only">输出题</option>
            <option value="communication">通信题</option>
          </select>
        </div>
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
          <input v-model="form.source" class="form-input" placeholder="如 LeetCode, 洛谷" />
        </div>
        <div class="form-group">
          <label class="form-label">标签</label>
          <TagInput v-model="form.tags" />
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">测试数据 <span class="text-danger">*</span></label>
        <TestDataUpload v-model="testDataFiles" :problem-type="form.problem_type" />
      </div>

      <div class="form-group">
        <label class="form-label">题面图片 <span class="text-muted">(可选，多选)</span></label>
        <input type="file" accept="image/*" multiple @change="images = Array.from($event.target.files)" />
        <span v-if="images.length" class="text-sm text-muted ml-1">{{ images.length }} 个文件</span>
      </div>

      <button class="btn btn-primary btn-lg" :disabled="loading" @click="handleCreate">
        {{ loading ? '上传中...' : '上传题目' }}
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
.text-danger { color: var(--danger); }
.ml-1 { margin-left: 8px; }
</style>
