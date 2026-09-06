// EVERY ROW IS DRAWN FROM WHAT THE CATALOGUE SAYS IT IS: ADDING A SETTING IS A
// ROW IN A PYTHON FILE AND NOTHING AT ALL IN HERE.

const Knobs = (() => {
  let sheet = null
  let ask = null

  let groups = []
  let values = {}
  let opened = null

  // THE LAST DRAW, AS ITS OWN COPY. A CLICK CHANGES values IMMEDIATELY SO THE CONTROL UNDER
  // THE FINGER ANSWERS AT ONCE; THIS IS WHAT THE SCREEN ACTUALLY SAYS.
  const painted = { values: null, groups: null }

  // OUTLIVES A REDRAW, SO A SIGN IN FINISHING DOES NOT FOLD THEM BACK.
  const asked = new Set()

  function tell(key, value) {
    // A COPY, NOT THE OBJECT painted WAS MEASURED FROM: THE CONTROL UNDER THE FINGER NEEDS
    // THE NEW VALUE AT ONCE, BUT WRITING IT INTO THE MEASURED ONE WOULD MAKE THE BACKEND'S
    // ANSWER LOOK LIKE NO CHANGE AND THE SHUT ROWS WOULD KEEP THE OLD WORD.
    values = { ...values, [key]: value }
    ask({ do: 'set', key, value })
  }

  function knob(entry) {
    // A SWITCH NEEDS NO ROOM UNDER ITS NAME, AND NOR DOES A BARE WORD.
    const flat = entry.kind === 'toggle' || entry.kind === 'state'
    const row = element('div', flat ? 'knob flat' : 'knob')
    const top = element('div', 'top')
    const now = element('span', 'now', Fields.reading(entry, values[entry.key]))

    top.append(element('span', 'label', entry.label))

    if (entry.kind === 'number') top.append(now)

    const control = Fields.control(entry, values[entry.key], now)

    row.append(top)
    ;(flat ? top : row).append(control)

    if (entry.hint) row.append(element('p', 'hint', entry.hint))

    return row
  }

  function drawing(entry) {
    if (entry.kind === 'heading') return Services.heading(entry)
    if (entry.kind === 'service') return Services.row(entry)
    if (entry.kind === 'folded') return Services.folded(entry)

    return knob(entry)
  }

  // ── WHAT A SHUT SECTION SAYS ABOUT ITSELF ──

  function phrase(entry) {
    const value = values[entry.key]

    if (entry.kind === 'number') return Fields.reading(entry, value)
    if (entry.kind === 'toggle') return value ? entry.label : null
    if (entry.kind !== 'choice') return value || null

    const found = (entry.options || []).find((each) => each.value === value)

    return found ? found.label : value || null
  }

  function summary(group) {
    const services = group.settings.filter((each) => each.kind === 'service')

    if (services.length) {
      const live = services.filter((each) => each.connected).length

      return live ? `${live} connected` : 'nothing connected yet'
    }

    const said = (group.sums || [])
      .map((key) => group.settings.find((each) => each.key === key))
      .filter(Boolean)
      .map(phrase)
      .filter(Boolean)

    return said.length ? said.join(' · ') : group.hint
  }

  // ── THE SECTIONS ──

  function inside(group) {
    const box = element('div', 'inside')
    const rare = []

    for (const entry of group.settings) {
      if (entry.rare) rare.push(entry)
      else box.append(drawing(entry))
    }

    if (!rare.length) return box

    if (asked.has(group.key)) {
      for (const entry of rare) box.append(drawing(entry))
      return box
    }

    const button = element(
      'button',
      'more',
      `More — ${rare.length} ${rare.length === 1 ? 'setting' : 'settings'}`,
    )

    button.onclick = () => {
      asked.add(group.key)
      paint()
    }

    box.append(button)

    return box
  }

  function section(group) {
    const part = element('div', group.key === opened ? 'part open' : 'part')
    const face = element('button', 'face')
    const about = element('div', 'about')

    about.append(element('div', 'title', group.label), element('div', 'now', summary(group)))
    face.append(marking(group.key, group.label), about, element('span', 'go', '›'))
    face.onclick = () => fold(group.key)

    part.append(face)

    if (group.key === opened) part.append(inside(group))

    return part
  }

  // ONE OPEN AT A TIME: TWO WOULD NOT BOTH FIT ON THE SCREEN.
  function fold(key) {
    const already = opened === key

    opened = already ? null : key

    Services.shut()
    paint()

    if (already) return

    const found = sheet.querySelector('.part.open')

    if (found) found.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }

  function paint() {
    const where = sheet.scrollTop

    // WHAT THIS DRAW IS MADE OF, SO THE NEXT WORD CAN BE COMPARED AGAINST THE SCREEN.
    painted.values = JSON.stringify(values)
    painted.groups = JSON.stringify(groups)

    sheet.innerHTML = ''

    for (const group of groups) sheet.append(section(group))

    sheet.scrollTop = where

    Fields.resume(sheet)
  }

  return {
    start(sheetNode, asking) {
      sheet = sheetNode
      ask = asking

      Fields.start({ tell, ask })

      Services.start({
        value: (key) => values[key],
        tell,
        ask,
        knob,
        doer: Fields.doer,
        typing: Fields.typing,
        switcher: Fields.switcher,
        repaint: paint,
        sheet: () => sheet,
      })
    },

    // REBUILT ONLY ON A REAL CHANGE: A REDRAW WOULD SHUT THE LIST STILL OPEN
    // UNDER SOMEBODY'S FINGER. WHAT IS COMPARED IS WHAT IS ON THE SCREEN, NOT WHAT IS IN
    // values: A CLICK WRITES ITS OWN ANSWER THERE BEFORE THE BACKEND AGREES, SO COMPARING
    // AGAINST values MATCHES ITSELF AND THE SHUT ROWS ABOVE KEEP THE OLD WORD.
    show(word) {
      const agreed =
        JSON.stringify(word.values) === painted.values &&
        JSON.stringify(word.groups) === painted.groups

      groups = word.groups
      values = word.values

      if (agreed) return

      paint()
    },
  }
})()
