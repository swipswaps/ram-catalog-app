import React, { useState, useEffect } from 'react';
import CadViewer from './components/CadViewer.jsx';
import './styles.css';

const BACKEND_URL = 'http://localhost:8000';

export default function App() {
  const [file, setFile] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [ocrStatus, setOcrStatus] = useState('loading');

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/health`);
        const data = await res.json();
        setBackendStatus('online');
        if (data.ocr_ready) setOcrStatus('ready');
        else if (data.ocr_error) setOcrStatus(`error: ${data.ocr_error}`);
        else setOcrStatus('loading');
      } catch {
        setBackendStatus('offline');
        setOcrStatus('offline');
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/analyze`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `Backend error: ${response.status}`);
      setResults(data.components);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <h1>DDR3 / DDR4 / DDR5 RAM Component Cataloguer</h1>
      
      {backendStatus === 'offline' && (
        <div style={{ background: '#fee2e2', color: '#991b1b', padding: '1rem', marginBottom: '1rem' }}>
          <strong>Backend Offline:</strong> Docker is not running.
        </div>
      )}
      {backendStatus === 'online' && ocrStatus === 'loading' && (
        <div style={{ background: '#fef08a', color: '#854d0e', padding: '1rem', marginBottom: '1rem' }}>
          <strong>Backend Online:</strong> PaddleOCR models are still loading. Please wait...
        </div>
      )}
      {backendStatus === 'online' && ocrStatus === 'ready' && (
        <div style={{ background: '#dcfce7', color: '#166534', padding: '1rem', marginBottom: '1rem' }}>
          <strong>Backend Online:</strong> OCR Ready.
        </div>
      )}
      {backendStatus === 'online' && ocrStatus.startsWith('error') && (
        <div style={{ background: '#fee2e2', color: '#991b1b', padding: '1rem', marginBottom: '1rem' }}>
          <strong>OCR Init Failed:</strong> {ocrStatus}
        </div>
      )}

      <div className="button-row">
        <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files[0])} />
        <button onClick={handleUpload} disabled={loading || !file || ocrStatus !== 'ready'}>
          {loading ? 'Processing…' : 'Analyse Module'}
        </button>
      </div>

      {error && <p style={{ color: '#b00020', whiteSpace: 'pre-wrap' }}>{error}</p>}

      {results && (
        <section className="result-panel">
          <h2>Detected ICs</h2>
          <pre>{JSON.stringify(results, null, 2)}</pre>
        </section>
      )}

      <CadViewer />
    </main>
  );
}
