import React, { useState, useEffect } from 'react'
import { postMatch, createTransaction, listExamples, pushExample } from './api'

import BatchProcessing from './BatchProcessing';
import UploadHistory from './UploadHistory';
import TransactionList from "./TransactionList";

export default function App(){
  const [desc, setDesc] = useState('')
  const [amount, setAmount] = useState('')
  const [match, setMatch] = useState(null)
  const [examples, setExamples] = useState([])

  useEffect(() => {
    loadExamples()
  }, [])

  async function loadExamples(){
    try {
      const res = await listExamples()
      setExamples(res)
    } catch (e){
      console.warn(e)
    }
  }

  async function handleSuggest(){
    if(!desc) return
    try {
      const res = await postMatch(desc)
      setMatch(res)
    } catch (e){
      console.error(e)
      alert('Taxonomy service error')
    }
  }

  async function handleSave(userLabel){
    const payload = {
      description: desc,
      amount: amount || null,
      user_label: userLabel || null,
      predicted_category: match?.category?.name || null,
      predicted_score: match?.score || null
    }
    try {
      alert('Saving...')
      await createTransaction(payload)
      alert('Saving...')
      if(userLabel){
        alert(userLabel)
        // push example record (also saved by Django)
        await pushExample({ category_name: userLabel, example_text: desc })
      }
      setDesc('')
      setAmount('')
      setMatch(null)
      loadExamples()
      alert('Saved')
    } catch (e){
      console.error(e)
      alert('Save failed')
    }
  }

  return (
    <div className="container">
      <h1>Transaction Categorizer</h1>
      <div className="card">
        <label>Description</label>
        <textarea value={desc} onChange={e => setDesc(e.target.value)} />
        <label>Amount </label>
        <input value={amount} onChange={e=>setAmount(e.target.value)} placeholder="e.g. 12.50" />
        <div style={{marginTop:8}}>
          <button onClick={handleSuggest}>Get Suggestion</button>
          <button onClick={() => handleSave(null)}>Save without label</button>
        </div>
      </div>

      {match && (
        <div className="card">
          <h3>Suggestion</h3>
          <div><strong>Category:</strong> {match.category.name} ({match.score.toFixed(3)})</div>
          <div><strong>Entities:</strong> {match.entities.map(e => `${e.text} [${e.label}]`).join(', ')}</div>
          <div style={{marginTop:8}}>
            <button onClick={() => handleSave(match.category.name)}>Accept suggestion (save)</button>
            <button onClick={() => {
              const userLabel = prompt("Enter correct category name")
              if(userLabel) handleSave(userLabel)
            }}>Label manually</button>
          </div>
        </div>
      )}

      <div className="card">
        <h3>Category Examples</h3>
        <ul>
          {examples.map(ex => (
            <li key={ex.id}><strong>{ex.category_name}:</strong> {ex.example_text}</li>
          ))}
        </ul>
      </div>
      <div>       
        <BatchProcessing />
      </div>
      <div>
        <TransactionList />
      </div>
      <div>
        <UploadHistory />
      </div>

    </div>
  )
  



}
