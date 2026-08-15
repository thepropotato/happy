const { app, ipcMain, shell, systemPreferences } = require('electron')

const { Core } = require('./core')
const blooms = require('./bloom')
const popover = require('./popover')
const trays = require('./tray')

const OPEN = '--open' // START WITH THE PANEL ALREADY DOWN.

const MACOS = 'darwin'

// HE COMES UP ON HIS OWN FOR A TURN, AND GOES AWAY AGAIN WHEN IT IS OVER.
const LINGER = 5000 // LONG ENOUGH TO READ THE LAST THING HE SAID.

const SLIDE = 220 // THE CAPSULE'S WAY OUT, WHICH IT NEEDS BEFORE IT IS HIDDEN.

// A TURN HAS STARTED WITHOUT ANYBODY OPENING ANYTHING. HIS NAME ON ITS OWN
// LEAVES HIM listening; HIS NAME AND THE WHOLE QUESTION IN ONE BREATH GOES
// STRAIGHT TO hearing, AND SHOWING NOTHING FOR THAT IS THE COMMON CASE MISSED.
const WOKEN = { listening: true, hearing: true }

const IDLE = 'idle'

// WHERE MACOS KEEPS THE LIST HAPPY HAS TO BE ON TO HEAR THE KEY FROM ANYWHERE.
const PRIVACY = 'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'

const core = new Core()

let panel = null
let bloom = null
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
let slipping = null

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

  bloom = blooms.make()

  tray = trays.make({ toggle, show, restart, quit })

  core.on('word', (word) => relay(word))
  core.on('gone', (why) => relay({ is: 'gone', ...why }))
  core.on('starting', () => relay({ is: 'state', state: 'loading' }))
  core.start()
})

app.on('window-all-closed', (event) => event.preventDefault()) // THE ICON IS THE APP.

app.on('before-quit', () => core.stop())

function relay(word) {
  // A PAGE BELONGS IN A BROWSER, NOT IN THE PANEL: THIS ONE IS WIDE AND IS READ
  // FOR A WHILE, AND THE PANEL PUTS ITSELF AWAY THE MOMENT IT LOSES FOCUS.
  if (word.is === 'open') {
    shell.openExternal(word.url)
    return
  }

  if (listening && panel && !panel.isDestroyed()) panel.webContents.send('happy:event', word)
  else backlog.push(word)

  if (bloom && !bloom.isDestroyed()) bloom.webContents.send('happy:event', word)

  overheard(word)
}

// HEARING HIS NAME IS NOT SOMEBODY ASKING TO SEE HIM. WHAT COMES UP UNASKED IS
// THE CAPSULE; THE PANEL ONLY EVER OPENS BECAUSE THIS PERSON OPENED IT.
function overheard(word) {
  if (!bloom || word.is !== 'state') return

  if (WOKEN[word.state]) rise()
  else if (word.state === IDLE) fade()
}

function rise() {
  if (panel?.isVisible()) return // THEY ARE ALREADY LOOKING AT THE REAL THING.

  clearTimeout(leaving)
  clearTimeout(slipping)

  if (!bloom.isVisible()) {
    blooms.place(bloom)
    bloom.showInactive() // TAKING THE FOCUS WOULD PULL THE CARET OUT OF THEIR WORK.
  }

  bloom.webContents.send('happy:event', { is: 'shown' })
  summoned = true
}

function fade() {
  if (!summoned) return

  clearTimeout(leaving)

  leaving = setTimeout(() => {
    summoned = false
    tuck()
  }, LINGER)
}

function tuck() {
  if (!bloom || bloom.isDestroyed() || !bloom.isVisible()) return

  clearTimeout(slipping)
  bloom.webContents.send('happy:event', { is: 'hiding' })

  slipping = setTimeout(() => bloom?.hide(), SLIDE)
}

function show() {
  if (!panel) return

  clearTimeout(leaving) // OPENED ON PURPOSE: NOT OURS TO PUT AWAY.
  summoned = false

  tuck() // THE CAPSULE WAS THE STAND IN FOR THIS, AND THIS IS HERE NOW.

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
ipcMain.on('happy:show', () => show())

// A LINK IN AN ANSWER GOES TO THEIR BROWSER. FOLLOWED IN HERE IT WOULD REPLACE
// THE PANEL WITH A WEB PAGE, AND THERE IS NOTHING TO GO BACK WITH.
ipcMain.on('happy:open', (event, url) => {
  if (/^https?:\/\//i.test(String(url))) shell.openExternal(url)
})

ipcMain.on('happy:restart', () => restart())
ipcMain.on('happy:quit', () => quit())

// MACOS GRANTS THE KEYBOARD BY WHOEVER STARTED THE PROCESS — THIS APP, NEVER
// PYTHON — SO THIS IS THE ONLY PLACE THAT CAN HONESTLY ASK FOR IT.
ipcMain.on('happy:allow', () => {
  if (process.platform !== MACOS) return

  systemPreferences.isTrustedAccessibilityClient(true)
  shell.openExternal(PRIVACY) // THE LIST ITSELF, FOR THE SECOND TIME ONWARDS.
})
