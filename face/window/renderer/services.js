// A CONNECTION AS ONE ROW: A MARK, A NAME, ONE LINE OF HOW IT IS, AND A
// CHEVRON. NOTHING ELSE, EVER.

const Services = (() => {
  let help = null

  // WHICH ROWS ARE OPEN. IT OUTLIVES THE REDRAW A SIGN IN CAUSES.
  const opened = new Set()

  function words(entry) {
    const row = element('div', 'heading')

    row.append(element('span', '', entry.label))

    if (entry.count) row.append(element('span', 'count', entry.count))

    return row
  }

  function serving(entry) {
    const row = element('div', ['service', entry.tone].join(' ').trim())
    const face = element('button', 'face')
    const who = element('div', 'who')

    who.append(element('div', 'title', entry.label))

    if (entry.under) who.append(element('div', 'under', entry.under))

    face.append(element('span', 'mark', entry.mark), who)

    // A ROW WITH NOTHING INSIDE IT DOES NOT OPEN.
    if (worth(entry)) face.onclick = () => fold(entry.name)
    else face.classList.add('shut')

    row.append(face, element('span', 'go', '›'))

    if (opened.has(entry.name)) {
      row.classList.add('open')
      row.append(inside(entry))
    }

    return row
  }

  function worth(entry) {
    return Boolean(
      entry.note ||
        entry.action ||
        entry.fields.length ||
        entry.doing.length ||
        entry.leaving.length,
    )
  }

  // THE SAME FEW THINGS IN THE SAME ORDER ON EVERY CONNECTION.
  function inside(entry) {
    const drawer = element('div', 'drawer')

    if (entry.note) drawer.append(element('p', 'note', entry.note))

    if (entry.doing.length) drawer.append(offering(entry.doing))

    for (const field of entry.fields) drawer.append(asking(field))

    if (entry.action) {
      const button = help.doer(entry.action, entry.careful ? 'doer careful' : 'doer')

      button.disabled = entry.ready === false
      drawer.append(button)
    }

    for (const leaving of entry.leaving) drawer.append(help.doer(leaving, 'leave'))

    return drawer
  }

  function asking(field) {
    const box = element('div', 'field')

    box.append(element('label', '', field.label), help.typing(field, help.value(field.key)))

    if (field.hint) box.append(element('p', 'hint', field.hint))

    return box
  }

  // WHAT A CONNECTED SERVICE HANDS OVER, WHICH IS EVERYTHING ITS SERVER HAS.
  function offering(names) {
    const holder = element('div', 'offering')

    for (const name of names) holder.append(element('span', '', name))

    return holder
  }

  // THE ROW AT THE BOTTOM THAT IS NOT A CONNECTION AT ALL.
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

  // ONE ROW OPEN AT A TIME.
  function fold(which) {
    const already = opened.has(which)

    opened.clear()

    if (!already) opened.add(which)

    help.repaint()

    if (already) return

    const found = help.sheet().querySelector('.service.open')

    if (found) found.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }

  return {
    start(helpers) {
      help = helpers
    },

    shut() {
      opened.clear()
    },

    heading: words,
    row: serving,
    folded: folding,
  }
})()
