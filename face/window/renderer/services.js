// A CONNECTION AS ONE ROW, AND WHAT OPENS UNDER IT WHEN IT IS TAPPED. NOTHING
// HERE KNOWS WHICH SERVICES EXIST OR WHAT ANY OF THEM WANT: A ROW SAYS WHETHER IT
// HAS BOXES, PARTS OR A BUTTON, AND THAT IS THE WHOLE VOCABULARY.

const Services = (() => {
  let help = null

  // WHICH ROWS ARE OPEN. SIGNING INTO SOMETHING REDRAWS THE WHOLE SHEET, AND A ROW
  // THAT SHUT ITSELF HALFWAY THROUGH PASTING A SECRET WOULD PICK THE WORST MOMENT.
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

    // A ROW WITH NOTHING INSIDE IT DOES NOT OPEN. TAPPING SOMETHING AND GETTING AN
    // EMPTY BOX IS WORSE THAN THE ROW NOT ANSWERING AT ALL.
    if (worth(entry)) face.onclick = () => fold(entry.name, within)
    else face.style.cursor = 'default'

    row.append(face, aside(entry, within))

    if (opened.has(entry.name)) {
      row.classList.add('open')
      row.append(inside(entry))
    }

    return row
  }

  // TRUE WHEN THE ROW'S OWN BUTTON IS THE WHOLE STORY: NOTHING TO FILL IN, NOTHING
  // TO SWITCH, SO THE BUTTON ON THE RIGHT IS THE ONLY THING THERE IS TO PRESS.
  function bare(entry) {
    return Boolean(entry.action) && !entry.key && !entry.parts.length && !entry.fields.length
  }

  function worth(entry) {
    const held = entry.note || entry.fields.length || entry.parts.length || entry.doing.length

    return Boolean(held || entry.leaving.length || (entry.action && !bare(entry)))
  }

  // THE RIGHT HAND END OF A ROW: A SWITCH ONCE THERE IS SOMETHING TO SWITCH, A
  // BUTTON WHILE THERE IS NOT, AND NOTHING AT ALL IN BETWEEN.
  function aside(entry, within) {
    if (entry.key) return help.switcher(entry, help.value(entry.key))

    if (entry.parts.length) return switching(entry)

    if (!entry.action) return element('span', 'go', '›')

    // A SERVICE WITH NOTHING TO FILL IN IS ONE TAP, AND MAKING SOMEBODY OPEN A ROW
    // TO FIND THE ONLY BUTTON IN IT WOULD BE A STEP INVENTED OUT OF NOTHING. ONE
    // WORTH THINKING TWICE ABOUT IS STILL ONE TAP, BUT NOT AN INVITING ONE.
    if (bare(entry)) return help.doer(entry.action, entry.careful ? 'pill quiet' : 'pill')

    const button = element('button', 'pill quiet', entry.wording)

    button.onclick = (event) => {
      event.stopPropagation()
      fold(entry.name, within)
    }

    return button
  }

  // A FAMILY'S SWITCH. IT IS ON WHEN ANY OF ITS SERVICES IS, AND MOVING IT MOVES
  // ALL OF THEM, WHICH IS THE ONLY THING "GOOGLE, OFF" COULD HONESTLY MEAN.
  function switching(entry) {
    const held = entry.parts.filter((part) => part.key)
    const on = held.some((part) => help.value(part.key))
    const button = element('button', on ? 'switch on' : 'switch')

    button.onclick = (event) => {
      event.stopPropagation()

      const wanted = !button.classList.contains('on')

      button.classList.toggle('on', wanted)
      for (const part of held) help.tell(part.key, wanted)
    }

    return button
  }

  function inside(entry) {
    const drawer = element('div', 'drawer')

    if (entry.note) drawer.append(element('p', 'note', entry.note))

    for (const field of entry.fields) drawer.append(asking(field))

    for (const part of entry.parts) drawer.append(serving(part, entry.name))

    if (entry.doing.length) drawer.append(offering(entry.doing))

    if (entry.action && !bare(entry)) {
      const button = help.doer(entry.action)

      button.disabled = !entry.ready
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

  // WHAT A CONNECTED SERVICE ACTUALLY HANDS OVER, WHICH IS NOT ALWAYS ALL OF IT.
  function offering(names) {
    const holder = element('div', 'offering')

    for (const name of names) holder.append(element('span', '', name))

    return holder
  }

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

  // ONE ROW OPEN AT A TIME. TWO OPEN AT ONCE IN A PANEL THIS TALL IS A SHEET WHERE
  // NEITHER OF THEM IS FULLY ON THE SCREEN. within IS THE ROW THIS ONE LIVES
  // INSIDE, WHICH STAYS OPEN EITHER WAY: SHUTTING THE FAMILY TO OPEN ONE OF ITS
  // SERVICES WOULD TAKE THE THING THAT WAS TAPPED OFF THE SCREEN.
  function fold(which, within) {
    const already = opened.has(which)

    opened.clear()

    if (within) opened.add(within)
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
