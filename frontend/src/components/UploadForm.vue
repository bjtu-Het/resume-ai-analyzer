<script setup>
import { ref } from 'vue'

defineProps({
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['submit'])

const file = ref(null)
const fileName = ref('')
const jobDescription = ref('')
const localError = ref('')

function onFileChange(e) {
  const f = e.target.files?.[0]
  if (!f) {
    file.value = null
    fileName.value = ''
    return
  }
  if (!f.name.toLowerCase().endsWith('.pdf')) {
    localError.value = '仅支持 PDF 文件'
    file.value = null
    fileName.value = ''
    e.target.value = ''
    return
  }
  localError.value = ''
  file.value = f
  fileName.value = f.name
}

function onSubmit() {
  localError.value = ''
  if (!file.value) {
    localError.value = '请先上传 PDF 简历'
    return
  }
  if (!jobDescription.value.trim()) {
    localError.value = '请填写岗位需求描述'
    return
  }
  emit('submit', {
    file: file.value,
    jobDescription: jobDescription.value.trim(),
  })
}
</script>

<template>
  <section class="panel form-panel">
    <div class="field">
      <label for="resume-file">简历 PDF</label>
      <input id="resume-file" type="file" accept="application/pdf,.pdf" @change="onFileChange" />
      <p v-if="fileName" class="hint">已选择：{{ fileName }}</p>
    </div>

    <div class="field">
      <label for="jd">岗位需求（JD）</label>
      <textarea
        id="jd"
        v-model="jobDescription"
        rows="8"
        placeholder="粘贴招聘岗位描述，例如：要求 Python / FastAPI，具备 3 年工作经验…"
      />
    </div>

    <button class="cta" type="button" :disabled="loading" @click="onSubmit">
      {{ loading ? '分析中…' : '开始分析' }}
    </button>
    <p v-if="localError" class="error">{{ localError }}</p>
  </section>
</template>
