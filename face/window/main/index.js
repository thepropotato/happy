const { app, ipcMain, shell, systemPreferences } = require('electron')

const { Core } = require('./core')
const popover = require('./popover')
const trays = require('./tray')

const OPEN = '--open' // START WITH THE PANEL ALREADY DOWN.

const MACOS = 'darwin'

// HE COMES UP ON HIS OWN FOR A TURN, AND GOES AWAY AGAIN WHEN IT IS OVER.
const LINGER = 5000 // LONG ENOUGH TO READ THE LAST THING HE SAID.

const LISTENING = 'listening'
const IDLE = 'idle'

// WHERE MACOS KEEPS THE LIST HAPPY HAS TO BE ON TO HEAR THE KEY FROM ANYWHERE.
const PRIVACY = 'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'

const core = new Core()

let panel = null
let tray = null
let pinned = false

// A WINDOW BLURS ONCE ON THE WAY UP, BEFORE IT HAS EVER BEEN FOCUSED.
let focused = false

// WHAT HAPPY SAID BEFORE THE PAGE WAS READY TO HEAR IT.
let backlog = []
let listening = false

// OURS TO PUT AWAY. ONE THAT WAS OPENED ON PURPOSE STAYS OPEN.
let summoned = false
let leaving = null

if (process.platform === 'darwin') app.dock?.hide()

if (!app.requestSingleInstanceLock()) app.quit()

app.on('second-instance', () => show())

app.whenReady().then(() => {
  panel = popover.make(() => {
    if (pinned || !focused) return

    focused = false
    panel.hide()
  })

  panel.on('focus', () => {
    focused = true
  })

  panel.webContents.on('did-finish-load', () => {
    listening = true
    for (const word of backlog) panel.webContents.send('happy:event', word)
    backlog = []

    if (process.argv.includes(OPEN)) show()
  })

  panel.webContents.on('did-fail-load', (event, code, why) =>
    process.stderr.write(`panel would not load: ${why} (${code})\n`),
  )

  panel.webContents.on('console-message', (event) =>
    process.stderr.write(`panel: ${event.message} (${event.lineNumber})\n`),
  )

  tray = trays.make({ toggle, show, restart, quit })

  core.on('word', (word) => relay(word))
  core.on('gone', (why) => relay({ is: 'gone', ...why }))
  core.on('starting', () => relay({ is: 'state', state: 'loading' }))
  core.start()
})

app.on('window-all-closed', (event) => event.preventDefault()) // THE ICON IS THE APP.

app.on('before-quit', () => core.stop())

function relay(word) {
  if (listening && panel && !panel.isDestroyed()) panel.webContents.send('happy:event', word)
  else backlog.push(word)

  overheard(word)
}

function overheard(word) {
  if (!panel || word.is !== 'state') return

  if (word.state === LISTENING && !panel.isVisible()) rise()
  else if (word.state === IDLE) fade()
}

function rise() {
  popover.place(panel, tray)

  // NOT show(): TAKING THE FOCUS WOULD PULL THE CARET OUT OF ANOTHER WINDOW.
  panel.showInactive()
  panel.webContents.send('happy:event', { is: 'shown' })

  clearTimeout(leaving)
  summoned = true
}

function fade() {
  if (!summoned) return

  clearTimeout(leaving)

  leaving = setTimeout(() => {
    summoned = false

    if (!pinned && panel && !panel.isDestroyed() && !panel.isFocused()) panel.hide()
  }, LINGER)
}

function show() {
  if (!panel) return

  clearTimeout(leaving) // OPENED ON PURPOSE: NOT OURS TO PUT AWAY.
  summoned = false

  popover.place(panel, tray)
  panel.show()
  panel.focus()
  panel.webContents.send('happy:event', { is: 'shown' })
}

function toggle() {
  if (panel?.isVisible()) panel.hide()
  else show()
}

function restart() {
  backlog = []
  core.restart()
}

function quit() {
  core.stop()
  app.quit()
}

ipcMain.on('happy:order', (event, order) => core.ask(order))

ipcMain.on('happy:pin', (event, on) => {
  pinned = Boolean(on)
})

ipcMain.on('happy:hide', () => panel?.hide())
ipcMain.on('happy:restart', () => restart())
ipcMain.on('happy:quit', () => quit())

// MACOS GRANTS THE KEYBOARD BY WHOEVER STARTED THE PROCESS — THIS APP, NEVER
// PYTHON — SO THIS IS THE ONLY PLACE THAT CAN HONESTLY ASK FOR IT.
ipcMain.on('happy:allow', () => {
  if (process.platform !== MACOS) return

  systemPreferences.isTrustedAccessibilityClient(true)
  shell.openExternal(PRIVACY) // THE LIST ITSELF, FOR THE SECOND TIME ONWARDS.
})
