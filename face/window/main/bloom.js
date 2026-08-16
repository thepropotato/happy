// WHAT HAPPY SHOWS WHEN NOBODY ASKED TO SEE HIM. HOLDING THE KEY IS NOT A
// REQUEST FOR THE WHOLE PANEL, SO A CAPSULE THE SIZE OF A NOTIFICATION SITS AT
// THE TOP OF THE SCREEN FOR THE LENGTH OF THE TURN AND THEN GOES AWAY AGAIN.

const { BrowserWindow, screen } = require('electron')
const path = require('node:path')

const WIDTH = 380
const HEIGHT = 108 // THE CAPSULE IS SHORTER THAN THIS: THE REST IS ITS GLOW.

const TOP = 10 // BELOW THE MENU BAR, NOT UNDER IT.

function build() {
  return new BrowserWindow({
    width: WIDTH,
    height: HEIGHT,
    show: false,
    frame: false,
    transparent: true,
    resizable: false,
    movable: false,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    hasShadow: false,
    // IT COMES UP WHILE SOMEBODY IS TYPING SOMEWHERE ELSE. TAKING THE FOCUS
    // WOULD PULL THE CARET OUT OF WHATEVER THEY WERE HALFWAY THROUGH.
    focusable: false,
    acceptFirstMouse: true,
    backgroundColor: '#00000000',
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      spellcheck: false,
    },
  })
}

function make() {
  const window = build()

  window.loadFile(path.join(__dirname, '..', 'renderer', 'bloom.html'))
  window.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })
  window.setAlwaysOnTop(true, 'screen-saver')

  return window
}

// WHERE THE PERSON IS LOOKING, WHICH IS THE SCREEN THEIR POINTER IS ON RATHER
// THAN WHICHEVER ONE THE SYSTEM CALLS FIRST.
function place(window) {
  const here = screen.getDisplayNearestPoint(screen.getCursorScreenPoint())
  const work = here.workArea

  window.setPosition(
    Math.round(work.x + work.width / 2 - WIDTH / 2),
    Math.round(work.y + TOP),
  )
}

module.exports = { make, place, WIDTH, HEIGHT }
