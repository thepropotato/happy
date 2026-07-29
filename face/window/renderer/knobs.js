// THE SHEET OF CONTROLS: SIX SECTIONS THAT FOLD OPEN WHERE THEY SIT. EVERY ROW
// IS DRAWN FROM WHAT THE CATALOGUE SAYS IT IS, WHICH IS WHY ADDING A SETTING IS A
// ROW IN A PYTHON FILE AND NOTHING AT ALL IN HERE.
//
// A SHUT SECTION STILL SAYS WHAT IT IS SET TO, BECAUSE MOST VISITS TO THE
// CONTROLS ARE SOMEBODY CHECKING RATHER THAN CHANGING.

const Knobs = (() => {
  let sheet = null
  let ask = null

  let groups = []
  let values = {}
  let opened = null

  // SECTIONS WHERE THE RARELY TOUCHED ONES HAVE BEEN ASKED FOR. IT OUTLIVES A
  // REDRAW, SO A SIGN IN FINISHING DOES NOT FOLD THEM BACK UNDER SOMEBODY.
  const asked = new Set()

  function tell(key, value) {
    values[key] = value
    ask({ do: 'set', key, value })
  }

  function knob(entry) {
    const flat = entry.kind === 'toggle' // A SWITCH NEEDS NO ROOM UNDER ITS NAME.
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

  // A CONNECTION IS NOT A SETTING AND IS NOT DRAWN LIKE ONE. NEITHER IS THE LINE
  // OVER A RUN OF THEM, OR A ROW THAT OPENS INTO ORDINARY CONTROLS.
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

    // A SECTION OF SERVICES COUNTS ITSELF. NOTHING ELSE ABOUT IT IS WORTH A LINE.
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

  // ONE OPEN AT A TIME. TWO AT ONCE IN A PANEL THIS TALL IS A SHEET WHERE NEITHER
  // OF THEM IS FULLY ON THE SCREEN.
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
    // A SHEET REDRAWN UNDER SOMEBODY BECAUSE A SIGN IN FINISHED SHOULD STAY WHERE
    // THEY LEFT IT.
    const where = sheet.scrollTop

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

      // WHAT DRAWING A CONNECTION BORROWS. IT IS THE CONTROLS EVERY OTHER SETTING
      // IS DRAWN WITH AND NOTHING ELSE, SO A SERVICE'S BOXES AND BUTTONS ARE THE
      // SAME BOXES AND BUTTONS.
      Services.start({
        value: (key) => values[key],
        tell,
        knob,
        doer: Fields.doer,
        typing: Fields.typing,
        switcher: Fields.switcher,
        repaint: paint,
        sheet: () => sheet,
      })
    },

    // A CONTROL THAT WAS JUST MOVED HAS ALREADY DRAWN ITSELF, AND REDRAWING IT
    // WOULD SHUT THE LIST THAT IS STILL OPEN UNDER SOMEBODY'S FINGER. SO THE
    // SHEET IS ONLY REBUILT WHEN WHAT CAME BACK IS NOT WHAT WE ALREADY BELIEVE.
    show(word) {
      const agreed =
        JSON.stringify(word.values) === JSON.stringify(values) &&
        JSON.stringify(word.groups) === JSON.stringify(groups)

      groups = word.groups
      values = word.values

      if (agreed) return

      paint()
    },
  }
})()
