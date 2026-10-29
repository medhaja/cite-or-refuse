// Serve this folder for the play/scrub preview: node preview.mjs, then open the printed URL. Ctrl+C to stop.
import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { dirname, extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const TYPES = { ".html": "text/html", ".json": "application/json", ".wav": "audio/wav" };
const port = Number(process.argv[2] ?? 8123);

createServer((req, res) => {
  const path = normalize(join(HERE, decodeURIComponent(new URL(req.url, "http://x").pathname)));
  if (!path.startsWith(HERE) || !existsSync(path) || statSync(path).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { "Content-Type": TYPES[extname(path)] ?? "application/octet-stream" });
  createReadStream(path).pipe(res);
}).listen(port, "127.0.0.1", () => console.log(`Preview: http://127.0.0.1:${port}/kt-video.html`));
