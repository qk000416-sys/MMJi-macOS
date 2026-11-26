import AppKit
import Foundation

struct WorkerResult: Decodable { var ok: Bool?; var error: String?; var code: String? }
func processPDF(_ url: URL, password: String) -> WorkerResult {
    guard let resources = Bundle.main.resourceURL else { return WorkerResult(error: "缺少应用资源。") }
    let process = Process()
    process.executableURL = resources.appendingPathComponent("Python.framework/Versions/3.13/bin/python3.13-runtime")
    process.arguments = ["-B", resources.appendingPathComponent("worker.py").path, url.path]
    var env = ProcessInfo.processInfo.environment
    env["PYTHONHOME"] = resources.appendingPathComponent("Python.framework/Versions/3.13").path
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    process.environment = env
    let input = Pipe(), output = Pipe(), errors = Pipe()
    process.standardInput = input; process.standardOutput = output; process.standardError = errors
    do {
        try process.run()
        input.fileHandleForWriting.write(try JSONSerialization.data(withJSONObject: ["password": password]))
        try input.fileHandleForWriting.close()
        // Drain stderr concurrently so malformed PDFs cannot fill the pipe.
        DispatchQueue.global().async { _ = errors.fileHandleForReading.readDataToEndOfFile() }
        let data = output.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()
        if let result = try? JSONDecoder().decode(WorkerResult.self, from: data) { return result }
        return WorkerResult(error: "处理程序退出（状态 \(process.terminationStatus)），原文件未被替换。")
    } catch { return WorkerResult(error: error.localizedDescription) }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    var busy = false
    var queue: [URL] = []
    func application(_ sender: NSApplication, openFiles filenames: [String]) {
        queue += filenames.map { URL(fileURLWithPath: $0) }
        sender.reply(toOpenOrPrint: .success)
        runNext()
    }
    func applicationDidFinishLaunching(_ notification: Notification) {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            if !self.busy && self.queue.isEmpty {
                let panel = NSOpenPanel(); panel.allowedFileTypes = ["pdf"]; panel.allowsMultipleSelection = true
                panel.message = "选择需要解锁的 PDF，处理成功后替换原文件。"
                NSApp.activate(ignoringOtherApps: true)
                if panel.runModal() == .OK { self.queue += panel.urls; self.runNext() }
                else { NSApp.terminate(nil) }
            }
        }
    }
    func runNext() {
        guard !busy else { return }
        guard !queue.isEmpty else { NSApp.terminate(nil); return }
        busy = true
        let url = queue.removeFirst()
        handle(url, password: "")
    }
    func handle(_ url: URL, password: String) {
        DispatchQueue.global(qos: .userInitiated).async {
            let result = processPDF(url, password: password)
            DispatchQueue.main.async {
                if result.code == "password_required" || result.code == "password_incorrect" {
                    let alert = NSAlert(); alert.messageText = "请输入 \(url.lastPathComponent) 的密码"
                    alert.informativeText = result.error ?? ""; alert.addButton(withTitle: "解锁"); alert.addButton(withTitle: "取消")
                    let field = NSSecureTextField(frame: NSRect(x: 0, y: 0, width: 300, height: 24)); alert.accessoryView = field
                    NSApp.activate(ignoringOtherApps: true)
                    if alert.runModal() == .alertFirstButtonReturn { self.handle(url, password: field.stringValue); return }
                } else if result.ok != true {
                    let alert = NSAlert(); alert.messageText = "未能解锁 \(url.lastPathComponent)"; alert.informativeText = result.error ?? "未知错误。"
                    alert.addButton(withTitle: "好"); NSApp.activate(ignoringOtherApps: true); alert.runModal()
                }
                self.busy = false; self.runNext()
            }
        }
    }
}

if CommandLine.arguments.dropFirst().first == "--process", CommandLine.arguments.count == 3 {
    let result = processPDF(URL(fileURLWithPath: CommandLine.arguments[2]), password: "")
    if let data = try? JSONSerialization.data(withJSONObject: ["ok": result.ok == true, "error": result.error ?? ""]) {
        FileHandle.standardOutput.write(data)
    }
    exit(result.ok == true ? 0 : 1)
}
let application = NSApplication.shared
let delegate = AppDelegate()
application.delegate = delegate
application.setActivationPolicy(.accessory)
application.run()
