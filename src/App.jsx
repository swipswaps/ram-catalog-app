import React, { useState } from 'react'
import CadViewer from './components/CadViewer.jsx'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

export default function App() {
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [results, setResults] = useState(null)
  const [cadUrl, setCadUrl] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleFileChange = (event) => {
    const selected = event.target.files[0]
    if (selected) {
      setFile(selected)
      setPreviewUrl(URL.createObjectURL(selected))
      setResults(null)
      setCadUrl(null)
      setError(null)
    }
  }

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/analyze`, {
        method: 'POST',
        body: formData
      })
      if (!response.ok) throw new Error(`Backend returned ${response.status}`)
      const data = await response.json()
      setResults(data.components)
      setCadUrl(data.cad_model_url ? `${BACKEND_URL}${data.cad_model_url}` : null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="app-shell">
      <h1>DDR3 / DDR4 / DDR5 RAM Component Cataloguer</h1>
      <p>Upload a module photograph. The backend rectifies perspective, extracts IC markings, resolves JEDEC specifications, and generates a parametric GLB.</p>

      <div className="button-row">
        <input type="file" accept="image/*" onChange={handleFileChange} />
        <button onClick={handleUpload} disabled={loading || !file}>
          {loading ? 'Running pipeline…' : 'Analyse Module'}
        </button>
      </div>

      {previewUrl && (
        <section>
          <h2>Uploaded module</h2>
          <img className="preview-img" src={previewUrl} alt="RAM module preview" />
        </section>
      )}

      {error && <p style={{ color: '#b00020' }}>{error}</p>}

      {results && (
        <section className="result-panel">
          <h2>Detected ICs &amp; JEDEC resolution</h2>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(results, null, 2)}</pre>
        </section>
      )}

      <CadViewer modelUrl={cadUrl} />
    </main>
  )
}
