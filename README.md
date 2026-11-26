# mm姬

macOS 本地 PDF 解锁工具，界面和安装器支持 Apple Silicon 与 Intel。处理在本机完成，校验成功后替换原文件。

## 下载和使用

1. 在 [Releases](https://github.com/qk000416-sys/MMJi-macOS/releases/latest) 下载 `MMJi-v1.3.2-Installer.zip`，用 macOS 归档实用工具解压。
2. 双击「mm姬 安装器.app」，点击「安装到应用程序」。
3. 将 PDF 拖到 `/Applications/mm姬.app`，或打开应用选择 PDF；设置了打开密码的文件需要输入正确密码。

处理成功后会替换原文件，建议先保留副本。支持不超过 50 MB 的 PDF。保留页面内容和可见签章外观，重写后的文件不保留原数字签名的密码学校验效力。应用使用本地签名，尚未经过 Apple 公证。

## 1.3.2 修复

- 修复修改内置 Python 后签名失效，导致 Apple Silicon 终止处理程序的问题。
- 禁止运行时生成应用内 Python 缓存，保持资源签名有效。
- 以文件身份、大小、修改时间和内容判断并发修改，避免把访问元数据变化误判为 PDF 内容变化。
- 提供原生 Swift 界面、安装器、构建脚本与回归测试。

## 构建

需要 macOS 和 Xcode 命令行工具。运行 `./build.sh /绝对路径/空输出目录`，生成应用和安装器。

仓库保存项目源码；缺少运行时和图标时，构建脚本会下载本项目 Release 的固定版本完整源码包，验证 SHA-256 后提取依赖，并验证框架签名。

也可下载 Release 中的 `MMJi-v1.3.2-Source.zip`，其中包含完整源码、图标和预编译第三方运行时，解压后无需下载依赖即可构建。第三方组件许可证位于各自运行时目录。

界面使用 Foundation、AppKit 和 GCD。为适配本机工具链，构建禁用了旧 Swift 兼容静态库的自动链接。已在 Apple Silicon 验证；Intel 实机及旧版 macOS 未在本次复测。

## 验证

使用应用内 Python 运行 `tests.py`，参数为应用的 `Contents/Resources` 绝对路径。测试覆盖 AES-256、RC4、打开密码、错误密码不替换、普通 PDF、签章外观、元数据变化和并发内容修改。

原生处理入口为 `mm姬.app/Contents/MacOS/PDFUnlock --process /测试副本.pdf`，会原地替换测试文件。
