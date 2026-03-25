import axios from 'axios'

const BASE = '/api/v1'
export const api = axios.create({ baseURL: BASE })

// Overview
export const getOverview = (reportDate = null) =>
  api.get('/overview', { params: reportDate ? { report_date: reportDate } : {} })

// Currencies
export const getCurrencies = (reportDate = null) =>
  api.get('/currencies', { params: reportDate ? { report_date: reportDate } : {} })

export const getCurrencyDetail = (symbol, reportDate = null, historyWeeks = 52) =>
  api.get(`/currencies/${symbol}`, {
    params: {
      ...(reportDate ? { report_date: reportDate } : {}),
      history_weeks: historyWeeks,
    },
  })

// Pairs
export const getPairs = (reportDate = null, filters = {}) =>
  api.get('/pairs', {
    params: {
      ...(reportDate ? { report_date: reportDate } : {}),
      ...filters,
    },
  })

export const getPairDetail = (pair, reportDate = null, historyWeeks = 52) =>
  api.get(`/pairs/${pair}`, {
    params: {
      ...(reportDate ? { report_date: reportDate } : {}),
      history_weeks: historyWeeks,
    },
  })

// Data management
export const fetchData = (year = null) =>
  api.post('/data/fetch', null, { params: year ? { year } : {} })

export const getDataStatus = () => api.get('/data/status')

// Settings (§16)
export const getConfig   = () => api.get('/config')
export const updateConfig = (body) => api.put('/config', body)
