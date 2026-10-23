const $ = (id) => document.getElementById(id);
let currentTab;

async function activeTab() {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  return tab;
}

async function scanPage() {
  $("status").textContent = "正在扫描页面中的媒体元素…";
  $("results").replaceChildren();
  try {
    const [{result}] = await chrome.scripting.executeScript({
      target: {tabId: currentTab.id},
      func: () => {
        const found = new Map();
        const add = (url, label, width = 0, height = 0) => {
          if (!url || !/^https?:/i.test(url)) return;
          found.set(url, {url, label, width, height});
        };
        document.querySelectorAll("video").forEach((v, i) => {
          add(v.currentSrc || v.src, `视频 ${i + 1}`, v.videoWidth, v.videoHeight);
          v.querySelectorAll("source").forEach(s => add(s.src, `视频源 ${i + 1}`));
        });
        ["og:video", "og:video:url", "og:video:secure_url", "twitter:player:stream"].forEach(key => {
          const node = document.querySelector(`meta[property="${key}"],meta[name="${key}"]`);
          if (node) add(node.content, key);
        });
        return [...found.values()];
      }
    });
    renderResults(result || []);
  } catch (error) {
    $("status").textContent = `无法扫描此页面：${error.message}`;
  }
}

function renderResults(items) {
  if (!items.length) {
    $("status").textContent = "未发现可直接下载的媒体地址，可尝试本机增强下载。";
    return;
  }
  $("status").textContent = `发现 ${items.length} 个媒体地址。`;
  items.forEach((item, index) => {
    const box = document.createElement("div");
    box.className = "item";
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `${item.label}${item.width ? ` · ${item.width}×${item.height}` : ""}`;
    const button = document.createElement("button");
    button.textContent = "直接下载";
    button.addEventListener("click", async () => {
      const name = `web-video-${Date.now()}-${index + 1}.mp4`;
      try {
        await chrome.downloads.download({url: item.url, filename: `WebVideoDownloads/${name}`, conflictAction: "uniquify", saveAs: true});
        $("status").textContent = "下载任务已提交给 Chrome。";
      } catch (error) {
        $("status").textContent = `直接下载失败：${error.message}`;
      }
    });
    box.append(meta, button);
    $("results").append(box);
  });
}

async function checkService() {
  try {
    const response = await fetch("http://127.0.0.1:17832/health", {signal: AbortSignal.timeout(1200)});
    if (!response.ok) throw new Error(String(response.status));
    $("service").textContent = "已连接";
    $("service").className = "badge ok";
    return true;
  } catch {
    $("service").textContent = "未启动";
    $("service").className = "badge bad";
    return false;
  }
}

async function localDownload() {
  if (!(await checkService())) {
    $("status").textContent = "请先运行 companion/start-service.cmd。";
    return;
  }
  const instagramUser = $("instagramUser").value.trim();
  await chrome.storage.local.set({instagramUser});
  $("localDownload").disabled = true;
  $("status").textContent = "本机下载器正在处理；可关闭此窗口。";
  try {
    const response = await fetch("http://127.0.0.1:17832/download", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        url: currentTab.url,
        frames: $("frames").checked,
        cookiesFromBrowser: $("cookies").checked ? "chrome" : null,
        instagramUser: instagramUser || null
      })
    });
    const data = await response.json();
    $("status").textContent = data.accepted ? `任务已开始：${data.jobId}` : `提交失败：${data.error || "未知错误"}`;
  } catch (error) {
    $("status").textContent = `无法连接本机下载器：${error.message}`;
  } finally {
    $("localDownload").disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  currentTab = await activeTab();
  $("host").textContent = currentTab?.url ? new URL(currentTab.url).hostname : "无法读取页面";
  const saved = await chrome.storage.local.get("instagramUser");
  $("instagramUser").value = saved.instagramUser || "";
  $("scan").addEventListener("click", scanPage);
  $("localDownload").addEventListener("click", localDownload);
  await checkService();
});
