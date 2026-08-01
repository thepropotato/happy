// A CONNECTION AS ONE ROW, AND WHAT OPENS UNDER IT WHEN IT IS TAPPED.
//
// EVERY ROW IS THE SAME ROW: A MARK, A NAME, ONE LINE OF HOW IT IS, AND A
// CHEVRON. NOTHING ELSE, EVER.

const USING = 'Let Happy use this'

const Services = (() => {
  let help = null
  const qrs = new Map()
  let lastStatus = null
  let polling = null

  // WHICH ROWS ARE OPEN. IT OUTLIVES THE REDRAW A SIGN IN CAUSES.
  const opened = new Set()

  function words(entry) {
    const row = element('div', 'heading')

    row.append(element('span', '', entry.label))

    if (entry.count) row.append(element('span', 'count', entry.count))

    return row
  }

  function serving(entry, within) {
    const row = element('div', ['service', entry.tone].join(' ').trim())
    const face = element('button', 'face')
    const who = element('div', 'who')

    who.append(element('div', 'title', entry.label))

    if (entry.under) who.append(element('div', 'under', entry.under))

    face.append(element('span', 'mark', entry.mark), who)

    // A ROW WITH NOTHING INSIDE IT DOES NOT OPEN.
    if (worth(entry)) face.onclick = () => fold(entry.name, within)
    else face.classList.add('shut')

    row.append(face, element('span', 'go', '›'))

    if (opened.has(entry.name)) {
      row.classList.add('open')
      if (
        entry.name === 'whatsapp' &&
        polling === null &&
        lastStatus !== 'connected' &&
        lastStatus !== 'unsupported'
      )
        startPolling('whatsapp')
      row.append(inside(entry))
    }

    return row
  }

  function worth(entry) {
    return Boolean(
      entry.note ||
        entry.key ||
        entry.action ||
        entry.fields.length ||
        entry.parts.length ||
        entry.doing.length ||
        entry.leaving.length,
    )
  }

  // THE SAME SEVEN THINGS IN THE SAME ORDER ON EVERY CONNECTION.
  function inside(entry) {
    const drawer = element('div', 'drawer')

    if (entry.name === 'whatsapp') {
      const info = qrs.get('whatsapp')

      if (info) {
        if (info.status === 'waiting' && info.qr) {
          const section = element('div', 'qr')
          const code = element('img', 'qr-code')

          code.src = info.qr

          section.append(code)
          section.append(
            element('p', 'note', 'Scan with WhatsApp: Settings -> Linked Devices -> Link a Device.'),
          )
          drawer.append(section)
        } else if (info.status === 'loading') {
          drawer.append(element('p', 'note', 'Starting up...'))
        } else if (info.status === 'offline') {
          drawer.append(
            element(
              'p',
              'note',
              "The WhatsApp bridge isn't running. Start it with: python mcps/servers/whatsapp/bridge.py",
            ),
          )
        }
      }
    }

    if (entry.note) drawer.append(element('p', 'note', entry.note))

    if (entry.key) drawer.append(using(entry))

    if (entry.doing.length) drawer.append(offering(entry.doing))

    for (const field of entry.fields) drawer.append(asking(field))

    if (entry.action) {
      const button = help.doer(entry.action, entry.careful ? 'doer careful' : 'doer')

      button.disabled = entry.ready === false
      drawer.append(button)
    }

    for (const part of entry.parts) drawer.append(serving(part, entry.name))

    for (const leaving of entry.leaving) drawer.append(help.doer(leaving, 'leave'))
    if (entry.name === 'whatsapp') lastStatus = null

    return drawer
  }

  function using(entry) {
    const row = element('div', 'knob flat')
    const top = element('div', 'top')

    top.append(element('span', 'label', USING), help.switcher(entry, help.value(entry.key)))
    row.append(top)

    return row
  }

  function asking(field) {
    const box = element('div', 'field')

    box.append(element('label', '', field.label), help.typing(field, help.value(field.key)))

    if (field.hint) box.append(element('p', 'hint', field.hint))

    return box
  }

  // WHAT A CONNECTED SERVICE ACTUALLY HANDS OVER, WHICH IS NOT ALWAYS ALL OF IT.
  function offering(names) {
    const holder = element('div', 'offering')

    for (const name of names) holder.append(element('span', '', name))

    return holder
  }

  // THE TWO ROWS AT THE BOTTOM THAT ARE NOT CONNECTIONS AT ALL.
  function folding(entry) {
    const row = element('div', 'service quiet')
    const face = element('button', 'face')
    const who = element('div', 'who')

    who.append(element('div', 'title', entry.label))
    face.append(element('span', 'mark', entry.mark), who)
    face.onclick = () => fold(entry.key)

    row.append(face, element('span', 'go', '›'))

    if (opened.has(entry.key)) {
      const drawer = element('div', 'drawer')

      entry.settings.forEach((each, index) => drawer.append(help.knob(each, index)))
      row.classList.add('open')
      row.append(drawer)
    }

    return row
  }

  // ONE ROW OPEN AT A TIME. within IS THE ROW THIS ONE LIVES INSIDE, WHICH STAYS
  // OPEN EITHER WAY: SHUTTING THE FAMILY WOULD TAKE THE TAPPED ROW OFF SCREEN.
  function fold(which, within) {
    const already = opened.has(which)

    if (which === 'whatsapp') {
      if (!already) startPolling('whatsapp')
      else stopPolling()
    } else {
      stopPolling()
    }

    opened.clear()

    if (within) opened.add(within)
    if (!already) opened.add(which)

    help.repaint()

    if (already) return

    const found = help.sheet().querySelector('.service.open')

    if (found) found.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }

  function showQR(word) {
    qrs.set(word.name, word)
    lastStatus = word.status

    if (word.status === 'connected' || word.status === 'unsupported') {
      stopPolling()
    }

    const img = help.sheet().querySelector('.qr-code')

    if (img && word.status === 'waiting' && word.qr) {
      img.src = word.qr
      return
    }

    help.repaint()
  }

  function startPolling(name) {
    stopPolling()
    polling = setInterval(() => help.ask({ do: 'qr', name }), 3000)
    help.ask({ do: 'qr', name })
  }

  function stopPolling() {
    if (polling) {
      clearInterval(polling)
      polling = null
    }
  }

  return {
    start(helpers) {
      help = helpers
    },

    shut() {
      stopPolling()
      opened.clear()
    },

    heading: words,
    row: serving,
    folded: folding,
    showQR,
  }
})()
