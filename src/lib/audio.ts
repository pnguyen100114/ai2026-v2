// Voice questions are recorded here and transcribed by the backend: the Web Speech API only works in
// Chrome/Edge (and fails with "network" in Cốc Cốc, Brave, Opera), while Web Audio works everywhere.
// Raw samples are captured directly instead of using MediaRecorder: decoding its WebM/MP4 output back to
// PCM (decodeAudioData) fails in some browsers and on some microphones, which broke voice input.

const TARGET_SAMPLE_RATE = 16000
const MIN_DURATION_SECONDS = 0.4

export type Recorder = { stop: () => Promise<string>; cancel: () => void }

/** Thrown when the student stopped before saying anything, so the UI can ask them to hold the button longer. */
export class RecordingTooShortError extends Error {}

type AudioContextConstructor = typeof AudioContext

function audioContextClass(): AudioContextConstructor | undefined {
  return window.AudioContext || (window as Window & { webkitAudioContext?: AudioContextConstructor }).webkitAudioContext
}

export function voiceInputSupported() {
  return typeof window !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia) && Boolean(audioContextClass())
}

const WORKLET_SOURCE = `
registerProcessor('pcm-capture', class extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0] && inputs[0][0]
    if (channel) this.port.postMessage(channel.slice(0))
    return true
  }
})`

/** Starts capturing the microphone; `stop()` resolves to base64 16 kHz mono WAV, which Gemini accepts. */
export async function startRecording(): Promise<Recorder> {
  const AudioContextClass = audioContextClass()!
  // Created before awaiting the permission prompt so it still counts as started by the click (Safari).
  const context = new AudioContextClass()
  // Not awaited: without a user gesture the promise never settles, and capture simply starts once it runs.
  void context.resume().catch(() => undefined)
  let stream: MediaStream
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } })
  } catch (err) {
    void context.close()
    throw err
  }

  const chunks: Float32Array[] = []
  const source = context.createMediaStreamSource(stream)
  // Keeps the graph pulling audio without playing the microphone back through the speakers.
  const mute = context.createGain()
  mute.gain.value = 0
  mute.connect(context.destination)
  let node: AudioNode
  if (context.audioWorklet && typeof AudioWorkletNode !== 'undefined') {
    const url = URL.createObjectURL(new Blob([WORKLET_SOURCE], { type: 'application/javascript' }))
    try {
      await context.audioWorklet.addModule(url)
    } finally {
      URL.revokeObjectURL(url)
    }
    const worklet = new AudioWorkletNode(context, 'pcm-capture')
    worklet.port.onmessage = (event: MessageEvent<Float32Array>) => { chunks.push(event.data) }
    node = worklet
  } else {
    const processor = context.createScriptProcessor(4096, 1, 1)
    processor.onaudioprocess = (event) => { chunks.push(event.inputBuffer.getChannelData(0).slice(0)) }
    node = processor
  }
  source.connect(node)
  node.connect(mute)

  const release = () => {
    source.disconnect()
    node.disconnect()
    stream.getTracks().forEach((track) => track.stop())
    void context.close()
  }

  return {
    stop: async () => {
      const sampleRate = context.sampleRate
      release()
      const length = chunks.reduce((total, chunk) => total + chunk.length, 0)
      if (length < sampleRate * MIN_DURATION_SECONDS) throw new RecordingTooShortError()
      const samples = new Float32Array(length)
      let offset = 0
      for (const chunk of chunks) {
        samples.set(chunk, offset)
        offset += chunk.length
      }
      return bytesToBase64(encodeWav(await resample(samples, sampleRate), TARGET_SAMPLE_RATE))
    },
    cancel: release,
  }
}

async function resample(samples: Float32Array, sampleRate: number): Promise<Float32Array> {
  if (sampleRate === TARGET_SAMPLE_RATE) return samples
  const offline = new OfflineAudioContext(1, Math.max(1, Math.round((samples.length * TARGET_SAMPLE_RATE) / sampleRate)), TARGET_SAMPLE_RATE)
  const buffer = offline.createBuffer(1, samples.length, sampleRate)
  buffer.getChannelData(0).set(samples)
  const source = offline.createBufferSource()
  source.buffer = buffer
  source.connect(offline.destination)
  source.start()
  return (await offline.startRendering()).getChannelData(0)
}

function encodeWav(samples: Float32Array, sampleRate: number) {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)
  const writeText = (offset: number, text: string) => { for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i)) }
  writeText(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  writeText(8, 'WAVE')
  writeText(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeText(36, 'data')
  view.setUint32(40, samples.length * 2, true)
  samples.forEach((sample, index) => {
    const clamped = Math.max(-1, Math.min(1, sample))
    view.setInt16(44 + index * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true)
  })
  return new Uint8Array(buffer)
}

function bytesToBase64(bytes: Uint8Array) {
  let binary = ''
  for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000))
  return btoa(binary)
}

/** A Vietnamese voice installed in the browser, used only when the backend voice is unreachable. */
export function vietnameseBrowserVoice(): SpeechSynthesisVoice | null {
  if (!('speechSynthesis' in window)) return null
  return window.speechSynthesis.getVoices().find((voice) => voice.lang.toLowerCase().replace('_', '-').startsWith('vi')) ?? null
}
