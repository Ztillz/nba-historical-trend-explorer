/* Optional dependency-free local preview: node scripts/serve.cjs [port]. */
const http=require("node:http"),fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"../docs"),port=Number(process.argv[2]||8000);
const types={".html":"text/html; charset=utf-8",".css":"text/css; charset=utf-8",".js":"text/javascript; charset=utf-8",".json":"application/json; charset=utf-8"};
http.createServer((request,response)=>{
  let pathname;
  try { pathname=decodeURIComponent(new URL(request.url,"http://localhost").pathname); }
  catch { response.writeHead(400);response.end("Invalid URL");return; }
  const file=path.resolve(root,"."+pathname+(pathname.endsWith("/")?"index.html":""));
  if (!file.startsWith(root+path.sep)) { response.writeHead(403);response.end("Forbidden");return; }
  fs.stat(file,(error,stat)=>{
    if(error||!stat.isFile()){response.writeHead(404);response.end("Not found");return;}
    response.writeHead(200,{"Content-Type":types[path.extname(file)]||"application/octet-stream","Cache-Control":"no-store"});
    fs.createReadStream(file).pipe(response);
  });
}).listen(port,"127.0.0.1",()=>console.log(`Local: http://127.0.0.1:${port}/research.html`));
