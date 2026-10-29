// Render kt-video.html to MP4: Playwright drives window.renderAt(t) frame by frame, PNG frames are piped
// straight into ffmpeg, and the narration is muxed in.
//
//   node render.mjs                 full render + publish (kt-video.mp4, poster.jpg, captions.vtt, chapters.txt)
//   node render.mjs --stills 12,40  only write PNG stills for those times (seconds) to out/stills/
//   node render.mjs --crf 24        override the H.264 quality (higher = smaller file)

import { spawn } from "node:child_process";
import { createReadStream, existsSync, mkdirSync, readFileSync, writeFileSync, copyFileSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { dirname, extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, "out");
const FPS = 30;
const args = process.argv.slice(2);
const opt = name => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : undefined; };
const CRF = opt("--crf") ?? "20";
const STILLS = opt("--stills");

const timing = JSON.parse(readFileSync(join(HERE, "timing.json"), "utf8"));
mkdirSync(OUT, { recursive: true });

function run(cmd, argv, opts = {}) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, argv, { stdio: ["ignore", "inherit", "inherit"], ...opts });
    p.on("error", reject);
    p.on("close", code => (code === 0 ? resolve() : reject(new Error(`${cmd} exited with ${code}`))));
  });
}

// Minimal static server so the page can fetch timing.json (file:// fetches are blocked).
const TYPES = { ".html": "text/html", ".json": "application/json", ".js": "text/javascript", ".wav": "audio/wav" };
function serve() {
  const server = createServer((req, res) => {
    const path = normalize(join(HERE, decodeURIComponent(new URL(req.url, "http://x").pathname)));
    if (!path.startsWith(HERE) || !existsSync(path) || statSync(path).isDirectory()) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { "Content-Type": TYPES[extname(path)] ?? "application/octet-stream" });
    createReadStream(path).pipe(res);
  });
  return new Promise(resolve => server.listen(0, "127.0.0.1", () => resolve(server)));
}

async function openPage(server) {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on("console", m => { if (m.type() === "warning" || m.type() === "error") console.log("[page]", m.text()); });
  await page.goto(`http://127.0.0.1:${server.address().port}/kt-video.html?render=1`);
  const info = await page.evaluate(() => window.ready);
  if (info.missing.length) throw new Error(`narration phrases not found: ${info.missing.join("; ")}`);
  return { browser, page };
}

async function concatAudio() {
  // Each scene = its WAV + PAD seconds of silence, in order.
  const inputs = timing.scenes.flatMap(s => ["-i", join(HERE, "audio", `scene_${s.id}.wav`)]);
  const pads = timing.scenes.map((_, i) => `[${i}]apad=pad_dur=${timing.pad}[a${i}]`).join(";");
  const cat = timing.scenes.map((_, i) => `[a${i}]`).join("") + `concat=n=${timing.scenes.length}:v=0:a=1[out]`;
  await run("ffmpeg", ["-y", "-loglevel", "error", ...inputs, "-filter_complex", `${pads};${cat}`, "-map", "[out]",
                       "-ar", "24000", "-ac", "1", join(OUT, "narration.wav")]);
}

async function renderVideo(page) {
  const frames = Math.round(timing.total * FPS);
  const out = join(OUT, "kt-video.mp4");
  const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "png",
                              "-i", "-", "-i", join(OUT, "narration.wav"), "-map", "0:v", "-map", "1:a",
                              "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", CRF, "-preset", "veryfast",
                              "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out],
                   { stdio: ["pipe", "inherit", "inherit"] });
  const done = new Promise((resolve, reject) => {
    ff.on("error", reject);
    ff.on("close", code => (code === 0 ? resolve() : reject(new Error(`ffmpeg exited with ${code}`))));
  });
  const started = Date.now();
  for (let i = 0; i < frames; i++) {
    await page.evaluate(t => window.renderAt(t), i / FPS);
    const png = await page.screenshot({ type: "png" });
    if (!ff.stdin.write(png)) await new Promise(r => ff.stdin.once("drain", r));
    if (i % 300 === 0) console.log(`frame ${i}/${frames}  (${((Date.now() - started) / 1000).toFixed(0)}s)`);
  }
  ff.stdin.end();
  await done;
  return out;
}

const pad2 = n => String(n).padStart(2, "0");
const ytTime = s => `${Math.floor(s / 60)}:${pad2(Math.floor(s % 60))}`;

function writeSidecars() {
  const chapters = timing.scenes.map(s => `${ytTime(s.start)} ${s.title}`).join("\n") + "\n";
  writeFileSync(join(OUT, "chapters.txt"), chapters);
  const srt = readFileSync(join(HERE, "captions.srt"), "utf8");
  writeFileSync(join(OUT, "captions.srt"), srt);
  const vtt = "WEBVTT\n\n" + srt.replace(/\r/g, "").replace(/(\d\d:\d\d:\d\d),(\d\d\d)/g, "$1.$2");
  writeFileSync(join(OUT, "captions.vtt"), vtt);
}

async function publish(mp4) {
  const s1 = timing.scenes[0];
  // End of scene 1: the shown and refused claims side by side.
  await run("ffmpeg", ["-y", "-loglevel", "error", "-ss", String(s1.start + s1.duration - 1), "-i", mp4,
                       "-frames:v", "1", "-vf", "scale=1280:-2", "-q:v", "3", join(HERE, "poster.jpg")]);
  copyFileSync(mp4, join(HERE, "kt-video.mp4"));
  copyFileSync(join(OUT, "captions.vtt"), join(HERE, "captions.vtt"));
  copyFileSync(join(OUT, "chapters.txt"), join(HERE, "chapters.txt"));
  const mb = statSync(join(HERE, "kt-video.mp4")).size / 1e6;
  console.log(`kt-video.mp4: ${mb.toFixed(1)} MB${mb > 20 ? "  (over 20 MB: re-run with a higher --crf)" : ""}`);
}

const server = await serve();
const { browser, page } = await openPage(server);
try {
  if (STILLS) {
    mkdirSync(join(OUT, "stills"), { recursive: true });
    for (const t of STILLS.split(",").map(Number)) {
      const id = await page.evaluate(x => window.renderAt(x), t);
      const file = join(OUT, "stills", `t${t.toFixed(1).padStart(6, "0")}_s${id}.png`);
      await page.screenshot({ path: file });
      console.log(file);
    }
  } else {
    await concatAudio();
    const mp4 = await renderVideo(page);
    writeSidecars();
    await publish(mp4);
  }
} finally {
  await browser.close();
  server.close();
}
