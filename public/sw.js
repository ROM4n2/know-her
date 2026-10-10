/**
 * know-her 离线急救与轻量 Service Worker 缓存系统
 * 策略定位：
 * - 核心离线急救资源与工具集预缓存 (Precache)
 * - HTML 页面导航采用 Network-First 策略，离线时降级命中本地急救工具或决策树
 * - 静态资源 (CSS / JS / SVG / 字体) 采用 Cache-First 策略加速二次渲染
 */

const CACHE_NAME = 'know-her-offline-v1';

const PRECACHE_ASSETS = [
  '/know-her/',
  '/know-her/tools/',
  '/know-her/guide/decision-tree/',
  '/know-her/glossary/',
  '/know-her/manifest.webmanifest',
  '/know-her/icon-192.svg',
  '/know-her/icon-512.svg',
  '/know-her/og-card.svg',
];

// 1. Install 阶段：预装离线急救关键路径
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// 2. Activate 阶段：清理旧版本缓存并立即接管当前受控页面
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames
          .filter((name) => name.startsWith('know-her-') && name !== CACHE_NAME)
          .map((staleCache) => caches.delete(staleCache))
      )
    ).then(() => self.clients.claim())
  );
});

// 3. Fetch 阶段：区分 HTML 导航请求与静态资源
self.addEventListener('fetch', (event) => {
  const { request } = event;

  // 仅代理同源或可安全缓存的 GET 请求
  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);

  // 过滤非同源协议 (例如 chrome-extension 等)
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // A. 页面导航请求 (HTML) -> Network-First, 离线断网降级至缓存或急救决策树
  const isNavigation =
    request.mode === 'navigate' ||
    (request.headers.get('accept') && request.headers.get('accept').includes('text/html'));

  if (isNavigation) {
    event.respondWith(
      fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
          }
          return networkResponse;
        })
        .catch(async () => {
          // 网络失败，进入离线急救降级逻辑
          const cachedPage = await caches.match(request);
          if (cachedPage) {
            return cachedPage;
          }

          // 若目标页面未被独立缓存，回退至离线工具箱或应急决策树
          const emergencyGuide = await caches.match('/know-her/guide/decision-tree/');
          if (emergencyGuide) {
            return emergencyGuide;
          }

          const toolsPage = await caches.match('/know-her/tools/');
          if (toolsPage) {
            return toolsPage;
          }

          return caches.match('/know-her/');
        })
    );
    return;
  }

  // B. 静态资源 (图片 / 样式 / 脚本 / 字体) -> Cache-First
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }

      return fetch(request)
        .then((networkResponse) => {
          if (
            networkResponse &&
            networkResponse.status === 200 &&
            (networkResponse.type === 'basic' || networkResponse.type === 'cors')
          ) {
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
          }
          return networkResponse;
        })
        .catch(() => {
          // 静态资源在离线且无缓存时静默失败或由调用方处理
          return new Response('', { status: 408, statusText: 'Offline Resource Unavailable' });
        });
    })
  );
});
