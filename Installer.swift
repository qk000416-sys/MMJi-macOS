import AppKit
import Foundation

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
app.activate(ignoringOtherApps: true)
let alert = NSAlert()
alert.messageText = "安装 mm姬 1.3.2"
alert.informativeText = "兼容 Apple 芯片和 Intel Mac。安装后，将 PDF 拖到 mm姬 图标即可解锁。处理成功后替换原文件。"
alert.addButton(withTitle: "安装到应用程序"); alert.addButton(withTitle: "取消")
if alert.runModal() == .alertFirstButtonReturn {
    do {
        let fm = FileManager.default
        let source = Bundle.main.resourceURL!.appendingPathComponent("mm姬.app")
        let destination = URL(fileURLWithPath: "/Applications/mm姬.app")
        let stage = destination.deletingLastPathComponent().appendingPathComponent(".mm-install-" + UUID().uuidString + ".app")
        let backup = destination.deletingLastPathComponent().appendingPathComponent(".mm-backup-" + UUID().uuidString + ".app")
        defer { try? fm.removeItem(at: stage) }
        try fm.copyItem(at: source, to: stage)
        let verify = Process(); verify.executableURL = URL(fileURLWithPath: "/usr/bin/codesign")
        verify.arguments = ["--verify", "--deep", "--strict", stage.path]; try verify.run(); verify.waitUntilExit()
        guard verify.terminationStatus == 0 else { throw NSError(domain: "MMInstaller", code: 1, userInfo: [NSLocalizedDescriptionKey: "安装包签名校验失败。请重新解压安装包。"] ) }
        let existed = fm.fileExists(atPath: destination.path)
        if existed { try fm.moveItem(at: destination, to: backup) }
        do { try fm.moveItem(at: stage, to: destination) }
        catch { if existed { try? fm.moveItem(at: backup, to: destination) }; throw error }
        if existed { try? fm.trashItem(at: backup, resultingItemURL: nil) }
        let done = NSAlert(); done.messageText = "mm姬 安装完成"; done.informativeText = "应用位于 /Applications/mm姬.app。可将 PDF 拖到应用图标，或双击应用选择文件。"; done.runModal()
    } catch {
        let failure = NSAlert(); failure.messageText = "未能安装 mm姬"; failure.informativeText = error.localizedDescription; failure.runModal()
    }
}
