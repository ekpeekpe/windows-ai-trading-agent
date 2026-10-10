import React, { useEffect, useRef, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import './app.css';

const native = '__TAURI_INTERNALS__' in window;
type Provider = 'chatgpt' | 'openai' | 'anthropic' | 'gemini';
type Dialog = 'provider' | 'terminal' | 'market' | 'proposal' | 'settings' | 'diagnostics' | 'about' | null;
type Line = { role: 'You' | 'Assistant' | 'Error'; text: string };
type Proposal = {account: number; symbol: string; side: string; volume: string; stop_loss?: string | null; take_profit?: string | null};
type Pending = {id: string; proposal: Proposal};
const modelDefaults: Record<Provider,string> = {chatgpt:'gpt-6.1-sol',openai:'gpt-4.1-mini',anthropic:'claude-sonnet-4-5',gemini:'gemini-2.5-flash'};
const names: Record<Provider,string> = {chatgpt:'ChatGPT plan (Codex)',openai:'OpenAI API',anthropic:'Anthropic API',gemini:'Google Gemini'};
const choices: Provider[] = ['chatgpt','openai','anthropic','gemini'];
function explain(error: unknown) { return error instanceof Error ? error.message : String(error); }
const now = () => new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});

export default function App() {
  const [token,setToken] = useState('');
  const [provider,setProvider] = useState<Provider>('chatgpt');
  const [model,setModel] = useState(modelDefaults.chatgpt);
  const [message,setMessage] = useState('');
  const [lines,setLines] = useState<Line[]>([]);
  const [status,setStatus] = useState('Starting AI services…');
  const [connected,setConnected] = useState<Record<string,boolean>>({});
  const [dialog,setDialog] = useState<Dialog>(null);
  const [menu,setMenu] = useState<string|null>(null);
  const [key,setKey] = useState('');
  const [connectionResult,setConnectionResult] = useState('');
  const [chatgptState,setChatgptState] = useState<{available:boolean;connected:boolean;usage_enabled:boolean;state:string;email?:string|null;error?:string|null;accounts?:{key:string;email?:string|null;connected:boolean}[]}|null>(null);
  const [chatgptModels,setChatgptModels] = useState<{slug:string;display_name:string}[]>([]);
  const [chosenAccount,setChosenAccount] = useState('');
  const [busy,setBusy] = useState(false);
  const [recording,setRecording] = useState(false);
  const [speak,setSpeak] = useState(true);
  const [lastSpoken,setLastSpoken] = useState('');
  const [theme,setTheme] = useState<'system'|'light'|'dark'>('system');
  const [terminals,setTerminals] = useState<string[]>([]);
  const [selectedTerminal,setSelectedTerminal] = useState('');
  const [terminalInfo,setTerminalInfo] = useState('Not checked');
  const [symbol,setSymbol] = useState('EURUSD');
  const [marketResult,setMarketResult] = useState('');
  const [proposal,setProposal] = useState<Proposal>({account:0,symbol:'EURUSD',side:'buy',volume:'0.01'});
  const [pending,setPending] = useState<Pending|null>(null);
  const [health,setHealth] = useState('Not checked');
  const endRef = useRef<HTMLDivElement>(null);
  const dialogRef = useRef<HTMLHeadingElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const stopRef = useRef<AbortController|null>(null);
  const recorderRef = useRef<MediaRecorder|null>(null);
  const streamRef = useRef<MediaStream|null>(null);
  const chunksRef = useRef<Blob[]>([]);

  async function api(path:string,method='GET',body?:unknown):Promise<any> {
    if (native) {
      if (body instanceof FormData) {
        const audio = body.get('audio');
        if (!(audio instanceof Blob)) throw new Error('Audio recording missing');
        return invoke('backend_transcribe',{audio:Array.from(new Uint8Array(await audio.arrayBuffer())),mime:audio.type.split(';')[0]});
      }
      return invoke('backend_request',{method,path,body:body??null});
    }
    const controller = new AbortController();
    stopRef.current = controller;
    try {
      const headers:Record<string,string> = {'x-agent-token':token};
      if (body && !(body instanceof FormData)) headers['Content-Type']='application/json';
      const response = await fetch('/api'+path,{method,headers,signal:controller.signal,
        body:body instanceof FormData?body:body?JSON.stringify(body):undefined});
      const data = await response.json();
      if(!response.ok) throw new Error(String(data.detail||'Request failed ('+response.status+')'));
      return data;
    } finally { if(stopRef.current===controller) stopRef.current=null; }
  }
  async function refreshChatGPT(){
    try{
      const result=await api('/chatgpt/status');
      setChatgptState(result);setConnected(x=>({...x,chatgpt:result.connected}));
      return result;
    }catch(e){setConnectionResult('ChatGPT status unavailable: '+explain(e));return null;}
  }
  async function startChatGPT(account_key?:string){
    setConnectionResult('Opening the system browser for ChatGPT authorization…');
    try{
      await api('/chatgpt/start','POST',{account_key:account_key||null});
      setConnectionResult('Complete authorization in your browser; return here when finished.');
      await refreshChatGPT();
    }catch(e){setConnectionResult('Sign-in could not start: '+explain(e));}
  }
  async function loadChatGPTModels(){
    try{
      const result=await api('/chatgpt/models');
      setChatgptModels(result.models||[]);
      const first=result.models?.[0]?.slug;
      if(first && provider==='chatgpt')setModel(first);
      setConnectionResult('Model catalog loaded. A model list does not establish plan entitlement.');
    }catch(e){setConnectionResult('Model list unavailable: '+explain(e));}
  }
  async function testChatGPT(){
    setConnectionResult('Running a real ChatGPT-plan inference test…');
    try{
      const result=await api('/chatgpt/test','POST',{model});
      setConnectionResult(result.verified?'Completed inference: '+result.response:'Inference was not verified');
    }catch(e){setConnectionResult('ChatGPT-plan test failed: '+explain(e));}
  }
  async function signOutChatGPT(){
    try{
      const result=await api('/chatgpt/signout','POST');
      setConnectionResult(result.remote_revocation_confirmed?'Signed out and remote session revoked.':
        'Signed out locally. Remote revocation could not be confirmed; review connected apps in ChatGPT Settings.');
      setChatgptModels([]);await refreshChatGPT();
    }catch(e){setConnectionResult('Sign-out failed: '+explain(e));}
  }
  useEffect(()=>{
    if(dialog!=='provider'||provider!=='chatgpt')return;
    let running=true;
    const poll=()=>{if(running)void refreshChatGPT();};
    poll();const timer=window.setInterval(poll,2200);
    return()=>{running=false;window.clearInterval(timer);};
  },[dialog,provider]);
  async function connections(){
    try {
      const result=await api('/providers');
      setConnected(Object.fromEntries(result.providers.map((p:{provider:string;configured:boolean})=>[p.provider,p.configured])));
    } catch(e){setConnectionResult('Unable to load providers: '+explain(e));}
  }
  useEffect(()=>{
    let active=true;
    async function startup(){
      for(let i=0;i<24&&active;i++){
        try {
          const data=await api('/health');
          if(!active)return;
          setHealth(JSON.stringify(data,null,2));
          setStatus('Services ready · trading disabled');
          void connections();
          void refreshChatGPT();
          return;
        } catch {
          if(active)setStatus('Starting AI services…');
          await new Promise(resolve=>setTimeout(resolve,500));
        }
      }
      if(active)setStatus('Backend unavailable · reopen the app or inspect diagnostics');
    }
    void startup();
    return()=>{active=false;};
  },[]);
  useEffect(()=>{endRef.current?.scrollIntoView({behavior:'smooth'});},[lines,busy]);
  useEffect(()=>{if(dialog)dialogRef.current?.focus();},[dialog]);
  useEffect(()=>{
    if(!dialog)return;
    const root=document.querySelector<HTMLElement>('.dialog');
    if(!root)return;
    const keepFocus=(event:KeyboardEvent)=>{
      if(event.key!=='Tab')return;
      const items=Array.from(root.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled)')).filter(el=>el.getClientRects().length>0);
      if(!items.length)return;
      const first=items[0],last=items[items.length-1],current=document.activeElement;
      if(event.shiftKey&&(current===first||current===dialogRef.current)){event.preventDefault();last.focus();}
      else if(!event.shiftKey&&current===last){event.preventDefault();first.focus();}
    };
    root.addEventListener('keydown',keepFocus);
    return()=>root.removeEventListener('keydown',keepFocus);
  },[dialog]);
  useEffect(()=>{
    const onKey=(e:KeyboardEvent)=>{
      if(e.key==='Escape'){setMenu(null);if(dialog)setDialog(null);}
      if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='n'){e.preventDefault();newChat();}
    };
    window.addEventListener('keydown',onKey);
    return()=>window.removeEventListener('keydown',onKey);
  },[dialog]);
  function setChosenProvider(p:Provider){setProvider(p);setModel(modelDefaults[p]);setConnectionResult('');if(p==='chatgpt')void refreshChatGPT();}
  function say(text:string){
    setLastSpoken(text);
    if('speechSynthesis' in window){window.speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(text);u.rate=1;window.speechSynthesis.speak(u);}
  }
  function stop(){
    stopRef.current?.abort();
    if(recorderRef.current?.state==='recording')recorderRef.current.stop();
    streamRef.current?.getTracks().forEach(t=>t.stop());
    window.speechSynthesis?.cancel();
    setRecording(false);setBusy(false);
    setStatus('Client stopped; a submitted server request may still finish');
  }
  function newChat(){stop();setLines([]);setMessage('');setMenu(null);setDialog(null);composerRef.current?.focus();}
  function chooseDialog(d:Dialog){setMenu(null);setDialog(d);}
  function exportConversation(){
    if(!lines.length)return;
    const blob=new Blob([lines.map(x=>x.role+': '+x.text).join('\n\n')],{type:'text/plain;charset=utf-8'});
    const href=URL.createObjectURL(blob);const a=document.createElement('a');
    a.href=href;a.download='windows-ai-chat.txt';a.click();URL.revokeObjectURL(href);setMenu(null);
  }
  async function send(e?:React.FormEvent){
    e?.preventDefault();
    if(busy||!message.trim())return;
    const prompt=message.trim();
    setMessage('');setBusy(true);setMenu(null);
    setLines(x=>[...x,{role:'You',text:prompt}]);setStatus('AI is responding…');
    try {
      const data=await api('/chat','POST',{message:prompt,provider,model});
      if(typeof data.answer!=='string')throw new Error('Invalid AI response');
      setLines(x=>[...x,{role:'Assistant',text:data.answer}]);
      setStatus('Response received · '+now());
      if(speak)say(data.answer);
    } catch(e){
      const msg=explain(e);setLines(x=>[...x,{role:'Error',text:msg}]);setStatus('AI request failed');
      if(speak)say('Request failed. '+msg);
    } finally {setBusy(false);}
  }
  async function record(){
    if(recording){recorderRef.current?.stop();return;}
    if(!navigator.mediaDevices?.getUserMedia||!('MediaRecorder'in window)){setStatus('Microphone unavailable in this WebView');return;}
    try {
      const stream=await navigator.mediaDevices.getUserMedia({audio:true});
      streamRef.current=stream;chunksRef.current=[];
      const mime=['audio/webm','audio/mp4'].find(m=>MediaRecorder.isTypeSupported(m));
      if(!mime)throw new Error('No compatible recording format');
      const recorder=new MediaRecorder(stream,{mimeType:mime});recorderRef.current=recorder;
      recorder.ondataavailable=e=>{if(e.data.size)chunksRef.current.push(e.data);};
      recorder.onstop=async()=>{
        stream.getTracks().forEach(t=>t.stop());setRecording(false);
        const audio=new Blob(chunksRef.current,{type:mime});
        if(audio.size<100){setStatus('Recording too short');return;}
        const form=new FormData();form.append('audio',audio,mime==='audio/mp4'?'speech.m4a':'speech.webm');
        setStatus('Sending audio to OpenAI transcription…');
        try{const data=await api('/transcribe','POST',form);setMessage(data.text||'');setStatus('Transcript ready to review; press Send');composerRef.current?.focus();}
        catch(e){setStatus('Transcription failed: '+explain(e));}
      };
      recorder.start();setRecording(true);setStatus('Microphone recording · click Stop recording');
    }catch(e){setStatus('Microphone error: '+explain(e));streamRef.current?.getTracks().forEach(t=>t.stop());}
  }
  async function manageKey(action:'save'|'remove'|'test'){
    setConnectionResult('Checking '+names[provider]+'…');
    try{
      const base='/providers/'+provider;
      const data=action==='save'?await api(base+'/key','PUT',{api_key:key}):
        action==='remove'?await api(base+'/key','DELETE'):await api(base+'/test','POST');
      setKey('');
      setConnectionResult(action==='save'?'Key stored · connection not yet verified':action==='remove'?'Stored credential removed':
        data.verified?'Connection verified by the provider':'Provider not verified');
      await connections();
    }catch(e){setKey('');setConnectionResult('Connection failed: '+explain(e));}
  }
  async function discover(){
    try{const r=await api('/terminals');setTerminals(r.terminals||[]);
      setSelectedTerminal(r.selected||r.terminals?.[0]||'');setTerminalInfo(r.terminals?.length?'Select a terminal to inspect':'No MT5 installation discovered');}
    catch(e){setTerminalInfo(explain(e));}
  }
  async function selectTerminal(){
    try{const r=await api('/terminals/select','POST',{path:selectedTerminal});setTerminalInfo(r.message);await checkTerminal();}
    catch(e){setTerminalInfo(explain(e));}
  }
  async function checkTerminal(){
    setTerminalInfo('Checking terminal…');
    try{const data=await api('/terminal');setTerminalInfo(JSON.stringify(data,null,2));
      if(data.account?.login)setProposal(p=>({...p,account:data.account.login}));}
    catch(e){setTerminalInfo('Terminal unavailable: '+explain(e));}
  }
  async function readMarket(kind:'quote'|'terminal'){
    setMarketResult('Loading actual MT5 data…');
    try{const data=await api(kind==='quote'?'/quote/'+encodeURIComponent(symbol):'/terminal');setMarketResult(JSON.stringify(data,null,2));}
    catch(e){setMarketResult('Market request failed: '+explain(e));}
  }
  async function prepare(e:React.FormEvent){
    e.preventDefault();
    try{const result=await api('/proposals','POST',proposal);setPending(result);setStatus('Unverified proposal prepared · execution disabled');}
    catch(e){setStatus('Proposal refused: '+explain(e));}
  }
  async function decide(approve:boolean){
    if(!pending)return;
    try{const result=await api('/proposals/'+pending.id+'/decision','POST',{proposal:pending.proposal,approve});
      setPending(null);setStatus(result.status+' · no broker trade placed');
      say(approve?'Proposal acknowledged; no trade was executed':'Proposal rejected; no trade was executed');}
    catch(e){setStatus('Decision refused: '+explain(e));}
  }
  const menus:{name:string;items:{label:string;run:()=>void;disabled?:boolean;hint?:string}[]}[]=[
    {name:'File',items:[{label:'New conversation    Ctrl+N',run:newChat},{label:'Export conversation',run:exportConversation,disabled:!lines.length}]},
    {name:'AI Provider',items:[{label:'Connections and API keys',run:()=>chooseDialog('provider')},{label:'Select model',run:()=>chooseDialog('provider')}]},
    {name:'MetaTrader',items:[{label:'Discover and select terminal',run:()=>{chooseDialog('terminal');void discover();}},{label:'Market data',run:()=>chooseDialog('market')}]},
    {name:'Tools',items:[{label:'Voice and speech settings',run:()=>chooseDialog('settings')},{label:'Non-executable trade proposal',run:()=>chooseDialog('proposal')},{label:'Diagnostics',run:()=>chooseDialog('diagnostics')}]},
    {name:'View',items:[{label:'Appearance and accessibility',run:()=>chooseDialog('settings')}]},
    {name:'Help',items:[{label:'About and security',run:()=>chooseDialog('about')},{label:'Connection diagnostics',run:()=>chooseDialog('diagnostics')}]},
  ];
  return <div className={'app '+(theme==='system'?'':theme)} onClick={()=>{if(menu)setMenu(null);}}>
    <header className="chrome">
      <div className="brand"><span className="brand-mark" aria-hidden="true">◇</span><span>AI Trading Agent</span><span className="edition">Pilot</span></div>
      <nav className="menubar" aria-label="Application menu">
        {menus.map(m=><div className="menu-root" key={m.name} onClick={e=>e.stopPropagation()}>
          <button type="button" className={'menu-trigger '+(menu===m.name?'active':'')} aria-expanded={menu===m.name}
            aria-haspopup="menu" onClick={()=>setMenu(menu===m.name?null:m.name)}>{m.name}</button>
          {menu===m.name&&<div className="menu-panel" role="menu" onKeyDown={e=>{
            if(e.key==='ArrowDown'||e.key==='ArrowUp'){
              e.preventDefault();
              const items=Array.from(e.currentTarget.querySelectorAll<HTMLButtonElement>('button:not(:disabled)'));
              const index=items.indexOf(document.activeElement as HTMLButtonElement);
              items[(index+(e.key==='ArrowDown'?1:-1)+items.length)%items.length]?.focus();
            }
          }}>
            {m.items.map(item=><button type="button" role="menuitem" key={item.label} disabled={item.disabled}
              title={item.hint} onClick={()=>{item.run();setMenu(null);}}>{item.label}</button>)}
          </div>}
        </div>)}
      </nav>
    </header>
    <div className="workspace">
      <div className="toolbar">
        <div className="toolbar-left">
          <button className="icon-button" title="New conversation (Ctrl+N)" aria-label="New conversation" onClick={newChat}>＋</button>
          <button className="pill model-pill" onClick={()=>chooseDialog('provider')} title="Choose AI provider and model">
            <span className="small-dot"/>{names[provider]} <span className="model-name">{model}</span><span aria-hidden="true">⌄</span>
          </button>
        </div>
        <div className="toolbar-right">
          <span className="read-only"><span aria-hidden="true">●</span> Read only</span>
          <button className="icon-button" title="MetaTrader connections" aria-label="MetaTrader connections" onClick={()=>{chooseDialog('terminal');void discover();}}>⌁</button>
          <button className="icon-button" title="Voice settings" aria-label="Voice settings" onClick={()=>chooseDialog('settings')}>♫</button>
          <button className="icon-button" title="Application settings" aria-label="Application settings" onClick={()=>chooseDialog('settings')}>⚙</button>
        </div>
      </div>
      <main className="chat-region" aria-label="Chat workspace">
        <div className="conversation" aria-live="polite" aria-relevant="additions">
          {lines.length===0?<div className="welcome"><div className="welcome-emblem">✦</div><h1>What would you like to do?</h1><p>Ask about your trading workspace, markets, or account.</p></div>:
            <div className="messages">{lines.map((line,i)=><article key={i} className={'message '+line.role.toLowerCase()}>
              <div className="message-label">{line.role}</div><div className="message-text">{line.text}</div>
            </article>)}{busy&&<div className="working">AI is working<span className="ellipsis">…</span></div>}<div ref={endRef}/></div>}
        </div>
        <div className="composer-wrap"><form className="composer" onSubmit={send}>
          <label htmlFor="instruction" className="sr-only">Message to AI Trading Agent</label>
          <textarea id="instruction" ref={composerRef} value={message} rows={2} placeholder="Message AI Trading Agent…"
            onChange={e=>setMessage(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();void send();}}}/>
          <div className="composer-actions">
            <span className="composer-hint">Enter to send · Shift+Enter for a new line</span>
            <div className="composer-buttons">
              <button type="button" className={'icon-button '+(recording?'recording':'')} onClick={record}
                title={recording?'Stop recording':'Push to talk'} aria-label={recording?'Stop recording':'Start voice input'}>{recording?'■':'♩'}</button>
              {busy?<button type="button" className="send-button" onClick={stop} title="Stop response" aria-label="Stop response">■</button>:
                <button className="send-button" type="submit" disabled={!message.trim()} aria-label="Send message">➤</button>}
            </div>
          </div>
        </form><p className="status-line" role="status" aria-live="polite">{status}</p></div>
      </main>
    </div>
    {dialog&&<div className="modal-scrim" onMouseDown={e=>{if(e.target===e.currentTarget)setDialog(null);}}>
      <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
        <div className="dialog-head"><h2 id="dialog-title" tabIndex={-1} ref={dialogRef}>{
          {provider:'AI connections',terminal:'MetaTrader terminals',market:'Market data',proposal:'Trade proposal preview',
           settings:'Appearance and voice',diagnostics:'Diagnostics',about:'About AI Trading Agent'}[dialog]
        }</h2><button type="button" className="icon-button" aria-label="Close dialog" onClick={()=>setDialog(null)}>✕</button></div>
        <div className="dialog-body">
          {dialog==='provider'&&<>
            <p className="subtle">ChatGPT-plan and separately billed provider API connections are independent.</p>
            <div className="provider-list" role="group" aria-label="AI provider">
              {choices.map(p=><button key={p} type="button" className={'provider-option '+(provider===p?'selected':'')}
                onClick={()=>setChosenProvider(p)}><span>{names[p]}</span><span className="option-status">{p==='chatgpt'?(chatgptState?.connected?'Signed in':'Not signed in'):(connected[p]?'Key configured':'Not connected')}</span></button>)}
            </div>
            {provider==='chatgpt'?<>
              <div className="info-note">
                <strong>Official open-source ChatGPT sign-in</strong>
                <p>Use an eligible ChatGPT plan. A separate OpenAI API key is not needed. OpenAI issues your client ID when you authorize the app in your system browser.</p>
                <p role="status">Connection: {chatgptState?.connected?'Signed in as '+(chatgptState.email||'ChatGPT account'):
                  chatgptState?.state==='waiting_for_browser'?'Waiting for browser consent':'Not signed in'}.
                  {' '}Plan usage: {chatgptState?.usage_enabled?'Authorized':'Not verified'}.</p>
              </div>
              <div className="action-row">
                <button className="primary" type="button" onClick={()=>void startChatGPT()}>Continue with ChatGPT</button>
                <button type="button" onClick={()=>void refreshChatGPT()}>Refresh status</button>
                <button type="button" disabled={!chatgptState?.connected} onClick={()=>void signOutChatGPT()}>Disconnect</button>
              </div>
              {(chatgptState?.accounts?.length||0)>0&&<label className="field">Previously registered account
                <select value={chosenAccount} onChange={e=>setChosenAccount(e.target.value)}>
                  <option value="">Choose a saved account</option>
                  {chatgptState?.accounts?.map(a=><option key={a.key} value={a.key}>{a.email||a.key}{a.connected?' · Connected':''}</option>)}
                </select>
              </label>}
              {chosenAccount&&<button type="button" onClick={()=>void startChatGPT(chosenAccount)}>Reauthorize selected account</button>}
              <label className="field">Model
                {chatgptModels.length>0?<select value={model} onChange={e=>setModel(e.target.value)}>
                  {chatgptModels.map(m=><option key={m.slug} value={m.slug}>{m.display_name}</option>)}</select>:
                  <input value={model} onChange={e=>setModel(e.target.value)} aria-label="ChatGPT model identifier"/>}
              </label>
              <div className="action-row">
                <button type="button" disabled={!chatgptState?.usage_enabled} onClick={()=>void loadChatGPTModels()}>Load account models</button>
                <button type="button" disabled={!chatgptState?.usage_enabled} onClick={()=>void testChatGPT()}>Test real ChatGPT inference</button>
              </div>
              <p className="subtle">A successful model list is not entitlement verification. Limits and credits can be reviewed in ChatGPT Settings; no balance is invented here.</p>
            </>:<>
            <label className="field">Model identifier<input value={model} onChange={e=>setModel(e.target.value)}/></label>
            <label className="field">API key<input type="password" autoComplete="new-password" value={key} onChange={e=>setKey(e.target.value)} placeholder="Paste provider API key"/></label>
            <div className="action-row"><button className="primary" type="button" disabled={key.length<12} onClick={()=>void manageKey('save')}>Save key</button>
              <button type="button" onClick={()=>void manageKey('test')}>Test connection</button>
              <button type="button" onClick={()=>void manageKey('remove')}>Remove</button></div>
            <p role="status" className="dialog-feedback">{connectionResult||'A saved key is not verification. Sign in or run a real connection test.'}</p>
            {!native&&<label className="field">Development-only local access token<input type="password" value={token} onChange={e=>setToken(e.target.value)}/></label>}
            </>}
            <div className="info-note"><strong>Claude account sign-in</strong><p>Unavailable for this independent app. Anthropic API-key access remains supported.</p></div>
          </>}
          {dialog==='terminal'&&<>
            <p className="subtle">Select an installed terminal explicitly. Nothing is launched automatically.</p>
            <button type="button" onClick={()=>void discover()}>Discover installations</button>
            <label className="field">Terminal path<select value={selectedTerminal} onChange={e=>setSelectedTerminal(e.target.value)}>
              <option value="">No terminal selected</option>{terminals.map(t=><option key={t} value={t}>{t}</option>)}</select></label>
            <div className="action-row"><button type="button" className="primary" disabled={!selectedTerminal} onClick={()=>void selectTerminal()}>Select and check</button>
              <button type="button" onClick={()=>void checkTerminal()}>Refresh status</button></div>
            <pre className="result" aria-label="Actual MT5 status">{terminalInfo}</pre>
            <p className="subtle">No terminal? Install from <a href="https://www.metatrader5.com/en" target="_blank" rel="noreferrer">MetaQuotes official website ↗</a> when you choose.</p>
          </>}
          {dialog==='market'&&<>
            <label className="field">Symbol<input value={symbol} onChange={e=>setSymbol(e.target.value)}/></label>
            <div className="action-row"><button type="button" className="primary" onClick={()=>void readMarket('quote')}>Get actual bid and ask</button>
              <button type="button" onClick={()=>void readMarket('terminal')}>Account status</button></div>
            <pre className="result" aria-label="Retrieved market data">{marketResult||'No live data retrieved yet'}</pre>
          </>}
          {dialog==='proposal'&&<>
            <p className="warning">Trading is disabled. This form only prepares an unverified proposal; acknowledging it cannot execute an order.</p>
            <form onSubmit={prepare} className="form-grid">
              <label className="field">Account<input type="number" value={proposal.account} onChange={e=>setProposal({...proposal,account:Number(e.target.value)})} required/></label>
              <label className="field">Symbol<input value={proposal.symbol} onChange={e=>setProposal({...proposal,symbol:e.target.value})} required/></label>
              <label className="field">Direction<select value={proposal.side} onChange={e=>setProposal({...proposal,side:e.target.value})}><option value="buy">Buy</option><option value="sell">Sell</option></select></label>
              <label className="field">Volume (lots)<input value={proposal.volume} onChange={e=>setProposal({...proposal,volume:e.target.value})} required/></label>
              <button type="submit" className="primary">Prepare preview only</button>
            </form>
            {pending&&<div className="proposal-confirm"><pre className="result">{JSON.stringify(pending.proposal,null,2)}</pre>
              <div className="action-row"><button type="button" onClick={()=>void decide(false)}>Reject</button>
                <button type="button" onClick={()=>void decide(true)}>Acknowledge — no execution</button></div></div>}
          </>}
          {dialog==='settings'&&<>
            <fieldset className="fieldset"><legend>Appearance</legend>
              <div className="segmented">{(['system','light','dark'] as const).map(t=><button type="button" key={t}
                aria-pressed={theme===t} className={theme===t?'active':''} onClick={()=>setTheme(t)}>{t[0].toUpperCase()+t.slice(1)}</button>)}</div></fieldset>
            <label className="checkbox-field"><input type="checkbox" checked={speak} onChange={e=>setSpeak(e.target.checked)}/> Speak completed replies and errors</label>
            <div className="action-row"><button type="button" onClick={()=>say(lastSpoken)} disabled={!lastSpoken}>Repeat last response</button>
              <button type="button" onClick={()=>window.speechSynthesis?.cancel()}>Stop speech</button></div>
            <p className="subtle">Microphone recordings are sent to OpenAI for transcription after you stop recording. Spoken trade instructions never count as approval.</p>
          </>}
          {dialog==='diagnostics'&&<>
            <p className="subtle">Account information and market data are not cached as simulated responses.</p>
            <div className="action-row"><button type="button" onClick={async()=>{try{const h=await api('/health');setHealth(JSON.stringify(h,null,2));}catch(e){setHealth(explain(e));}}}>Refresh backend health</button>
              <button type="button" onClick={()=>void checkTerminal()}>Check MT5</button></div>
            <h3>Backend</h3><pre className="result">{health}</pre><h3>MT5</h3><pre className="result">{terminalInfo}</pre>
          </>}
          {dialog==='about'&&<>
            <p><strong>Windows AI Trading Agent</strong> · v0.3.1 development pilot</p>
            <p className="subtle">Local-first desktop assistant for registered AI tools and read-only MetaTrader 5 information. No broker orders can be submitted.</p>
            <h3>Privacy and security</h3>
            <p className="subtle">Provider credentials are stored in Windows Credential Manager by the backend. Chat instructions and retrieved data are sent only to the selected AI service. Voice recordings are sent to OpenAI when transcribing.</p>
            <p className="subtle">Eligible open-source users can register a ChatGPT client through browser OAuth. A future paid-hosted app may require a separate approval; code signing still requires publisher credentials.</p>
          </>}
        </div>
      </section>
    </div>}
  </div>;
}
