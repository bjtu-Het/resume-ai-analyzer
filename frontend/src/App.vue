<script setup>
import { onMounted, ref } from 'vue'
import UploadForm from './components/UploadForm.vue'
import ResultPanel from './components/ResultPanel.vue'
import { analyzeResume, healthCheck } from './api/resume'

const apiStatus = ref('检测中…')
const apiDetail = ref('')
const loading = ref(false)
const error = ref('')
const result = ref(null)

onMounted(async () => {
  try {
    const data = await healthCheck()
    const d = data?.data || {}
    apiStatus.value = d.status === 'ok' ? '在线' : String(d.status || '异常')
    apiDetail.value = `模型 ${d.llm_model || '-'} · 缓存 ${d.redis || '-'}`
  } catch {
    apiStatus.value = '离线'
    apiDetail.value = '请先启动后端（uvicorn app.main:app --port 8000）'
  }
})

async function handleAnalyze({ file, jobDescription }) {
  error.value = ''
  result.value = null
  loading.value = true
  try {
    const data = await analyzeResume(file, jobDescription)
    result.value = data
    if (data?.code && data.code !== 0) {
      error.value = data.message || `接口返回 code=${data.code}`
    }
  } catch (err) {
    error.value =
      err?.response?.data?.message ||
      err?.message ||
      '分析请求失败，请检查后端是否启动'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page">
    <header class="hero">
      <p class="brand">ResumeAI</p>
      <h1>智能简历分析</h1>
      <p class="sub">上传 PDF 简历，对照岗位 JD，自动提取关键信息并给出匹配评分</p>
      <p class="status">
        API：<span :class="apiStatus === '在线' ? 'ok' : 'bad'">{{ apiStatus }}</span>
        <span v-if="apiDetail" class="detail">{{ apiDetail }}</span>
      </p>
    </header>

    <main class="layout">
      <UploadForm :loading="loading" @submit="handleAnalyze" />
      <p v-if="error" class="error">{{ error }}</p>
      <ResultPanel :result="result" />
    </main>
  </div>
</template>
