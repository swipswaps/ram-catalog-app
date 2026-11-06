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

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/health`);
        if (!res.ok) throw new Error('Offline');
        setBackendStatus('online');
      } catch {
        setBackendStatus('offline');
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
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
      if (!response.ok) throw new Error(`Backend returned ${response.status}`);
      const data = await response.json();
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
      <p>Upload a module photograph to extract IC markings via OCR.</p>

      {backendStatus === 'offline' && (
        <div style={{ background: '#fee2e2', color: '#991b1b', padding: '1rem', borderRadius: '8px', marginBottom: '1rem' }}>
          <strong>Backend Offline:</strong> Start Docker locally to enable OCR.
        </div>
      )}
      {backendStatus === 'online' && (
        <div style={{ background: '#dcfce7', color: '#166534', padding: '1rem', borderRadius: '8px', marginBottom: '1rem' }}>
          <strong>Backend Online:</strong> Ready for upload.
        </div>
      )}

      <div className="button-row">
        <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files[0])} />
        <button onClick={handleUpload} disabled={loading || !file || backendStatus === 'offline'}>
          {loading ? 'Processing…' : 'Analyse Module'}
        </button>
      </div>

      {error && <p style={{ color: '#b00020' }}>{error}</p>}

      {results && (
        <section className="result-panel">
          <h2>Detected ICs & JEDEC Resolution</h2>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(results, null, 2)}</pre>
        </section>
      )}

      <CadViewer formFactor="DIMM" moduleType="DDR4" />
    </main>
  );
}
