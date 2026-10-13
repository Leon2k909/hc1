const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const project = path.resolve(__dirname, '../../..');
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.png': 'image/png', '.ttf': 'font/ttf' };
const server = http.createServer((req, res) => {
  if (req.url === '/__shutdown') { res.end('closed'); server.close(); return; }
  const file = path.resolve(project, '.' + decodeURIComponent(new URL(req.url, 'http://127.0.0.1').pathname));
  if (!file.startsWith(project + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404).end(); return; }
  res.setHeader('Content-Type', types[path.extname(file)] || 'application/octet-stream');
  fs.createReadStream(file).pipe(res);
});
server.listen(8766, '127.0.0.1', () => console.log('Career layout preview at http://127.0.0.1:8766/output/playwright/career-record/index.html'));
