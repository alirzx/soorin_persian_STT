class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.samples = [];
    this.previous = 0;
    this.phase = 0;
    this.step = sampleRate / 16000;
  }
  process(inputs) {
    const source = inputs[0];
    if (!source || !source.length) return true;
    const channels = source.length;
    const input = source[0];
    for (let i = 0; i < input.length; i++) {
      let s = 0;
      for (let j = 0; j < channels; j++) s += source[j][i];
      s /= channels;
      if (i === 0 && this.phase < 0) this.phase = 0;
      // Linear interpolation on capture-device sample rate -> 16 kHz mono.
      while (this.phase <= i) {
        const frac = this.phase - (i - 1);
        const last = i > 0 ? source[0][i-1] : this.previous;
        const out = Math.max(-1,Math.min(1,last + (s-last)*Math.max(0,Math.min(1,frac))));
        this.samples.push(Math.round(out * 32767));
        this.phase += this.step;
        if (this.samples.length >= 320) {
          const frame = new Int16Array(this.samples.splice(0,320));
          this.port.postMessage(frame.buffer,[frame.buffer]);
        }
      }
    }
    this.phase -= input.length;
    this.previous = input[input.length-1];
    return true;
  }
}
registerProcessor('soorin-pcm-processor',PCMProcessor);
