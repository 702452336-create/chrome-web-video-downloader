# Chrome Web Video Downloader

一个面向 Windows 的 Chrome Manifest V3 扩展：优先下载当前页面已经加载的视频；遇到 Instagram 或隐藏媒体地址时，可调用本机伴侣服务，以 `yt-dlp → Instaloader` 的顺序尝试下载，并通过 FFprobe 验证视频、按需使用 FFmpeg 提取关键帧。

> 仅用于你有权访问和保存的内容。本项目不绕过 DRM、验证码、付费墙或账户权限。

## 功能

- 扫描当前页面的 `<video>`、`<source>` 和 Open Graph 视频地址
- 使用 Chrome 下载 API 保存浏览器已加载的视频
- 本机增强下载：yt-dlp 优先、Instaloader 作为 Instagram 回退
- 可选复用 Chrome 登录 Cookie；不会上传 Cookie
- FFprobe 验证下载结果是否包含视频流
- FFmpeg 基于场景变化提取代表性关键帧
- 本地服务仅监听 `127.0.0.1:17832`，下载接口只接受 Chrome 扩展来源

## 安装

### 1. 安装本地依赖

需要 Python 3.10+、FFmpeg 和 FFprobe。双击：

```text
companion/setup.cmd
```

### 2. 安装 Chrome 扩展

1. Chrome 打开 `chrome://extensions/`。
2. 开启“开发者模式”。
3. 点击“加载已解压的扩展程序”。
4. 选择本项目的 `extension` 文件夹。

## 使用

普通页面：打开目标网页 → 点击扩展 → “扫描当前页面” → “直接下载”。

如果页面使用 `blob:` 媒体地址（Instagram 等站点常见），直接扫描不会显示可下载文件，请使用增强模式。

增强模式：双击 `companion/start-service.cmd` 并保持窗口开启，然后在扩展中选择是否提取关键帧、是否使用 Chrome Cookie，再点击“交给本机下载器”。

默认输出位置：

```text
D:\Codex\outputs\web-video-downloads
```

更多说明见 [INSTALL.md](INSTALL.md)。

## 项目结构

```text
extension/               Chrome Manifest V3 扩展
companion/service.py     仅监听回环地址的本地 HTTP 服务
companion/fetch_video.py 下载、回退、验证和抽帧流程
companion/setup.cmd      安装 Python 依赖
companion/start-service.cmd
```

## 已知限制

- Chrome 扩展不能直接执行本机程序，增强模式必须启动伴侣服务。
- Instagram 会改变接口并限制匿名请求，下载成功率取决于页面可访问性和有效会话。
- 使用 `--cookies-from-browser` 时，浏览器或系统的 Cookie 加密/文件锁可能导致读取失败。
- 联系表仅在系统安装 ImageMagick 时生成；单独的关键帧不受影响。

## License

[MIT](LICENSE)
