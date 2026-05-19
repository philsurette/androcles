import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, resolve, sep } from "node:path";

const host = process.env.HOST ?? "127.0.0.1";
const port = Number(process.env.PORT ?? "4183");
const basePath = normalizeBasePath(process.env.BASE_PATH ?? "/theatre/cuemaster/");
const distDir = resolve(process.env.DIST_DIR ?? "dist");

const server = createServer((request, response) => {
  if (!request.url) {
    response.writeHead(400);
    response.end("Bad request");
    return;
  }
  const url = new URL(request.url, `http://${host}:${port}`);
  if (url.pathname === "/") {
    response.writeHead(302, { Location: basePath });
    response.end();
    return;
  }
  if (!url.pathname.startsWith(basePath)) {
    response.writeHead(404);
    response.end("Not found");
    return;
  }

  const relativePath = decodeURIComponent(url.pathname.slice(basePath.length));
  const requestedPath = safeJoin(distDir, relativePath || "index.html");
  const filePath = existsSync(requestedPath) && statSync(requestedPath).isFile()
    ? requestedPath
    : join(distDir, "index.html");

  response.writeHead(200, { "Content-Type": contentType(filePath) });
  createReadStream(filePath).pipe(response);
});

server.listen(port, host, () => {
  console.log(`Serving ${distDir} at http://${host}:${port}${basePath}`);
});

function normalizeBasePath(value) {
  const withLeading = value.startsWith("/") ? value : `/${value}`;
  return withLeading.endsWith("/") ? withLeading : `${withLeading}/`;
}

function safeJoin(root, relativePath) {
  const resolved = resolve(root, normalize(relativePath));
  if (resolved !== root && !resolved.startsWith(`${root}${sep}`)) {
    return join(root, "index.html");
  }
  return resolved;
}

function contentType(filePath) {
  switch (extname(filePath)) {
    case ".css":
      return "text/css; charset=utf-8";
    case ".html":
      return "text/html; charset=utf-8";
    case ".js":
      return "text/javascript; charset=utf-8";
    case ".json":
      return "application/json; charset=utf-8";
    case ".svg":
      return "image/svg+xml";
    default:
      return "application/octet-stream";
  }
}
