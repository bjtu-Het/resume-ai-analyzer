<script setup>
import { computed } from 'vue'

const props = defineProps({
  result: { type: Object, default: null },
})

const payload = computed(() => props.result?.data || null)
const meta = computed(() => props.result?.meta || null)
const profile = computed(() => payload.value?.profile || null)
const match = computed(() => payload.value?.match || null)
const job = computed(() => payload.value?.job || null)
const hasContent = computed(() => Boolean(payload.value))

function formatRate(v) {
  if (v == null || Number.isNaN(Number(v))) return '-'
  const n = Number(v)
  return n <= 1 ? `${Math.round(n * 100)}%` : `${n}`
}
</script>

<template>
  <section v-if="hasContent" class="panel result-panel">
    <div class="result-head">
      <h2>分析结果</h2>
      <p v-if="meta" class="hint">
        request：{{ meta.request_id || '-' }}
        · cache：{{ meta.cache_hit ? '命中' : '未命中' }}
      </p>
    </div>

    <div v-if="profile" class="block">
      <h3>基本信息</h3>
      <ul class="kv">
        <li><span>姓名</span><strong>{{ profile.name || '-' }}</strong></li>
        <li><span>电话</span><strong>{{ profile.phone || '-' }}</strong></li>
        <li><span>邮箱</span><strong>{{ profile.email || '-' }}</strong></li>
        <li><span>地址</span><strong>{{ profile.address || '-' }}</strong></li>
        <li><span>求职意向</span><strong>{{ profile.job_intention || '-' }}</strong></li>
        <li><span>期望薪资</span><strong>{{ profile.expected_salary || '-' }}</strong></li>
        <li><span>工作年限</span><strong>{{ profile.work_years ?? '-' }}</strong></li>
      </ul>
      <p v-if="profile.skills?.length" class="tags">
        <span v-for="s in profile.skills" :key="s" class="tag">{{ s }}</span>
      </p>
    </div>

    <div v-if="match" class="block">
      <h3>匹配评分</h3>
      <div class="scores">
        <div class="score-main">
          <em>{{ match.score ?? 0 }}</em>
          <span>综合分</span>
        </div>
        <ul class="kv compact">
          <li><span>技能匹配率</span><strong>{{ formatRate(match.skill_match_rate) }}</strong></li>
          <li><span>经验相关度</span><strong>{{ formatRate(match.experience_relevance) }}</strong></li>
          <li><span>AI 评分</span><strong>{{ match.ai_score ?? '-' }}</strong></li>
        </ul>
      </div>
      <ul v-if="match.reasons?.length" class="list">
        <li v-for="(r, i) in match.reasons" :key="i">{{ r }}</li>
      </ul>
      <p v-if="match.missing_keywords?.length" class="tags muted">
        缺失关键词：
        <span v-for="k in match.missing_keywords" :key="k" class="tag">{{ k }}</span>
      </p>
    </div>

    <div v-if="job?.keywords?.length" class="block">
      <h3>JD 关键词</h3>
      <p v-if="job.summary" class="hint">{{ job.summary }}</p>
      <p class="tags">
        <span v-for="k in job.keywords" :key="k" class="tag">{{ k }}</span>
      </p>
    </div>

    <details class="raw">
      <summary>查看原始 JSON</summary>
      <pre>{{ JSON.stringify(result, null, 2) }}</pre>
    </details>
  </section>
</template>
