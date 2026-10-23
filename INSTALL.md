# 安装与使用

## 1. 安装 Chrome 扩展

1. 解压本包。
2. 在 Chrome 地址栏打开 `chrome://extensions/`。
3. 打开右上角“开发者模式”。
4. 点击“加载已解压的扩展程序”，选择本包中的 `extension` 文件夹。

扩展可直接扫描当前页面已经加载的 `<video>` 和 Open Graph 视频地址，并调用 Chrome 下载。

## 2. 启动增强下载服务

首次使用先双击 `companion/setup.cmd` 安装 Python 依赖，并确认 FFmpeg/FFprobe 已加入 PATH。

双击 `companion/start-service.cmd`。窗口保持打开时，扩展可把当前页面发送给本机的 yt-dlp/Instaloader 下载器，并可自动提取关键帧。

默认输出目录：`D:\Codex\outputs\web-video-downloads`

任务结果保存在其 `jobs` 子目录。若 Instagram 要求登录，可在扩展中勾选 Chrome Cookie；Cookie 只由本机下载程序读取，不会由扩展上传。

## 限制

- 不支持 DRM、验证码、付费墙或无权访问的私密内容。
- Instagram 可能限制匿名访问；即使使用登录会话，也可能因平台限流而失败。
- Chrome 扩展不能直接运行 yt-dlp，因此增强模式必须保持本地伴侣服务运行。
