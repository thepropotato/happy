// THE SETTINGS, OPENED IN PLACE OF THE CONVERSATION. PYTHON SENDS WHAT IS TRUE
// RIGHT NOW AS ONE "settings" WORD AND THE WHOLE VIEW IS DRAWN FROM IT; EVERY
// CHANGE GOES BACK AS AN ORDER, AND THE ANSWER IS THE NEXT "settings" WORD.

const Settings = (() => {
  let box = null
  let glass = null
  let open = false
  let last = null
  let qr = null

  const ask = (order) => window.happy.ask(order)

  function show() {
    open = true
    glass.classList.add('tuning')
    box.hidden = false
    document.getElementById('controls').classList.add('on')
    if (last) draw(last)
    ask({ do: 'settings' })
  }

  function hide() {
    if (last && last.first && !last.started) return // THE FIRST TIME, THE ONLY WAY OUT IS STARTING.

    open = false
    glass.classList.remove('tuning')
    box.hidden = true
    document.getElementById('controls').classList.remove('on')
  }

  function section(title, state, stateClass) {
    const part = element('div', 'section')
    const head = element('div', 'title', title)

    if (state) head.append(element('span', `state ${stateClass || ''}`, state))

    part.append(head)
    box.append(part)

    const block = element('div', 'block')

    part.append(block)

    return block
  }

  function row(block, main, sub) {
    const line = element('div', 'row')
    const label = element('div', 'label')

    label.append(element('div', 'main', main))

    if (sub) {
      const below = element('div', 'sub')

      below.innerHTML = sub
      label.append(below)
    }

    line.append(label)
    block.append(line)

    return line
  }

  function button(text, onclick, strong) {
    const made = element('button', strong ? 'button strong' : 'button', text)

    made.type = 'button'
    made.onclick = onclick

    return made
  }

  function field(id, placeholder, kind) {
    const input = element('input')

    input.id = id
    input.type = kind || 'text'
    input.placeholder = placeholder
    input.spellcheck = false

    return input
  }

  function toggle(on, change) {
    const made = element('div', on ? 'switch on' : 'switch')

    made.onclick = () => change(!made.classList.contains('on'))

    return made
  }

  function escape(text) {
    const holder = element('span')

    holder.textContent = text || ''

    return holder.innerHTML
  }

  // WHAT SOMEBODY IS HALFWAY THROUGH TYPING SURVIVES THE VIEW BEING DRAWN AGAIN.
  function kept() {
    const held = {}

    for (const input of box.querySelectorAll('input[id]')) held[input.id] = input.value

    const focused = document.activeElement && box.contains(document.activeElement) ? document.activeElement.id : null

    return { held, focused }
  }

  function restore({ held, focused }) {
    for (const [id, value] of Object.entries(held)) {
      const input = document.getElementById(id)

      if (input && value) input.value = value
    }

    if (focused) document.getElementById(focused)?.focus()
  }

  function draw(word) {
    const memory = kept()

    box.innerHTML = ''

    const notice = element('div', 'notice', word.notice || '')

    box.append(notice)

    speech(word.speech)
    model(word.model)
    you(word)
    whatsapp(word.whatsapp)
    services(word.services)

    if (word.permissions && word.permissions.length) permissions(word.permissions)

    if (word.first || word.restart) {
      const end = element('div', 'begin')

      end.append(
        word.first
          ? button('Start Happy', () => ask({ do: 'begin' }), true)
          : button('Restart to use the changes', () => ask({ do: 'restart' }), true),
      )

      if (word.first && !word.speech.ready) end.firstChild.disabled = true

      box.append(end)
    }

    restore(memory)
  }

  function speech(state) {
    const block = section('Voice and ears', state.ready ? 'ready' : state.failed ? 'not finished' : '', state.ready ? 'good' : 'wait')
    const line = row(block, 'Speech models', escape(state.text || (state.ready ? 'Heard and spoken on this computer.' : 'Getting them…')))

    if (!state.ready && state.progress != null) {
      const bar = element('div', 'bar-progress')
      const fill = element('span')

      fill.style.width = `${Math.round(state.progress * 100)}%`
      bar.append(fill)
      line.querySelector('.label').append(bar)
    }

    if (state.failed) line.append(button('Try again', () => ask({ do: 'speech_retry' })))
  }

  function model(state) {
    const block = section('Model')
    const line = row(block, 'Thinks with', 'Claude when you are logged in to Claude Code; otherwise whatever runs here.')
    const choose = element('select')

    for (const each of state.options) {
      const option = element('option', '', each.label)

      option.value = each.id
      option.selected = each.id === state.chosen
      choose.append(option)
    }

    const other = element('option', '', 'Another service, with an API key…')

    other.value = 'key'
    other.selected = state.chosen === 'key'
    choose.append(other)

    choose.onchange = () => {
      if (choose.value === 'key') draw({ ...last, model: { ...state, chosen: 'key' } })
      else ask({ do: 'model', id: choose.value })
    }

    line.append(choose)

    if (state.chosen !== 'key') return

    const adding = element('div', 'adding')
    const url = field('model-url', 'API URL, like https://api.openai.com/v1')
    const name = field('model-name', 'Model')
    const key = field('model-key', 'API key', 'password')

    url.value = state.custom?.base_url || ''
    name.value = state.custom?.model || ''
    adding.style.flexDirection = 'column'
    adding.append(url, name, key, button('Use it', () => ask({ do: 'model', id: 'key', base_url: url.value, model: name.value, api_key: key.value }), true))
    block.append(adding)
  }

  const COLOURS = ['#658761', '#3f8f7a', '#4a7fb5', '#b5654a', '#c79a3e', '#8a8f98', '#d16d8f']

  function colour(block, chosen) {
    const line = row(block, 'Colour', 'What Happy wears, on the smile and in here.')
    const holder = element('div', 'swatches')

    for (const each of COLOURS) {
      const dot = element('div', each.toLowerCase() === chosen.toLowerCase() ? 'swatch on' : 'swatch')

      dot.style.background = each
      dot.title = each
      dot.onclick = () => pick(each)
      holder.append(dot)
    }

    const any = element('label', COLOURS.includes(chosen) ? 'swatch any' : 'swatch any on')
    const input = element('input')

    any.title = 'Any colour'
    input.type = 'color'
    input.value = chosen
    input.oninput = () => Tint.apply(input.value)
    input.onchange = () => pick(input.value)
    any.append(input)
    holder.append(any)
    line.append(holder)
  }

  function pick(hex) {
    Tint.apply(hex)
    ask({ do: 'set', key: 'colour', value: hex })
  }

  function you(word) {
    const block = section('Talking')
    const naming = row(block, 'Name', 'Saying it wakes Happy up.')
    const name = field('name', 'Happy')

    name.value = word.name
    name.style.maxWidth = '45%'
    name.onchange = () => ask({ do: 'set', key: 'name', value: name.value })
    naming.append(name)

    row(block, `Wake up to “${escape(word.name)}”`, 'Off means only the key wakes it.').append(
      toggle(word.wake, (on) => ask({ do: 'set', key: 'wake_word', value: on })),
    )

    const keyed = row(block, 'Hold to talk', 'Hold it anywhere, talk, let go.')
    const keys = element('select')

    for (const [id, label] of word.keys) {
      const option = element('option', '', label)

      option.value = id
      option.selected = id === word.key
      keys.append(option)
    }

    keys.onchange = () => ask({ do: 'set', key: 'push_to_talk', value: keys.value })
    keyed.append(keys)

    colour(block, word.colour || '#658761')
  }

  function whatsapp(state) {
    const good = state.state === 'linked'
    const block = section('WhatsApp', good ? 'linked' : '', good ? 'good' : '')
    const line = row(block, good ? state.text : 'Not linked', good ? 'Read, search and send messages.' : escape(state.text))

    if (state.state === 'unlinked') line.append(button('Link', () => ask({ do: 'whatsapp_link' }), true))

    if (qr && !good) {
      const holder = element('div', 'qr')
      const picture = element('img')

      picture.src = qr
      holder.append(picture)
      block.append(holder)
    }
  }

  function services(list) {
    const working = (list || []).filter((each) => each.state === 'connected').length
    const block = section('Services', list ? `${working} of ${list.length} working` : 'checking…', list && working === list.length ? 'good' : 'wait')

    for (const each of list || []) {
      const state = each.state === 'connected' ? `<span class="good">${escape(each.detail)}</span>` : `<span class="wait">${escape(each.state)}</span>`
      const line = row(block, each.name, `${escape(each.source)} · ${state}`)

      if (each.state === 'needs sign-in') line.append(button('Sign in', () => ask({ do: 'service_signin', name: each.name }), true))
      if (each.removable) line.append(button('Remove', () => ask({ do: 'service_remove', name: each.name })))
    }

    if (list && !list.length) row(block, 'None yet', 'Paste an install command below to add one.')

    const adding = element('div', 'adding')
    const pasted = field('service', 'Paste a claude or codex "mcp add" command, or a URL')

    pasted.onkeydown = (event) => {
      if (event.key === 'Enter') ask({ do: 'service_add', text: pasted.value })
    }

    adding.append(pasted, button('Add', () => ask({ do: 'service_add', text: pasted.value }), true))
    block.append(adding)
  }

  function permissions(list) {
    const block = section('Permissions')

    for (const each of list) {
      const line = row(block, each.title, escape(each.why))

      if (each.granted) line.append(element('span', 'good', 'allowed'))
      else line.append(button('Allow', () => ask({ do: 'allow', what: each.key }), true))
    }
  }

  return {
    start(holder, frame) {
      box = holder
      glass = frame
      document.getElementById('back').onclick = () => hide()
    },

    toggle() {
      if (open) hide()
      else show()
    },

    hide,

    hear(word) {
      if (word.is === 'settings') {
        last = word

        if (word.first && !open) show()
        else if (!word.first && open && last.started) hide()
        else if (open) draw(word)

        return
      }

      if (word.is === 'open_settings') {
        if (!open) show()
        return
      }

      if (word.is === 'qr') {
        qr = word.linked ? null : word.image
        if (open && last) draw(last)
      }
    },
  }
})()
