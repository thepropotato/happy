// window.happy OVER QT'S WEB CHANNEL: THE PAGE ASKS PYTHON, PYTHON TELLS THE PAGE.
// IT IS THE SAME SHAPE THE PANEL HAS ALWAYS TALKED TO, SO NOTHING ELSE CHANGES.

;(() => {
  const waiting = []
  let handler = null
  let core = null

  function send(kind, value) {
    const line = JSON.stringify({ kind, value })

    if (core) core.order(line)
    else waiting.push(line)
  }

  window.happy = {
    hears: (heard) => {
      handler = heard
    },
    ask: (order) => send('ask', order),
    dropped: () => '',
    pin: (on) => send('pin', on),
    allow: (what) => send('allow', what || ''),
    hide: () => send('hide'),
    show: () => send('show'),
    open: (url) => send('open', url),
    restart: () => send('restart'),
    quit: () => send('quit'),
  }

  new QWebChannel(qt.webChannelTransport, (channel) => {
    core = channel.objects.core
    core.event.connect((line) => {
      if (handler) handler(JSON.parse(line))
    })

    core.order(JSON.stringify({ kind: 'connected' }))
    for (const line of waiting.splice(0)) core.order(line)
  })
})()
