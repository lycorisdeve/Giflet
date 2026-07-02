# Giflet

一个用于把抖音/字节 `.awebp` 动态表情链接或本地图片提取为 `.gif` 的小工具。

Giflet is a small tool for extracting GIF files from Douyin/ByteDance `.awebp` animated emote links or local image files.

## 缘起 / Why this exists

我只是想把抖音里的 GIF 表情保存下来，在其他社交场景里继续使用，但页面上没有找到直接保存按钮。于是最终由 Codex 协助开发了这款小工具。

I built this because I wanted to save Douyin GIF emotes for use in other social apps, but could not find a direct save button. Codex helped turn that small need into this tool.

## 免责声明 / Disclaimer

Giflet 仅用于个人学习、格式转换和个人备份场景。请尊重原作者、平台规则和相关版权，不要将提取结果用于侵权、商用盗用、二次分发等用途。

如果本项目或相关说明涉及侵权，请联系我删除。

Giflet is intended for personal learning, format conversion, and personal backup use only. Please respect original creators, platform rules, and copyright. Do not use extracted files for infringement, unauthorized commercial use, or redistribution.

If this project or its documentation infringes your rights, please contact me and I will remove the relevant content.

## 功能

- 粘贴一个或多个 `.awebp` 链接
- 选择本地 `.awebp` / `.webp` / `.gif` / 常见图片文件
- 自动下载原始 `.awebp`
- 转换为循环播放的 `.gif`
- 保留原始文件和导出的 GIF
- 桌面 GUI 内预览导出的 GIF
- 本地 Web 页面支持上传图片或粘贴链接
- 支持中文 / English 界面切换
- 支持命令行批量处理
- 支持用 PyInstaller 打包成 Windows EXE

## 获取图片链接 / Get the image link

在网页里获取 `.awebp` 链接的一种方式：

1. 打开包含目标表情的页面。
2. 按 `F12` 打开开发者工具。
3. 使用选择元素工具，点选目标图片。
4. 在 Elements / Network 中找到图片地址。
5. 复制以 `.awebp`、`.webp` 或相关图片服务地址结尾的链接。
6. 粘贴到 Giflet 的“粘贴链接”输入框中。

One way to get the image link:

1. Open the page that contains the emote.
2. Press `F12` to open Developer Tools.
3. Use the element picker and select the image.
4. Find the image URL in Elements or Network.
5. Copy the `.awebp`, `.webp`, or related image-service URL.
6. Paste it into Giflet's link input.

## 方式一：桌面 GUI

```powershell
cd E:\OmniProject\Omni\tools\awebp-gif-extractor
python app.py
```

或者双击 `run.bat`。

桌面 GUI 支持两种输入：

- 点击 `Add images` 选择本地图片
- 在文本框里粘贴一个或多个图片链接

## 方式二：Web 页面

```powershell
cd E:\OmniProject\Omni\tools\awebp-gif-extractor
python web_app.py
```

或者双击 `start_web.bat`。

默认会打开：

```text
http://127.0.0.1:8765/
```

Web 页面支持：

- 上传本地图片并转换
- 粘贴远程图片链接并转换
- 在页面右侧预览和下载生成的 GIF

## 打包成 EXE

```powershell
cd E:\OmniProject\Omni\tools\awebp-gif-extractor
.\build_exe.bat
```

生成位置：

```text
dist\Giflet\Giflet.exe
```

这个 EXE 默认打包的是桌面 GUI 版本。打包需要联网安装 `pyinstaller`，只在构建时需要。

## 命令行用法

```powershell
python app.py --url "https://example.com/image.awebp?x=1" --output exports
```

多个链接可以重复传入 `--url`：

```powershell
python app.py --url "https://example.com/one.awebp" --url "https://example.com/two.awebp"
```

本地图片：

```powershell
python app.py --image "C:\path\to\image.awebp" --output exports
```

## 依赖

程序使用 Python 标准库负责下载、GUI 和本地 Web 服务，使用 Pillow 负责解码 animated WebP 并导出 GIF。

```powershell
pip install -r requirements.txt
```

## CI/CD

仓库内置 GitHub Actions：

- `.github/workflows/ci.yml`：推送到 `master` 或 PR 时，运行 Python 3.10/3.11/3.12 编译检查、单元测试和 Docker 构建检查。
- `.github/workflows/release.yml`：推送 `v*` tag 时自动发布。

发布流程会生成：

- GitHub Release
- Windows EXE 压缩包：`Giflet-windows-x64.zip`
- Python wheel / sdist
- GitHub Packages / GHCR 镜像：`ghcr.io/lycorisdeve/giflet`

发布新版本：

```powershell
git tag v0.1.4
git push origin v0.1.4
```

GitHub Actions 会自动完成 Release 和 Packages 发布。
