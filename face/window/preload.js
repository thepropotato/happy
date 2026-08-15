const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('happy', {
  hears: (handler) => ipcRenderer.on('happy:event', (event, word) => handler(word)),
  ask: (order) => ipcRenderer.send('happy:order', order),
  pin: (on) => ipcRenderer.send('happy:pin', on),
  allow: () => ipcRenderer.send('happy:allow'),
  hide: () => ipcRenderer.send('happy:hide'),
  open: (url) => ipcRenderer.send('happy:open', url),
  restart: () => ipcRenderer.send('happy:restart'),
  quit: () => ipcRenderer.send('happy:quit'),
})
