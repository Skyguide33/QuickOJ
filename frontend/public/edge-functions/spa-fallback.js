// EdgeOne Edge Functions — SPA 回退
// 将所有非静态资源请求重写到 index.html
// 用法：在 EdgeOne 控制台 → 边缘函数 → 新建函数，粘贴此代码

async function handleEvent(event) {
  const { request } = event;
  const url = new URL(request.url);
  const pathname = url.pathname;

  // 静态资源后缀，直接放行
  const staticExts = /\.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot|json|xml|txt|map|webp)$/i;
  // API 请求，直接放行
  const isApi = pathname.startsWith('/api/') || pathname.startsWith('/avatars') || pathname.startsWith('/images');

  if (staticExts.test(pathname) || isApi) {
    // 静态文件或 API 请求：正常回源
    return;
  }

  // 所有其他路径 → 返回 index.html（SPA 回退）
  const resp = await fetch(new URL('/index.html', request.url), {
    method: 'GET',
    headers: request.headers,
  });

  event.respondWith(resp);
}

addEventListener('fetch', (event) => {
  handleEvent(event);
});
