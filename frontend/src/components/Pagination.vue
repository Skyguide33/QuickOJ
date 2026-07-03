<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: { type: Number, default: 1 },
  size: { type: Number, default: 20 },
  total: { type: Number, default: 0 },
})

const emit = defineEmits(['change'])

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.size)))

const pages = computed(() => {
  const current = props.page
  const total = totalPages.value
  const range = []
  const delta = 2
  const left = Math.max(2, current - delta)
  const right = Math.min(total - 1, current + delta)

  range.push(1)
  if (left > 2) range.push('...')
  for (let i = left; i <= right; i++) range.push(i)
  if (right < total - 1) range.push('...')
  if (total > 1) range.push(total)

  return range
})

function goTo(p) {
  if (p === '...' || p === props.page || p < 1 || p > totalPages.value) return
  emit('change', p)
}
</script>

<template>
  <div v-if="totalPages > 1" class="pagination">
    <button :disabled="page <= 1" @click="goTo(page - 1)">‹ 上一页</button>
    <button
      v-for="p in pages"
      :key="p"
      :class="{ active: p === page, dots: p === '...' }"
      :disabled="p === '...'"
      @click="goTo(p)"
    >{{ p }}</button>
    <button :disabled="page >= totalPages" @click="goTo(page + 1)">下一页 ›</button>
  </div>
</template>

<style scoped>
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
  margin-top: 20px;
}
.pagination button {
  min-width: 36px;
  padding: 6px 10px;
  border: 1px solid var(--gray-300);
  border-radius: var(--radius);
  background: #fff;
  font-size: 14px;
  color: var(--gray-700);
  cursor: pointer;
  transition: all .15s;
}
.pagination button:hover:not(:disabled):not(.dots) {
  border-color: var(--primary);
  color: var(--primary);
}
.pagination button.active {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}
.pagination button:disabled { cursor: not-allowed; opacity: .5; }
.pagination button.dots { border: none; background: none; cursor: default; }
</style>
