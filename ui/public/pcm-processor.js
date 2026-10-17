// Capture-device-independent downsampling with frame-boundary continuity.
class PCMProcessor extends AudioWorkletProcessor {
  constructor(){
    super();
    this.step=sampleRate/16000;
    this.next=0;
    this.index=0;
    this.previous=0;
    this.frames=[];
  }
  process(inputs){
    const channels=inputs[0];
    if(!channels||!channels.length)return true;
    const length=channels[0].length;
    for(let i=0;i<length;i++){
      let current=0;
      for(const c of channels)current+=c[i];
      current/=channels.length;
      const absolute=this.index+i;
      while(this.next<=absolute){
        const frac=Math.max(0,Math.min(1,this.next-(absolute-1)));
        const sample=this.previous+(current-this.previous)*frac;
        this.frames.push(Math.round(Math.max(-1,Math.min(1,sample))*32767));
        if(this.frames.length===320){
          const pcm=new Int16Array(this.frames);
          this.port.postMessage(pcm.buffer,[pcm.buffer]);
          this.frames=[];
        }
        this.next+=this.step;
      }
      this.previous=current;
    }
    this.index+=length;
    return true;
  }
}
registerProcessor('soorin-pcm-processor',PCMProcessor);
