const { BrowserWindow, screen } = require('electron')
const path = require('node:path')

const WIDTH = 420
const HEIGHT = 720

const GAP = 8 // BETWEEN THE ICON AND THE PANEL.
const EDGE = 12 // THE CLOSEST IT EVER GETS TO THE SIDE OF A SCREEN.

function build() {
  return new BrowserWindow({
    width: WIDTH,
    height: HEIGHT,
    show: false,
    frame: false,
    transparent: true,
    resizable: false,
    movable: false,
    maximizable: false,
    fullscreenable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    hasShadow: true,
    backgroundColor: '#00000000',
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      spellcheck: false,
    },
  })
}

function make(onBlur) {
  const window = build()

  window.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'))
  window.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })

  // THE PLAIN FLOATING LEVEL SITS UNDER A FULL SCREEN APP.
  window.setAlwaysOnTop(true, 'screen-saver')

  window.on('blur', () => onBlur(window))

  return window
}

// HOW FAR DOWN A MENU BAR ICON CAN HONESTLY BE.
const MENU_BAR = 60

function place(window, tray) {
  const icon = tray?.getBounds?.() || { x: 0, y: 0, width: 0, height: 0 }
  const mac = process.platform === 'darwin'
  const work = screen.getDisplayMatching(icon.width ? icon : screen.getPrimaryDisplay().bounds).workArea

  // AN ICON SWALLOWED BY A CROWDED MENU BAR OR HIDDEN BEHIND A NOTCH STILL
  // REPORTS BOUNDS, AND THEY ARE NONSENSE.
  if (!icon.width || (mac && icon.y > work.y + MENU_BAR)) {
    const right = work.x + work.width - WIDTH - EDGE
    window.setPosition(right, mac ? work.y + EDGE : work.y + work.height - HEIGHT - EDGE)
    return
  }

  const middle = Math.round(icon.x + icon.width / 2 - WIDTH / 2)
  const under = icon.y < work.y + work.height / 2
  const above = Math.round(under ? icon.y + icon.height + GAP : icon.y - HEIGHT - GAP)

  window.setPosition(
    hemmed(middle, work.x + EDGE, work.x + work.width - WIDTH - EDGE),
    hemmed(above, work.y + EDGE, work.y + work.height - HEIGHT - EDGE),
  )
}

function hemmed(value, least, most) {
  return Math.round(Math.min(Math.max(value, least), Math.max(least, most)))
}

module.exports = { make, place, WIDTH, HEIGHT }
