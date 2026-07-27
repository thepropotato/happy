// THE APP ITSELF: ONE ICON, ONE PANEL, AND HAPPY RUNNING BEHIND BOTH.

const { app, ipcMain } = require('electron')

const { Core } = require('./core')
const popover = require('./popover')
const trays = require('./tray')

const OPEN = '--open' // START WITH THE PANEL ALREADY DOWN. FOR WORKING ON IT.

const core = new Core()

let panel = null
let tray = null
let pinned = false

// A WINDOW BLURS ONCE ON THE WAY UP, BEFORE IT HAS EVER BEEN FOCUSED. HIDING ON
// THAT ONE WOULD MEAN THE PANEL VANISHING THE INSTANT IT APPEARED.
let focused = false

// EVERYTHING HAPPY SAYS BEFORE THE PAGE IS READY TO HEAR IT, SO STARTING UP IS
// NEVER MISSED BY A WINDOW THAT WAS STILL LOADING.
let backlog = []
let listening = false

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
}

function show() {
  if (!panel) return

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
