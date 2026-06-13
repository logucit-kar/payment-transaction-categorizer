import React, { useEffect, useState } from 'react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8300'


export default function UploadHistory() {
  const [batches, setBatches] = useState([])

  useEffect(() => {
    fetchBatches()
  }, [])

  async function fetchBatches() {
    try {
      const res = await axios.get(`${API_BASE}/api/batches/`, { })
      setBatches(res.data)
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div className="card" style={{ padding: 12 }}>
      <h3>Upload History</h3>
      <ul>
        {batches.map(b => (
          <li key={b.id} style={{ marginBottom: 8 }}>
            <div><strong>#{b.id}</strong> {b.filename || '(no filename)'} — {b.status}</div>
            <div>Items: {b.total_items} processed: {b.processed} saved: {b.saved}</div>
            <details>
              <summary>View items</summary>
              <ul>
                {b.items && b.items.map(it => (
                  <li key={it.id}>
                    processed: {it.processed ? 'yes' : 'no'} saved: {it.saved ? 'yes' : 'no'} error: {it.error || '-'}
                    <div style={{ marginLeft: 8 }}>{JSON.stringify(it.payload)}</div>
                  </li>
                ))}
              </ul>
            </details>
          </li>
        ))}
      </ul>
    </div>
  )
}
