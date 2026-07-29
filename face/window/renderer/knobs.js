// EVERY CONTROL IS DRAWN FROM WHAT THE CATALOGUE SAYS THE SETTING IS. NOTHING
// HERE KNOWS WHAT A SINGLE ONE OF THEM MEANS, WHICH IS WHY ADDING ONE IS A ROW
// IN A PYTHON FILE AND NOTHING AT ALL IN HERE.

const SEGMENT_MOST = 4 // MORE CHOICES THAN THIS AND A ROW OF BUTTONS STOPS FITTING.

const CUSTOM = '… something else'

const Knobs = (() => {
  let tabs = null
  let sheet = null
  let ask = null

  let groups = []
  let values = {}
  let chosen = null

  function tell(key, value) {
    values[key] = value
    ask({ do: 'set', key, value })
  }

  function reading(entry, value) {
    if (entry.kind !== 'number') return ''
    const shown = entry.step < 1 ? Number(value).toFixed(2) : String(Math.round(value))
    return entry.unit ? `${shown} ${entry.unit}` : shown
  }

  function segments(entry, value, now) {
    const holder = element('div', 'segments')

    for (const option of entry.options) {
      const button = element('button', option.value === value ? 'on' : '', option.label)

      button.onclick = () => {
        tell(entry.key, option.value)
        for (const other of holder.children) other.className = ''
        button.className = 'on'
        if (now) now.textContent = ''
      }

      holder.append(button)
    }

    return holder
  }

  function picker(entry, value) {
    const holder = element('div', 'dropdown')
    const here = entry.options.find((each) => each.value === value)
    const face = element('button', 'picker', here ? here.label : value || 'not set')
    const list = element('div', 'options')

    // A CHOICE IS A VALUE AND SOMETHING NICER TO READ, AND THEY ARE NOT ALWAYS
    // THE SAME WORD. THE SETTING ONLY EVER HEARS THE VALUE.
    const offered = entry.open ? [...entry.options, { value: CUSTOM, label: CUSTOM }] : entry.options

    for (const option of offered) {
      const row = element('button', option.value === value ? 'option on' : 'option', option.label)

      row.onclick = () => {
        list.classList.remove('open')

        if (option.value === CUSTOM) {
          holder.replaceWith(typing(entry, value))
          return
        }

        face.textContent = option.label
        for (const other of list.children) other.className = 'option'
        row.className = 'option on'
        tell(entry.key, option.value)
      }

      list.append(row)
    }

    face.onclick = () => list.classList.toggle('open')
    holder.append(face, list)

    return holder
  }

  function typing(entry, value) {
    const box = element('input', 'typed')

    box.type = 'text'
    box.value = value ?? ''
    box.placeholder = entry.placeholder || ''
    box.onchange = () => tell(entry.key, box.value)

    return box
  }

  function slider(entry, value, now) {
    const holder = element('div', 'slider')
    const range = element('input')

    Object.assign(range, { type: 'range', min: entry.low, max: entry.high, step: entry.step, value })

    range.oninput = () => {
      now.textContent = reading(entry, range.value)
    }
    range.onchange = () => tell(entry.key, Number(range.value))

    holder.append(range)

    return holder
  }

  function switcher(entry, value) {
    const button = element('button', value ? 'switch on' : 'switch')

    button.onclick = () => {
      const wanted = !button.classList.contains('on')
      button.classList.toggle('on', wanted)
      tell(entry.key, wanted)
    }

    return button
  }

  // A BUTTON, NOT A SETTING. IT SENDS ITS OWN VERB AND NOTHING IS STORED, WHICH
  // IS HOW SIGNING INTO SOMETHING DRAWS ITSELF WITHOUT THIS FILE KNOWING WHAT.
  function doer(entry) {
    const button = element('button', 'doer', entry.wording)

    button.onclick = () => {
      button.disabled = true
      button.textContent = '…'
      ask({ do: entry.verb, name: entry.key })
    }

    return button
  }

  function control(entry, value, now) {
    if (entry.kind === 'action') return doer(entry)
    if (entry.kind === 'toggle') return switcher(entry, value)
    if (entry.kind === 'number') return slider(entry, value, now)
    if (entry.kind === 'text') return typing(entry, value)
    if (entry.options.length <= SEGMENT_MOST && !entry.open) return segments(entry, value, now)

    return picker(entry, value)
  }

  function knob(entry, index) {
    const row = element('div', 'knob')
    const top = element('div', 'top')
    const now = element('span', 'now', reading(entry, values[entry.key]))

    row.style.animationDelay = `${Math.min(index, 12) * 22}ms`
    top.append(element('span', 'label', entry.label), now)
    row.append(top, control(entry, values[entry.key], now))

    if (entry.hint) row.append(element('p', 'hint', entry.hint))

    return row
  }

  function paint() {
    const group = groups.find((each) => each.key === chosen) || groups[0]

    if (!group) return

    sheet.innerHTML = ''
    sheet.scrollTop = 0
    group.settings.forEach((entry, index) => sheet.append(knob(entry, index)))
  }

  function labels() {
    tabs.innerHTML = ''

    for (const group of groups) {
      const button = element('button', group.key === chosen ? 'group on' : 'group', group.label)

      button.onclick = () => {
        chosen = group.key
        labels()
        paint()
      }

      tabs.append(button)
    }
  }

  return {
    start(tabsNode, sheetNode, asking) {
      tabs = tabsNode
      sheet = sheetNode
      ask = asking
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
      chosen = chosen || (groups[0] && groups[0].key)

      if (agreed) return

      labels()
      paint()
    },
  }
})()
