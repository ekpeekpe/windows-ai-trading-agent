import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';

const API = '/api';
function App() {
  const [model, setModel] = useState('gpt-4.1-mini');
  const [message, setMessage] = useState('');
  const [reply, setReply] = useState('No connection checked yet.');
  const [status, setStatus] = useState('Idle');
  async function check() {
    setStatus('Checking');
    try {
      const r = await fetch(API + '/terminal');
      const j = await r.json();
      setReply(JSON.stringify(j, null, 2));
      setStatus(r.ok ? 'Terminal response received' : 'Disconnected');
    } catch {
      setStatus('Backend unavailable');
    }
  }
  async function send(e: React.FormEvent) {
    e.preventDefault();
    setStatus('Asking AI provider');
    try {
      const r = await fetch(API + '/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({message, model})
      });
      const j = await r.json();
      setReply(j.answer || JSON.stringify(j));
      setStatus(r.ok ? 'Response received' : 'Error');
    } catch {
      setReply('Backend unavailable. Start the Python service.');
      setStatus('Error');
    }
  }
  return <main style={{maxWidth:760,margin:'2rem auto',fontFamily:'system-ui',lineHeight:1.5}}>
    <h1>Windows AI Trading Agent</h1>
    <p role="status">Status: {status}. Trading is disabled in this pilot.</p>
    <button onClick={check}>Check MT5 connection</button>
    <form onSubmit={send}>
      <p><label>OpenAI model <input value={model} onChange={e=>setModel(e.target.value)}/></label></p>
      <p><label htmlFor="prompt">Instruction</label></p>
      <textarea id="prompt" rows={4} style={{width:'100%'}} value={message}
        onChange={e=>setMessage(e.target.value)} required/>
      <p><button type="submit">Send</button></p>
    </form>
    <h2>Result</h2><pre style={{whiteSpace:'pre-wrap'}} aria-live="polite">{reply}</pre>
  </main>;
}
createRoot(document.getElementById('root')!).render(<App />);
