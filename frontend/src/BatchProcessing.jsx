import React, { useState, useRef } from 'react'
import axios from 'axios'
import LowConfidenceReview from "./LowConfidenceReview";

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8300'

export default function BulkUpload() {
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [status, setStatus] = useState('')
  const [progress, setProgress] = useState(0)
  const [batchId, setBatchId] = useState(null)
  const [lowConfidence, setLowConfidence] = useState([])   // NEW
  const inputRef = useRef(null)

  const handleFile = (f) => {
    setFile(f)
    setStatus('')
    setProgress(0)
    setBatchId(null)
    setLowConfidence([])   // reset
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    if (e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) { setStatus('No file selected'); return }
    setStatus('Uploading file...')
    const form = new FormData()
    form.append('file', file)
    try {
      const res = await axios.post(`${API_BASE}/api/upload/`, form, {})
      const bid = res.data.batch_id
      setBatchId(bid)
      setStatus(`Batch queued (id=${bid}). Listening for progress...`)
      startSSE(bid)
    } catch (err) {
      console.error(err)
      setStatus('Upload failed: ' + (err.message || 'unknown'))
    }
  }

  function startSSE(bid) {
    const url = `${API_BASE}/api/upload/stream/${bid}/`
    const es = new EventSource(url)

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        setStatus(`Status: ${data.status}`)

        if (data.total_items) {
          const pct = Math.round((data.processed / data.total_items) * 100)
          setProgress(pct)
        }

        // When job is done collect low-confidence list
        if (data.status === 'COMPLETED') {
          setLowConfidence(data.low_confidence || [])
          es.close()
        }

        if (data.status === 'FAILED') {
          es.close()
        }

      } catch (err) {
        console.error('SSE parse', err)
      }
    }

    es.onerror = (err) => {
      console.error('SSE error', err)
      setStatus('SSE connection error')
      es.close()
    }
  }

  return (
    <div className="card" style={{ padding: 12 }}>
      <h3>Bulk Upload (JSON or CSV)</h3>

      <div
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        style={{ border: '2px dashed', padding: 20, borderRadius: 8, marginBottom: 8, background: dragging ? '#eef2ff' : '#fff' }}
      >
        {file ? <div>Selected: <strong>{file.name}</strong></div> : <div>Drag & drop file here</div>}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".json,.csv,application/json,text/csv"
        onChange={(e) => handleFile(e.target.files[0])}
      />

      <div style={{ marginTop: 8 }}>
        <button onClick={() => inputRef.current && inputRef.current.click()}>Choose</button>
        <button onClick={handleUpload} style={{ marginLeft: 8 }}>Upload</button>
      </div>

      <div style={{ marginTop: 12 }}>
        <div style={{ height: 12, background: '#e5e7eb', borderRadius: 6 }}>
          <div style={{ width: `${progress}%`, height: '100%', background: '#2563eb', borderRadius: 6 }} />
        </div>
        <div style={{ marginTop: 8 }}>{status} {progress > 0 && `— ${progress}%`}</div>
      </div>

      {batchId && <div style={{ marginTop: 8 }}>Batch ID: {batchId}</div>}

      {/* Low Confidence Reviewer */}
      {lowConfidence.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <LowConfidenceReview items={lowConfidence} />
        </div>
      )}
    </div>
  )
}
