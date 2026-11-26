mm姬 1.3.2 源码

main.swift：原生 PDF 选择、拖入、密码输入和处理逻辑。
Installer.swift：安装到 /Applications，校验签名并在失败时恢复旧版。
worker.py：校验输出后替换原文件，保留扩展属性。
pdf_unlock.py：PDF 解密和签章外观保留逻辑。
Resources/Python.framework：随原安装包提供的第三方 Python、pypdf、PyCryptodome 运行时，已修复签名。第三方依赖以预编译形式附带，许可证位于其各自目录。

构建环境：macOS、Xcode 命令行工具。运行 ./build.sh /绝对路径/空输出目录。
产物同时包含 arm64 和 x86_64。已在本机 Apple Silicon 验证；未在 Intel 实机复测。
为适配本机仅包含 ARM 兼容静态库的工具链，构建禁用了旧 Swift 兼容库自动链接。界面使用 Foundation、AppKit 和 GCD，无 Swift async/await 依赖。旧版 macOS 仍需实机验证。

修复内容：
1. 重新签署修改过的 Python 和动态库，再由内向外签署框架和应用。
2. 运行时禁用 Python 字节码缓存写入，避免改变已签名的应用资源。
3. 文件替换前比较文件身份、大小、修改时间和原始内容，不将 macOS 访问元数据的 ctime 变化误判为内容变化。
4. 补齐可重建的原生界面与安装器源码，后台处理 PDF，失败时显示具体原因。

测试入口：应用二进制 --process /路径/测试.pdf。成功会原地替换，请使用副本。
worker 回归：内置 Python 运行 tests.py /绝对路径/mm姬.app/Contents/Resources。
