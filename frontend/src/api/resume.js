import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 120000,
})

export async function healthCheck() {
  const { data } = await api.get('/health')
  return data
}

export async function parseResume(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/api/v1/resumes/parse', form)
  return data
}

export async function analyzeResume(file, jobDescription) {
  const form = new FormData()
  form.append('file', file)
  form.append('job_description', jobDescription)
  const { data } = await api.post('/api/v1/resumes/analyze', form)
  return data
}

export async function matchResume(payload) {
  const { data } = await api.post('/api/v1/match', payload)
  return data
}

export default api
