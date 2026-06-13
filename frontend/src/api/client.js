import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8300'
const TAX_BASE = import.meta.env.VITE_TAXONOMY_URL || 'http://localhost:8200'

export const postMatch = async (text) => {
  const res = await axios.post(`${TAX_BASE}/match`, { text })
  return res.data
}

export const createTransaction = async (payload) => {
  const res = await axios.post(`${API_BASE}/api/transactions/`, payload)
  return res.data
}

export const listExamples = async () => {
  const res = await axios.get(`${API_BASE}/api/category-data/`)
  return res.data
}

export const pushExample = async (payload) => {
  const res = await axios.post(`${API_BASE}/api/category-data/`, payload)
  return res.data
}
