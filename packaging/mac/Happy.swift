// Happy.app's executable. When Happy is set up for this version it hands straight over to launch.sh, which runs him.
// The first time, and after an update, it first shows a small window with what is being installed, so the Mac is
// never silent for minutes, and opens Happy only once everything he needs to listen and talk is on this Mac.
import AppKit

let files = FileManager.default
let resources = Bundle.main.resourcePath!
let launcher = resources + "/launch.sh"
let home = ProcessInfo.processInfo.environment["HAPPY_HOME"] ?? (NSHomeDirectory() + "/.happy")
let app = home + "/app"
let logPath = home + "/install.log"

func contents(_ path: String) -> String? {
    (try? String(contentsOfFile: path, encoding: .utf8))?.trimmingCharacters(in: .whitespacesAndNewlines)
}

func runHappy(_ extra: [String]) -> Never {
    // WHERE THIS APP LIVES, SO HAPPY CAN REPLACE IT WITH A NEWER ONE WHEN AN UPDATE COMES.
    setenv("HAPPY_BUNDLE", Bundle.main.bundlePath, 1)
    // EXEC, NOT A CHILD PROCESS: HAPPY STAYS THIS APP TO MACOS, SO THE MICROPHONE PROMPT NAMES "HAPPY".
    let argv = (["/bin/bash", launcher] + extra).map { strdup($0) } + [nil]
    execv("/bin/bash", argv)
    let alert = NSAlert()
    alert.messageText = "Happy couldn't start"
    alert.informativeText = "Its launcher could not be run (\(String(cString: strerror(errno))))."
    alert.runModal()
    exit(1)
}

let wanted = contents(resources + "/app/.app-version") ?? ""
if !wanted.isEmpty && contents(app + "/.app-version") == wanted && files.isExecutableFile(atPath: app + "/.venv/bin/python") {
    runHappy([])
}
let fresh = !files.fileExists(atPath: app + "/.venv")
// AN UPDATE SAYS SO, AND WHICH VERSION; ONLY A FIRST OPEN IS "GETTING HAPPY READY".
let title = fresh ? "Getting Happy ready" : "Updating Happy to \(wanted)"
let blurb = fresh ? "This happens once and takes a few minutes, mostly downloading. Happy opens by himself when it's done."
                  : "Getting what the new version needs. Happy opens by himself when it's done."

// WHERE EACH STEP OF setup.sh AND `happy prepare` STARTS, SO THE BAR CAN CREEP TOWARDS THE NEXT ONE MEANWHILE.
let milestones: [Double] = [1, 2, 5, 10, 14, 50, 86, 96, 100]

final class Setup: NSObject, NSApplicationDelegate, NSWindowDelegate {
    var window: NSWindow!
    let heading = NSTextField(labelWithString: title)
    let status = NSTextField(labelWithString: "Starting…")
    let note = NSTextField(wrappingLabelWithString: blurb)
    let bar = NSProgressIndicator()
    let spinner = NSProgressIndicator()
    let retry = NSButton(title: "Try Again", target: nil, action: nil)
    let details = NSButton(title: "Show Details", target: nil, action: nil)
    let quit = NSButton(title: "Quit", target: nil, action: nil)
    var process: Process?
    var log: FileHandle?
    var pending = ""
    var problem = ""
    var reached = 0.0
    var creep: Timer?
    var finishing = false
    let busyStatus = NSRect(x: 126, y: 120, width: 330, height: 18)

    func applicationDidFinishLaunching(_ note: Notification) {
        NSApp.setActivationPolicy(.regular)
        buildMenu()
        buildWindow()
        NSApp.activate(ignoringOtherApps: true)
        start()
    }

    func buildMenu() {
        let main = NSMenu()
        let item = NSMenuItem()
        main.addItem(item)
        let menu = NSMenu()
        menu.addItem(withTitle: "Quit Happy", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        item.submenu = menu
        NSApp.mainMenu = main
    }

    func buildWindow() {
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 480, height: 196),
                          styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        window.title = "Happy"
        window.isReleasedWhenClosed = false
        window.delegate = self
        let view = window.contentView!

        let icon = NSImageView(frame: NSRect(x: 24, y: 104, width: 64, height: 64))
        icon.image = NSApp.applicationIconImage
        view.addSubview(icon)

        heading.font = .systemFont(ofSize: 17, weight: .semibold)
        heading.frame = NSRect(x: 104, y: 144, width: 352, height: 24)
        view.addSubview(heading)

        spinner.style = .spinning
        spinner.controlSize = .small
        spinner.frame = NSRect(x: 104, y: 121, width: 16, height: 16)
        spinner.startAnimation(nil)
        view.addSubview(spinner)

        status.font = .systemFont(ofSize: 13)
        status.textColor = .secondaryLabelColor
        status.lineBreakMode = .byTruncatingTail
        status.frame = busyStatus
        view.addSubview(status)

        bar.style = .bar
        bar.isIndeterminate = false
        bar.minValue = 0
        bar.maxValue = 100
        bar.frame = NSRect(x: 104, y: 96, width: 352, height: 20)
        view.addSubview(bar)

        note.font = .systemFont(ofSize: 12)
        note.textColor = .secondaryLabelColor
        note.frame = NSRect(x: 104, y: 52, width: 352, height: 36)
        view.addSubview(note)

        for (button, x, action) in [(quit, 104.0, #selector(quitNow)), (details, 220.0, #selector(showDetails)),
                                    (retry, 356.0, #selector(tryAgain))] {
            button.target = self
            button.action = action
            button.bezelStyle = .rounded
            button.frame = NSRect(x: x, y: 14, width: button == details ? 130 : 100, height: 30)
            button.isHidden = true
            view.addSubview(button)
        }
        retry.keyEquivalent = "\r"

        window.center()
        window.makeKeyAndOrderFront(nil)
    }

    func start() {
        if log == nil {
            // ONE HANDLE FOR THE APP'S LIFE: A STRAY WRITE AFTER A CLOSE WOULD BE AN EXCEPTION, NOT A LOST LINE.
            try? files.createDirectory(atPath: home, withIntermediateDirectories: true)
            if !files.fileExists(atPath: logPath) { files.createFile(atPath: logPath, contents: nil) }
            log = FileHandle(forWritingAtPath: logPath)
            log?.seekToEndOfFile()
        }

        problem = ""
        pending = ""
        reached = 0
        bar.doubleValue = 0
        bar.isHidden = false
        status.frame = busyStatus
        status.maximumNumberOfLines = 1
        status.lineBreakMode = .byTruncatingTail
        status.textColor = .secondaryLabelColor
        heading.stringValue = title
        status.stringValue = "Starting…"
        note.stringValue = blurb
        for button in [retry, details, quit] { button.isHidden = true }
        spinner.isHidden = false
        spinner.startAnimation(nil)

        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/bin/bash")
        task.arguments = [launcher, "setup"]
        let pipe = Pipe()
        task.standardOutput = pipe
        task.standardError = pipe
        task.standardInput = FileHandle.nullDevice
        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else { handle.readabilityHandler = nil; return }
            self?.log?.write(data)
            let text = String(decoding: data, as: UTF8.self)
            DispatchQueue.main.async { self?.read(text) }
        }
        task.terminationHandler = { [weak self] done in
            // A MOMENT FOR THE LAST LINES TO ARRIVE, SINCE THEY CARRY THE REASON FOR A FAILURE.
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) { self?.ended(done.terminationStatus) }
        }
        do {
            try task.run()
            process = task
        } catch {
            problem = "The setup could not be started (\(error.localizedDescription))."
            ended(1)
            return
        }
        creep?.invalidate()
        creep = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in self?.inch() }
    }

    func read(_ text: String) {
        pending += text
        while let end = pending.firstIndex(of: "\n") {
            let line = String(pending[..<end]).trimmingCharacters(in: .whitespaces)
            pending = String(pending[pending.index(after: end)...])
            if line.hasPrefix("::error ") {
                problem = String(line.dropFirst(8))
            } else if line.hasPrefix(":: ") {
                let parts = line.dropFirst(3).split(separator: " ", maxSplits: 1)
                if let percent = Double(parts.first ?? ""), parts.count == 2 {
                    reached = max(reached, percent)
                    bar.doubleValue = max(bar.doubleValue, percent)
                    status.stringValue = String(parts[1])
                }
            }
        }
    }

    func inch() {
        // THE LONGEST STEPS SAY NOTHING FOR MINUTES; A BAR THAT STILL MOVES TELLS YOU NOTHING HAS FROZEN.
        let ceiling = (milestones.first { $0 > reached } ?? 100) - 0.5
        if bar.doubleValue < ceiling { bar.doubleValue += (ceiling - bar.doubleValue) * 0.012 }
    }

    func ended(_ code: Int32) {
        creep?.invalidate()
        process = nil
        if code == 0 {
            finishing = true
            bar.doubleValue = 100
            status.stringValue = "Happy is ready"
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) { runHappy(fresh ? ["--settings"] : []) }
            return
        }
        spinner.stopAnimation(nil)
        spinner.isHidden = true
        bar.isHidden = true
        heading.stringValue = "Happy couldn't finish setting up"
        // THE REASON TAKES THE BAR'S PLACE AND WRAPS, SINCE IT IS WHAT THE PERSON NEEDS TO READ WHOLE.
        status.lineBreakMode = .byWordWrapping
        status.maximumNumberOfLines = 3
        status.textColor = .labelColor
        status.frame = NSRect(x: 104, y: 90, width: 352, height: 50)
        status.stringValue = problem.isEmpty ? "Setup stopped partway." : problem
        note.stringValue = "Nothing is lost: trying again picks up where it stopped. The details are in ~/.happy/install.log."
        for button in [retry, details, quit] { button.isHidden = false }
        NSApp.requestUserAttention(.criticalRequest)
    }

    @objc func tryAgain() { start() }

    @objc func showDetails() { NSWorkspace.shared.open(URL(fileURLWithPath: logPath)) }

    @objc func quitNow() { NSApp.terminate(nil) }

    func windowWillClose(_ notification: Notification) { NSApp.terminate(nil) }

    func applicationWillTerminate(_ notification: Notification) {
        // CLOSING THE WINDOW STOPS THE SETUP; WHAT IT ALREADY FETCHED STAYS FOR NEXT TIME.
        if let task = process, task.isRunning, !finishing { task.terminate() }
    }
}

let application = NSApplication.shared
let setup = Setup()
application.delegate = setup
application.run()
