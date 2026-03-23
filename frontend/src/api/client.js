import axios from 'axios'

const BASE = '/api/v1'

export const api = axios.create({ baseURL: BASE })

// Dashboard
export const getDashboard = (reportDate = null) =>
  api.get('/dashboard', { params: reportDate ? { report_date: reportDate } : {} })

// Valuutat
export const getCurrencyRanking = (reportDate = null) =>
  api.get('/currencies/ranking', { params: reportDate ? { report_date: reportDate } : {} })

export const getCurrencyHistory = (currency, weeks = 52) =>
  api.get(`/currencies/${currency}/history`, { params: { weeks } })

export const getAvailableDates = () => api.get('/currencies/dates')

// Parit
export const getPairRanking = (reportDate = null, minAbsScore = 0) =>
  api.get('/pairs/ranking', {
    params: {
      ...(reportDate ? { report_date: reportDate } : {}),
      min_abs_score: minAbsScore,
    },
  })

export const getPairHistory = (pair, weeks = 52) =>
  api.get(`/pairs/${pair}/history`, { params: { weeks } })

export const getHeatmapData = (reportDate = null) =>
  api.get('/pairs/heatmap', { params: reportDate ? { report_date: reportDate } : {} })

// Import
export const uploadFile = (formData) =>
  api.post('/import/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const fetchHistory = (year = null) =>
  api.post('/import/fetch-history', null, { params: year ? { year } : {} })

export const fetchLatest = () => api.post('/import/fetch-latest')

export const getImportLogs = (limit = 50) =>
  api.get('/import/logs', { params: { limit } })

// Bias Dashboard
export const getBiasDashboard = (reportDate = null, threshold = 25) =>
  api.get('/bias-dashboard', {
    params: {
      ...(reportDate ? { report_date: reportDate } : {}),
      threshold,
    },
  })

// Verifiointi
export const getVerification = (reportDate = null) =>
  api.get('/verification', { params: reportDate ? { report_date: reportDate } : {} })

export const getVerificationStats = (weeks = 26) =>
  api.get('/verification/stats', { params: { weeks } })

// Config
export const getConfig = () => api.get('/config')
export const updateWeights = (weights) => api.put('/config/weights', weights)
export const updateThresholds = (thresholds) => api.put('/config/thresholds', thresholds)
