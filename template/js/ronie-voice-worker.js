// Ronie's natural voice (Kokoro), running in a background thread so speaking never stutters the 3D scene.
// Messages: { id, type: 'load', model } → { id, ok }   |   { id, type: 'speak', text, voice, speed } → { id, ok, audio, rate }
import { KokoroTTS } from 'https://cdn.jsdelivr.net/npm/kokoro-js@1.2.1/dist/kokoro.web.js';

let tts = null;
self.onmessage = async ({ data }) => {
  const { id, type } = data;
  try {
    if (type === 'load') {
      if (!(navigator.gpu && (await navigator.gpu.requestAdapter()))) throw new Error('no WebGPU here');
      tts = await KokoroTTS.from_pretrained(data.model, { dtype: 'fp32', device: 'webgpu' });
      self.postMessage({ id, ok: true });
    } else if (type === 'speak') {
      if (!tts) throw new Error('voice not loaded');
      const out = await tts.generate(data.text, { voice: data.voice, speed: data.speed });
      self.postMessage({ id, ok: true, audio: out.audio, rate: out.sampling_rate }, [out.audio.buffer]);
    }
  } catch (err) {
    self.postMessage({ id, ok: false, error: String(err && err.message || err) });
  }
};
