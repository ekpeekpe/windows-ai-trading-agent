import React, { useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';

const API = '/api';
type Proposal = { account: number; symbol: string; side: string; volume: string; stop_loss?: string | null; take_profit?: string | null };
type Pending = { id: string; proposal: Proposal; status: string; execution_enabled: false };
type ChatLine = { role: string; text: string };

function App() {
  const [localToken, setLocalToken] = useState('');
  const [model, setModel] = useState('gpt-4.1-mini');
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState('Backend not checked');
  const [terminal, setTerminal] = useState('Not connected');
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [lastSpoken, setLastSpoken] = useState('');
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [speakReplies, setSpeakReplies] = useState(true);
  const [pending, setPending] = useState<Pending | null>(null);
  const [order, setOrder] = useState<Proposal>({ account: 0, symbol: 'EURUSD', side: 'buy', volume: '0.01' });
  const abortRef = useRef<AbortController | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  function say(text: string) {
    setLastSpoken(text);
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1;
      window.speechSynthesis.speak(utterance);
    }
  }
  function stop() {
    abortRef.current?.abort();
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop();
    streamRef.current?.getTracks().forEach(t => t.stop());
    window.speechSynthesis?.cancel();
    setRecording(false); setBusy(false); setStatus('Client request stopped; any server call may still finish.');
  }
  async function api(path: string, opts: RequestInit = {}): Promise<any> {
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      const headers = new Headers(opts.headers);
      headers.set('x-agent-token', localToken);
      if (opts.body && !(opts.body instanceof FormData)) headers.set('Content-Type', 'application/json');
      const r = await fetch(API + path, { ...opts, headers, signal: ctrl.signal });
      const response = await r.json();
      if (!r.ok) throw new Error(String(response.detail || 'HTTP ' + r.status));
      return response;
    } finally { if (abortRef.current === ctrl) abortRef.current = null; }
  }
  async function checkTerminal() {
    setStatus('Checking real terminal');
    try {
      const result = await api('/terminal');
      setTerminal(JSON.stringify(result, null, 2));
      if (result.account?.login) setOrder(x => ({ ...x, account: result.account.login }));
      setStatus(result.connected ? 'MT5 connected' : 'MT5 disconnected');
    } catch (e) {
      setTerminal(String(e)); setStatus('MT5 unavailable');
    }
  }
  async function send(e: React.FormEvent) {
    e.preventDefault(); if (busy || !message.trim()) return;
    const prompt = message.trim(); setMessage(''); setBusy(true);
    setLines(x => [...x, { role: 'You', text: prompt }]);
    setStatus('Requesting AI response');
    try {
      const response = await api('/chat', { method: 'POST', body: JSON.stringify({ message: prompt, model }) });
      setLines(x => [...x, { role: 'Assistant', text: response.answer }]);
      setStatus('Response received');
      if (speakReplies) say(response.answer);
    } catch (e) {
      const text = String(e); setLines(x => [...x, { role: 'Error', text }]);
      setStatus('Request failed'); if (speakReplies) say('Request failed. ' + text);
    } finally { setBusy(false); }
  }
  async function microphone() {
    if (recording) { recorderRef.current?.stop(); setRecording(false); return; }
    if (!navigator.mediaDevices?.getUserMedia || !('MediaRecorder' in window)) {
      setStatus('Microphone recording is not supported by this webview'); return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream; chunksRef.current = [];
      const mime = ['audio/webm', 'audio/mp4'].find(x => MediaRecorder.isTypeSupported(x));
      if (!mime) throw new Error('No compatible microphone recording format');
      const recorder = new MediaRecorder(stream, { mimeType: mime });
      recorderRef.current = recorder;
      recorder.ondataavailable = e => { if (e.data.size) chunksRef.current.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop()); setRecording(false);
        const audio = new Blob(chunksRef.current, { type: mime });
        if (audio.size < 100) { setStatus('Recording was too short'); return; }
        const form = new FormData(); form.append('audio', audio, 'speech.' + (mime === 'audio/mp4' ? 'm4a' : 'webm'));
        setStatus('Sending microphone recording to OpenAI transcription');
        try { const result = await api('/transcribe', { method:'POST', body:form });
          setMessage(result.text); setStatus('Transcription ready to review; press Send to submit');
        } catch (e) { setStatus('Transcription failed: ' + String(e)); }
      };
      recorder.start(); setRecording(true); setStatus('Microphone recording ACTIVE; press Stop Recording');
    } catch (e) { setStatus('Microphone unavailable: ' + String(e)); streamRef.current?.getTracks().forEach(t=>t.stop()); }
  }
  async function prepare(e: React.FormEvent) {
    e.preventDefault();
    try { const result = await api('/proposals', { method: 'POST', body: JSON.stringify(order) });
      setPending(result); setStatus('Proposal prepared; not sent to broker');
    } catch (e) { setStatus('Proposal refused: ' + String(e)); }
  }
  async function decision(approve: boolean) {
    if (!pending) return;
    try {
      const result = await api('/proposals/' + pending.id + '/decision',
        { method:'POST', body:JSON.stringify({ proposal:pending.proposal, approve }) });
      setStatus(result.status + ' — no trade was executed'); setPending(null);
      say(approve ? 'Proposal acknowledged. No trade was executed.' : 'Proposal rejected. No trade was executed.');
    } catch (e) { setStatus('Decision failed: ' + String(e)); }
  }
  return <main style={{maxWidth:760,margin:'2rem auto',padding:'0 1rem',fontFamily:'system-ui',lineHeight:1.5}}>
    <h1>Windows AI Trading Agent</h1>
    <p><strong>Read-only development pilot.</strong> No broker trading or chart control is enabled.</p>
    <p role="status" aria-live="polite"><strong>Status:</strong> {status}</p>
    <p><label>Local access token (backend AGENT_LOCAL_TOKEN) <input type="password" autoComplete="off" value={localToken} onChange={e=>setLocalToken(e.target.value)} /></label></p>
    <button type="button" onClick={checkTerminal}>Check MT5 terminal</button>
    <pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}} aria-label="Actual MT5 terminal status">{terminal}</pre>
    <form onSubmit={send}>
      <p><label>AI provider <select aria-label="AI provider"><option>OpenAI</option></select></label> <label>Model <input value={model} onChange={e=>setModel(e.target.value)} /></label></p>
      <label htmlFor="instruction">Natural-language instruction</label>
      <textarea id="instruction" rows={3} style={{width:'100%'}} value={message} onChange={e=>setMessage(e.target.value)} required />
      <p><button type="submit" disabled={busy}>Send</button> <button type="button" onClick={microphone}>{recording ? 'Stop recording' : 'Push to talk'}</button> <button type="button" onClick={stop}>Stop/Cancel</button></p>
      <p><label><input type="checkbox" checked={speakReplies} onChange={e=>setSpeakReplies(e.target.checked)} /> Speak responses</label> <button type="button" onClick={()=>say(lastSpoken)} disabled={!lastSpoken}>Repeat last response</button></p>
    </form>
    <section aria-label="Conversation history" aria-live="polite"><h2>Conversation</h2>
      {lines.map((line,i)=><p key={i}><strong>{line.role}:</strong> {line.text}</p>)}
    </section>
    <section aria-label="Non-executable trade proposals"><h2>Trade proposal preview (execution disabled)</h2>
      <form onSubmit={prepare}>
        <label>Account <input type="number" value={order.account} onChange={e=>setOrder({...order,account:Number(e.target.value)})} required /></label>{' '}
        <label>Symbol <input value={order.symbol} onChange={e=>setOrder({...order,symbol:e.target.value})} required /></label>{' '}
        <label>Direction <select value={order.side} onChange={e=>setOrder({...order,side:e.target.value})}><option value="buy">Buy</option><option value="sell">Sell</option></select></label>{' '}
        <label>Lots <input value={order.volume} onChange={e=>setOrder({...order,volume:e.target.value})} required /></label>
        <p><button type="submit">Prepare (no execution)</button></p>
      </form>
      {pending && <div role="group" aria-label="Review exact proposal"><p><strong>Unverified proposal:</strong> {JSON.stringify(pending.proposal)}. This is not a broker-validated order.</p>
        <button type="button" onClick={()=>decision(false)}>Reject proposal</button>{' '}
        <button type="button" onClick={()=>decision(true)}>Acknowledge proposal — no trade</button>
      </div>}
    </section>
  </main>;
}
createRoot(document.getElementById('root')!).render(<App />);
