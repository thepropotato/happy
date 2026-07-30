const { Menu, Tray, nativeImage } = require('electron')
const path = require('node:path')

const ASSETS = path.join(__dirname, '..', 'assets')

// MACOS TINTS A TEMPLATE IMAGE ITSELF, LIGHT MENU BAR OR DARK. NOWHERE ELSE DOES.
const ICONS = { darwin: 'trayTemplate.png', other: 'tray-light.png' }

function picture() {
  const file = process.platform === 'darwin' ? ICONS.darwin : ICONS.other
  const image = nativeImage.createFromPath(path.join(ASSETS, file))

  if (process.platform === 'darwin') image.setTemplateImage(true)

  return image
}

function make(doing) {
  const tray = new Tray(picture())

  tray.setToolTip('Happy')
  tray.on('click', () => doing.toggle())
  tray.on('right-click', () => tray.popUpContextMenu(menu(doing)))

  return tray
}

function menu(doing) {
  return Menu.buildFromTemplate([
    { label: 'Show Happy', click: () => doing.show() },
    { type: 'separator' },
    { label: 'Restart Happy', click: () => doing.restart() },
    { type: 'separator' },
    { label: 'Quit', accelerator: 'CommandOrControl+Q', click: () => doing.quit() },
  ])
}

module.exports = { make }
