// Phones often save a photographed exercise as a PDF (16 MB for a single photo). Rendering page 1 in the
// browser sends the chat a ~200 KB JPEG instead of uploading the whole file. Loaded only when a PDF is picked.
import { GlobalWorkerOptions, getDocument } from 'pdfjs-dist/legacy/build/pdf.mjs'
import workerUrl from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url'

GlobalWorkerOptions.workerSrc = workerUrl

export async function renderPdfFirstPage(file: File, maxSide: number): Promise<{ data: string; mime: string; pageCount: number }> {
  const task = getDocument({ data: new Uint8Array(await file.arrayBuffer()) })
  const document = await task.promise
  try {
    const page = await document.getPage(1)
    const base = page.getViewport({ scale: 1 })
    const viewport = page.getViewport({ scale: maxSide / Math.max(base.width, base.height) })
    const canvas = window.document.createElement('canvas')
    canvas.width = Math.round(viewport.width)
    canvas.height = Math.round(viewport.height)
    const context = canvas.getContext('2d')
    if (!context) throw new Error('canvas')
    context.fillStyle = '#fff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    await page.render({ canvas, canvasContext: context, viewport }).promise
    return { data: canvas.toDataURL('image/jpeg', 0.85), mime: 'image/jpeg', pageCount: document.numPages }
  } finally {
    void task.destroy()
  }
}
