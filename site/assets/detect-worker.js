/* Hold The Line: Web Worker running the Python detectors with Pyodide.
 *
 * holdtheline/ (copied unchanged into site/py/) runs here with the Pyodide
 * builds of NumPy, SciPy, OpenCV (opencv-python) and scikit-image, so the
 * page stays responsive (webcam, sound) during a detection.
 *
 * Loading in two steps:
 *   1. Pyodide + numpy, scipy, opencv-python -> "ready": middle_edge and
 *      quantization work;
 *   2. scikit-image (only for the Radon method) -> "radon-ready".
 * scikit-image is loaded from its wheel URL so that Pyodide does not pull its
 * declared dependencies networkx (+ matplotlib), imageio, pillow and
 * pywavelets, which skimage.transform.radon does not import (about 11 MB
 * saved); packaging and lazy-loader, which it does import, are loaded.
 *
 * Messages in : {type: "init"} | {type: "detect", id, method, bytes | rgba+width+height, color?, threshold?}
 *               (bytes = image file; rgba = raw webcam frame)
 * Messages out: {type: "progress", step, loaded, total} | {type: "ready", ms, bytes, versions}
 *               {type: "radon-ready", ms, bytes} | {type: "result", id, data} | {type: "error", id?, fatal?, message}
 */
"use strict";
const PYODIDE_VERSION = "0.27.7";
const CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const CACHE_NAME = `pyodide-${PYODIDE_VERSION}`;
const SKIMAGE_WHEEL = "scikit_image-0.25.0-cp312-cp312-pyodide_2024_0_wasm32.whl";
// Uncompressed sizes, for the progress bar only: Pyodide core 12.6 MB,
// numpy 3.1, scipy 13.5, openblas 6.1, opencv-python 11.4 / scikit-image 10.2.
const EXPECTED = { core: 46.7e6, radon: 10.3e6 };

let step = "core", loaded = 0, netBytes = 0;
const report = () => postMessage({ type: "progress", step, loaded, total: Math.max(EXPECTED[step], loaded) });

// fetch() wrapper: Cache API for the CDN files (instant on the next visits)
// and byte counting for the progress bar.
const netFetch = self.fetch.bind(self);
self.fetch = async (input, init) => {
  const url = input instanceof Request ? input.url : String(input);
  if (!url.startsWith(CDN)) return netFetch(input, init);
  let cache = null, resp = null;
  try { cache = await caches.open(CACHE_NAME); resp = await cache.match(url); } catch { cache = null; }
  const fromNet = !resp;
  if (!resp) {
    resp = await netFetch(url);
    // not awaited: the copy is stored while the original streams to Pyodide
    if (resp.ok && cache) cache.put(url, resp.clone()).catch(() => { /* quota: no cache */ });
  }
  if (!resp.body) return resp;
  const reader = resp.body.getReader();
  const counted = new ReadableStream({
    async pull(ctrl) {
      const { done, value } = await reader.read();
      if (done) { ctrl.close(); return; }
      loaded += value.byteLength; if (fromNet) netBytes += value.byteLength; report(); ctrl.enqueue(value);
    },
  });
  return new Response(counted, { status: resp.status, statusText: resp.statusText, headers: { "Content-Type": resp.headers.get("Content-Type") || "application/octet-stream" } });
};

let pyodide = null, api = null, radonReady = null;

async function init() {
  const t0 = performance.now();
  importScripts(CDN + "pyodide.js");
  pyodide = await loadPyodide({ indexURL: CDN });
  const pkgs = pyodide.loadPackage(["numpy", "scipy", "opencv-python"], { messageCallback: () => {} });
  // Project code: site/py/ (manifest written by site/sync_py.sh)
  const base = new URL("../py/", self.location.href);
  const files = await (await netFetch(new URL("manifest.json", base), { cache: "no-cache" })).json();
  for (const f of files) {
    const text = await (await netFetch(new URL(f, base), { cache: "no-cache" })).text();
    const path = "/home/pyodide/app/" + f;
    pyodide.FS.mkdirTree(path.slice(0, path.lastIndexOf("/")));
    pyodide.FS.writeFile(path, text);
  }
  await pkgs;
  pyodide.runPython("import sys; sys.path.insert(0, '/home/pyodide/app')");
  api = pyodide.pyimport("web_detect");
  const versions = JSON.parse(pyodide.runPython(
    "import json, sys, numpy, scipy, cv2; json.dumps({'python': sys.version.split()[0], 'numpy': numpy.__version__, 'scipy': scipy.__version__, 'opencv': cv2.__version__})"));
  postMessage({ type: "ready", ms: performance.now() - t0, bytes: netBytes, versions });
  // Step 2, in the background: scikit-image for the Radon method.
  const t1 = performance.now(), b1 = netBytes;
  step = "radon"; loaded = 0;
  radonReady = (async () => {
    await pyodide.loadPackage(["packaging", "lazy-loader"], { messageCallback: () => {} });
    await pyodide.loadPackage(CDN + SKIMAGE_WHEEL, { messageCallback: () => {} });
    api.enable_radon();
    const skv = pyodide.runPython("import skimage; skimage.__version__");
    postMessage({ type: "radon-ready", ms: performance.now() - t1, bytes: netBytes - b1, version: skv });
  })();
  radonReady.catch((err) => postMessage({ type: "error", radon: true, message: String(err && err.message || err) }));
}

// JPEG decoding: Pyodide's OpenCV and Pillow are linked against IJG libjpeg,
// whose chroma upsampling differs from the libjpeg-turbo used by the
// server's OpenCV (pixel values move by a few levels, angles by up to 0.3 deg
// on middle_edge and more on quantization). Browsers decode with
// libjpeg-turbo (Chrome, Firefox): we decode here, without colour management,
// and hand the RGBA pixels to Python. cv2.imdecode stays the fallback.
const MAX_UPLOAD_BYTES = 8 * 1024 * 1024;
async function decodeInBrowser(bytes) {
  if (typeof createImageBitmap !== "function" || typeof OffscreenCanvas !== "function") return null;
  try {
    const bmp = await createImageBitmap(new Blob([bytes]), { colorSpaceConversion: "none", premultiplyAlpha: "none" });
    const c = new OffscreenCanvas(bmp.width, bmp.height);
    const ctx = c.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(bmp, 0, 0);
    const rgba = new Uint8Array(ctx.getImageData(0, 0, bmp.width, bmp.height).data.buffer);
    bmp.close();
    return { rgba, width: c.width, height: c.height };
  } catch { return null; }
}

self.onmessage = async (e) => {
  const m = e.data;
  if (m.type === "init") {
    try { await init(); }
    catch (err) { postMessage({ type: "error", fatal: true, message: String(err && err.message || err) }); }
    return;
  }
  if (m.type !== "detect") return;
  try {
    if (m.method === "radon") await radonReady;
    const t0 = performance.now();
    const color = m.color ?? null, thr = m.threshold ?? null;
    let img = m.rgba ? m : null;
    if (!img && m.bytes.length && m.bytes.length <= MAX_UPLOAD_BYTES) img = await decodeInBrowser(m.bytes);
    const out = img
      ? api.detect_rgba(img.rgba, img.width, img.height, m.method, color, thr)
      : api.detect_bytes(m.bytes, m.method, color, thr);
    const data = JSON.parse(out);
    data.worker_ms = performance.now() - t0;
    postMessage({ type: "result", id: m.id, data });
  } catch (err) {
    postMessage({ type: "error", id: m.id, message: String(err && err.message || err) });
  }
};
