import { useCallback,useEffect,useRef,useState } from 'react'
import { Activity,AudioLines,Check,ChevronDown,Clipboard,FileAudio,Headphones,Info,Mic,Pause,Play,Radio,RefreshCcw,Shield,Square,UploadCloud,Volume2,X,Zap } from 'lucide-react'
const endpoint='/api'
const uri=()=>`${location.protocol==='https:'?'wss':'ws'}://${location.host}/api/v1/audio/transcriptions/stream`
const human=(ms)=>ms<1000?`${ms} ms`:`${(ms/1000).toFixed(2)} s`

function Pill({children,tone='muted'}) {return <span className={`pill ${tone}`}>{children}</span>}
function Wave({active, analyser}) {
 const canvas=useRef(null)
 useEffect(()=>{
   let raf,ctx=canvas.current?.getContext('2d'); if(!ctx)return
   function draw(){
     const cn=canvas.current,dpr=window.devicePixelRatio||1,w=cn.clientWidth,h=cn.clientHeight
     if(cn.width!==Math.floor(w*dpr)){cn.width=w*dpr;cn.height=h*dpr}
     ctx.clearRect(0,0,w*dpr,h*dpr);ctx.save();ctx.scale(dpr,dpr)
     const bars=75,bw=(w-2)/bars
     const data=new Uint8Array(analyser?.frequencyBinCount||1024)
     if(analyser)analyser.getByteTimeDomainData(data)
     for(let i=0;i<bars;i++){
       const idx=Math.floor(i*data.length/bars)
       const amp=active&&analyser?Math.abs(data[idx]-128)/128:0.08 + Math.abs(Math.sin(i*1.41))*0.09
       const H=Math.max(4,amp*h*1.2),x=i*bw
       ctx.fillStyle=active?`rgba(102,155,255,${0.55+i/bars*.4})`:'rgba(110,130,173,.30)'
       ctx.fillRect(x,(h-H)/2,Math.max(2,bw-3),H)
     }
     ctx.restore();raf=requestAnimationFrame(draw)
   }draw();return ()=>cancelAnimationFrame(raf)
 },[active,analyser])
 return <canvas ref={canvas} className="wave" aria-label="Audio activity visualization"/>
}
export default function App(){
 const [health,setHealth]=useState(null),[model,setModel]=useState(null)
 const [tab,setTab]=useState('mic'),[domain,setDomain]=useState('general')
 const [recording,setRecording]=useState(false),[uploading,setUploading]=useState(false)
 const [transcript,setTranscript]=useState(''),[partial,setPartial]=useState('')
 const [stats,setStats]=useState(null),[error,setError]=useState('')
 const [file,setFile]=useState(null),[normalize,setNormalize]=useState(true)
 const [elapsed,setElapsed]=useState(0),[analyser,setAnalyser]=useState(null)
 const media=useRef(null),audioCtx=useRef(null),source=useRef(null),worklet=useRef(null),socket=useRef(null),clock=useRef(null)
 const scroll=useRef(null)
 const refresh=useCallback(async()=>{
  try{const [h,m]=await Promise.all([fetch(`${endpoint}/health/ready`),fetch(`${endpoint}/v1/models/current`)])
  setHealth(await h.json());setModel(await m.json())}catch{setHealth({ready:false,error:'API unreachable'});setModel(null)}
 },[])
 useEffect(()=>{refresh();const i=setInterval(refresh,6500);return()=>clearInterval(i)},[refresh])
 useEffect(()=>{scroll.current?.scrollIntoView({behavior:'smooth',block:'end'})},[transcript,partial])
 useEffect(()=>()=>{if(clock.current)clearInterval(clock.current);socket.current?.close();media.current?.getTracks().forEach(t=>t.stop());audioCtx.current?.close()},[])
 const onEvent=(event)=>{
   let data;try{data=JSON.parse(event.data)}catch{return}
   if(data.type==='session.error'){setError(data.message);return}
   if(data.type==='session.closed'){socket.current?.close();return}
   if(data.type==='transcript.partial'){setPartial(data.normalized_text||data.text)}
   if(data.type==='transcript.final'){setTranscript(data.normalized_text||data.text);setPartial('');setStats({mode:'Live stream',duration:data.end_ms})}
 }
 async function startMic(){
  if(!health?.ready){setError('The STT model is not ready. Download and warm it first.');return}
  setError('');setTranscript('');setPartial('');setElapsed(0);setStats(null)
  let localStream,context,ws
  try{
    localStream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,channelCount:1}})
    ws=new WebSocket(uri());ws.binaryType='arraybuffer';socket.current=ws
    await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=()=>reject(new Error('WebSocket connection failed'))})
    ws.onmessage=onEvent
    ws.send(JSON.stringify({type:'session.start',audio:{format:'pcm_s16le',sample_rate:16000,channels:1},language:'fa',normalize,domain}))
    context=new AudioContext();audioCtx.current=context
    await context.audioWorklet.addModule('/pcm-processor.js')
    source.current=context.createMediaStreamSource(localStream)
    const analyzer=context.createAnalyser();analyzer.fftSize=2048;setAnalyser(analyzer)
    worklet.current=new AudioWorkletNode(context,'soorin-pcm-processor')
    worklet.current.port.onmessage=({data})=>{if(ws.readyState===WebSocket.OPEN)ws.send(data)}
    source.current.connect(analyzer);analyzer.connect(worklet.current)
    // Keep worklet clock running, with zero gain so raw mic isn't played back.
    const mute=context.createGain();mute.gain.value=0;worklet.current.connect(mute);mute.connect(context.destination)
    media.current=localStream;setRecording(true)
    const started=Date.now();clock.current=setInterval(()=>setElapsed(Math.round((Date.now()-started)/1000)),250)
  }catch(ex){setError(ex.message||'Microphone unavailable');localStream?.getTracks().forEach(t=>t.stop());context?.close();ws?.close()}
 }
 async function stopMic(){
  setRecording(false);clearInterval(clock.current)
  worklet.current?.disconnect();source.current?.disconnect()
  media.current?.getTracks().forEach(t=>t.stop());media.current=null
  await audioCtx.current?.close();audioCtx.current=null;setAnalyser(null)
  if(socket.current?.readyState===WebSocket.OPEN){socket.current.send(JSON.stringify({type:'session.end'}))}
 }
 async function sendFile(){
  if(!file||uploading)return
  setUploading(true);setError('');setTranscript('');setPartial('');setStats(null)
  try{
    const body=new FormData();body.append('file',file);body.append('language','fa');body.append('normalize',String(normalize));body.append('domain',domain)
    const response=await fetch(`${endpoint}/v1/audio/transcriptions`,{method:'POST',body})
    const data=await response.json();if(!response.ok)throw new Error(data.detail?.message||data.detail||data.error?.message||'Transcription failed')
    setTranscript(data.normalized_text);setStats({mode:'File transcription',duration:data.duration_ms,processing:data.processing_ms,rtf:data.rtf})
  }catch(ex){setError(String(ex.message))}finally{setUploading(false)}
 }
 const canCopy=Boolean(transcript||partial)
 return <div className="app-shell">
   <aside className="sidebar">
     <div className="brand"><div className="brand-mark"><AudioLines size={23}/></div><div><strong>SOORIN<span className="brand-dot">.</span></strong><small>VOICE INFRASTRUCTURE</small></div></div>
     <div className="nav-label">WORKSPACE</div>
     <div className="nav-item selected"><Activity size={18}/> Transcription Studio <span className="nav-pulse"/></div>
     <div className="nav-item inactive"><Radio size={18}/> Live audio</div>
     <div className="nav-label">RUNTIME</div>
     <div className="mini-card"><div className="mini-title"><span className={`status-dot ${health?.ready?'ok':'off'}`}/>Inference service</div><strong>{health?.ready?'Model online':'Not ready'}</strong><span className="mini-muted">{model?.name||'Waiting for backend'}</span><div className="mini-foot"><Pill tone={model?.streaming_mode==='native'?'success':'muted'}>{model?.streaming_mode==='native'?'Native streaming':'Buffered mode'}</Pill><Pill>CPU first</Pill></div></div>
     <div className="side-bottom"><Shield size={16}/><span>Locally hosted. Your audio stays in your infrastructure.</span></div>
   </aside>
   <main className="main">
     <header className="topbar"><div className="crumb">Platform <span>/</span> Speech Intelligence <span>/</span> <b>Studio</b></div><div className="top-right"><span className="topchip"><span className={`status-dot ${health?.ready?'ok':'off'}`}/>{health?.ready?'Service operational':'Service unavailable'}</span><button className="icon-btn" onClick={refresh} title="Refresh service"><RefreshCcw size={17}/></button></div></header>
     <div className="content">
       <div className="intro"><div><div className="eyebrow"><span/> PERSIAN SPEECH INTELLIGENCE <span className="version">v0.1</span></div><h1>Speech, transformed<br/><span>into understanding.</span></h1><p>Transcribe Persian audio locally with a modular, production-oriented inference service.</p></div><div className="intro-icon"><AudioLines size={58} strokeWidth={1.3}/></div></div>
       <div className="metrics-row"><div><span>ACTIVE MODEL</span><strong>{model?.name||'No model loaded'}</strong></div><div><span>BACKEND</span><strong>{model?.backend?.replaceAll('_',' ')||'Unavailable'}</strong></div><div><span>STREAMING MODE</span><strong>{model?.streaming_mode==='native'?'Cache-aware / native':'Buffered / chunked'}</strong></div></div>
       <div className="section-header"><h2>Transcription studio</h2><span>Audio → Persian text</span></div>
       <div className="studio-grid"><section className="card input-panel"><div className="card-header"><div><h3>Audio input</h3><p>Record in real time or transcribe a file</p></div><Headphones size={19}/></div>
           <div className="segmented"><button className={tab==='mic'?'active':''} onClick={()=>{if(!recording)setTab('mic')}}><Mic size={16}/> Live microphone</button><button className={tab==='upload'?'active':''} onClick={()=>{if(!recording)setTab('upload')}}><UploadCloud size={16}/> Upload file</button></div>
           {tab==='mic'?<div className="microphone-area"><div className={`mic-bubble ${recording?'listening':''}`}><Mic size={29}/></div><strong>{recording?'Listening to your voice':'Microphone is ready'}</strong><p>{recording?'Speak naturally in Persian. Partial text appears as the model processes audio.':'A private, local connection to your STT service.'}</p><Wave active={recording} analyser={analyser}/><div className="timer">{String(Math.floor(elapsed/60)).padStart(2,'0')}:{String(elapsed%60).padStart(2,'0')} <span>{recording?'● LIVE':'READY'}</span></div><button className={`primary-btn ${recording?'stop':''}`} disabled={!health?.ready} onClick={recording?stopMic:startMic}>{recording?<><Square size={16} fill="currentColor"/> Stop recording</>:<><Mic size={18}/> Start recording</>}</button></div>:
           <div className="upload-area"><label className="dropzone" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();setFile(e.dataTransfer.files[0])}}><input type="file" accept="audio/*,.wav,.flac,.mp3,.ogg" onChange={e=>setFile(e.target.files[0])}/><div className="upload-icon"><FileAudio size={25}/></div><strong>{file?.name||'Choose an audio file'}</strong><p>{file?`${(file.size/1024/1024).toFixed(2)} MB · Ready for transcription`:'Drop a file here or click to browse'} </p><span>WAV, FLAC, MP3 (subject to server decoder support)</span></label><button className="primary-btn" disabled={!file||!health?.ready||uploading} onClick={sendFile}>{uploading?<><RefreshCcw className="spin" size={16}/> Processing...</>:<><Zap size={17}/> Transcribe audio</>}</button></div>}
           <div className="options"><label><span>Vocabulary domain</span><div className="selectbox"><select value={domain} disabled={recording} onChange={e=>setDomain(e.target.value)}><option value="general">General Persian</option><option value="soc">Cybersecurity / SOC</option></select><ChevronDown size={16}/></div></label><label className="toggle-row"><span>Text normalization</span><input type="checkbox" checked={normalize} disabled={recording} onChange={e=>setNormalize(e.target.checked)}/><span className="toggle-ui"/></label></div>
         </section><section className="card output-panel"><div className="card-header"><div><h3>Transcript</h3><p>Recognition output and partial hypotheses</p></div><div className="output-actions"><Pill tone={canCopy?'success':'muted'}>{canCopy?'Transcript ready':'Awaiting audio'}</Pill><button className="icon-btn" disabled={!canCopy} onClick={()=>navigator.clipboard.writeText(transcript||partial)} title="Copy transcript"><Clipboard size={16}/></button></div></div>
           {error&&<div className="error-box"><Info size={18}/><span>{error}</span><button onClick={()=>setError('')}><X size={16}/></button></div>}
           {!transcript&&!partial?<div className="empty-output"><div className="empty-icon"><AudioLines size={30}/></div><strong>Your transcript will appear here</strong><p>Start a live recording or upload audio to see the result. Persian script is displayed right-to-left.</p></div>:<div className="transcript-box" lang="fa" dir="rtl"><p>{transcript||partial}</p>{partial&&!transcript&&<span className="partial-indicator">در حال پردازش…</span>}<div ref={scroll}/></div>}
           <div className="results-footer"><div className="result-title"><Check size={16}/> Processing insights</div><div className="result-grid"><div><small>MODE</small><strong>{stats?.mode||'—'}</strong></div><div><small>AUDIO LENGTH</small><strong>{stats?.duration?human(stats.duration):'—'}</strong></div><div><small>PROCESSING</small><strong>{stats?.processing?human(stats.processing):'—'}</strong></div><div><small>REAL-TIME FACTOR</small><strong>{stats?.rtf??'—'}</strong></div></div></div>
         </section></div>
       <div className="bottom-note"><Info size={16}/><span>Model selection is configured by <code>STT_MODEL</code> on the server. Changing the model does not change this interface or its API contract.</span></div>
     </div>
   </main>
 </div>
}
