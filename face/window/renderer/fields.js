// THE THINGS A SETTING CAN BE MOVED WITH: A SLIDE, A SWITCH, A ROW OF ONE, A LIST,
// A BOX TO TYPE IN, AND A BUTTON THAT IS NOT A SETTING AT ALL. NOTHING HERE KNOWS
// WHAT ANY PARTICULAR SETTING MEANS, ONLY WHAT KIND OF THING IT IS.

const SEGMENT_MOST = 4 // MORE CHOICES THAN THIS AND A ROW OF BUTTONS STOPS FITTING.

const CUSTOM = '… something else'

const Fields = (() => {
  let help = null

  // WHERE SOMEBODY WAS TYPING WHEN THE SHEET WAS REDRAWN UNDER THEM, WHICH A SIGN
  // IN FINISHING DOES. LOSING THE CARET MID SECRET IS A REAL WAY TO LOSE ONE.
  let typingIn = null

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
        help.tell(entry.key, option.value)
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
        help.tell(entry.key, option.value)
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
    box.dataset.key = entry.key
    box.onchange = () => help.tell(entry.key, box.value)
    box.onfocus = () => (typingIn = entry.key)
    box.onblur = () => (typingIn = typingIn === entry.key ? null : typingIn)

    return box
  }

  function slider(entry, value, now) {
    const holder = element('div', 'slider')
    const range = element('input')

    Object.assign(range, { type: 'range', min: entry.low, max: entry.high, step: entry.step, value })

    range.oninput = () => {
      now.textContent = reading(entry, range.value)
    }
    range.onchange = () => help.tell(entry.key, Number(range.value))

    holder.append(range)

    return holder
  }

  function switcher(entry, value) {
    const button = element('button', value ? 'switch on' : 'switch')

    button.onclick = () => {
      const wanted = !button.classList.contains('on')
      button.classList.toggle('on', wanted)
      help.tell(entry.key, wanted)
    }

    return button
  }

  // A BUTTON, NOT A SETTING. IT SENDS ITS OWN VERB AND NOTHING IS STORED, WHICH
  // IS HOW SIGNING INTO SOMETHING DRAWS ITSELF WITHOUT THIS FILE KNOWING WHAT.
  function doer(entry, look) {
    const button = element('button', look || 'doer', entry.wording)

    button.onclick = (event) => {
      event.stopPropagation()
      button.disabled = true
      button.textContent = '…'
      help.ask({ do: entry.verb, name: entry.key })
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

  return {
    start(helpers) {
      help = helpers
    },

    // PUT THE CARET BACK WHERE IT WAS BEFORE THE SHEET WAS REBUILT UNDER IT.
    resume(sheet) {
      if (!typingIn) return

      const box = sheet.querySelector(`[data-key="${typingIn}"]`)

      if (!box) return

      box.focus()
      box.setSelectionRange(box.value.length, box.value.length)
    },

    reading,
    control,
    doer,
    typing,
    switcher,
  }
})()
