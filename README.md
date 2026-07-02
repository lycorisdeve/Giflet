# Giflet

一个用于把抖音/字节 `.awebp` 动态表情链接或本地图片提取为 `.gif` 的小工具。

## 功能

- 粘贴一个或多个 `.awebp` 链接
- 选择本地 `.awebp` / `.webp` / `.gif` / 常见图片文件
- 自动下载原始 `.awebp`
- 转换为循环播放的 `.gif`
- 保留原始文件和导出的 GIF
- 桌面 GUI 内预览导出的 GIF
- 本地 Web 页面支持上传图片或粘贴链接
- 支持命令行批量处理
- 支持用 PyInstaller 打包成 Windows EXE

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
