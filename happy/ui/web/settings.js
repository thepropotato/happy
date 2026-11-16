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
    box.scrollTop = 0
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

  // ONE ROW PER SECTION, SAYING IN A LINE WHERE IT STANDS. IT FOLDS OPEN IN PLACE, ONE AT A TIME,
  // SO THE SETTINGS NEVER SHOW EVERYTHING AT ONCE.
  let opened = null
  let opening = null
  let group = null

  const MARKS = {
    voice: '<path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3z" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" />',
    model: '<rect x="6" y="6" width="12" height="12" rx="2.5" /><path d="M9.5 2.5v3.5M14.5 2.5v3.5M9.5 18v3.5M14.5 18v3.5M2.5 9.5H6M2.5 14.5H6M18 9.5h3.5M18 14.5h3.5" />',
    talking: '<path d="M20 11.5a7.5 7.5 0 0 1-10.9 6.7L4 19.5l1.3-4.6A7.5 7.5 0 1 1 20 11.5z" />',
    whatsapp: '<rect x="7" y="2.5" width="10" height="19" rx="2.5" /><path d="M11 18h2" />',
    services: '<path d="M9 2.5V7M15 2.5V7M6 7h12v4a6 6 0 0 1-12 0V7zM12 17v4.5" />',
    permissions: '<path d="M12 3l7.5 3v5.5c0 4.3-3.2 8-7.5 9-4.3-1-7.5-4.7-7.5-9V6L12 3z" /><path d="M9 12l2 2 4-4" />',
  }

  function section(key, title, summary, summaryClass) {
    const part = element('div', opened === key ? (opening === key ? 'section open opening' : 'section open') : 'section')
    const head = element('button', 'head')

    head.type = 'button'
    head.insertAdjacentHTML('beforeend', `<span class="mark"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${MARKS[key] || ''}</svg></span>`)
    head.append(element('span', 'name', title))
    head.append(element('span', `summary ${summaryClass || ''}`, summary || ''))
    head.insertAdjacentHTML('beforeend', '<svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6" /></svg>')
    head.onclick = () => {
      opened = opened === key ? null : key
      opening = opened
      if (opened === 'services') ask({ do: 'services' })
      draw(last)
    }

    part.append(head)
    group.append(part)

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

    group = element('div', 'group')
    box.append(group)

    speech(word.speech, word)
    model(word.model)
    you(word)
    whatsapp(word.whatsapp)
    services(word.services, word.services_checking)

    if (word.permissions && word.permissions.length) permissions(word.permissions)

    if (word.first) {
      const end = element('div', 'begin')

      end.append(button('Start Happy', () => ask({ do: 'begin' }), true))

      if (word.first && !word.speech.ready) end.firstChild.disabled = true

      box.append(end)
    }

    restore(memory)
    opening = null
  }

  function speech(state, word) {
    const block = section('voice', 'Voice and ears', state.ready ? 'ready' : state.failed ? 'not finished' : 'getting ready…', state.ready ? 'good' : 'wait')
    const line = row(block, 'Speech models', escape(state.text || (state.ready ? 'Heard and spoken on this computer.' : 'Getting them…')))

    if (!state.ready && state.progress != null) {
      const bar = element('div', 'bar-progress')
      const fill = element('span')

      fill.style.width = `${Math.round(state.progress * 100)}%`
      bar.append(fill)
      line.querySelector('.label').append(bar)
    }

    if (state.failed) line.append(button('Try again', () => ask({ do: 'speech_retry' })))

    const voiced = row(block, 'Voice', 'Who Happy sounds like.')
    const voices = element('select')

    for (const each of word.voices || []) {
      const option = element('option', '', each.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()))

      option.value = each
      option.selected = each === word.voice
      voices.append(option)
    }

    voices.onchange = () => ask({ do: 'set', key: 'voice', value: voices.value })
    voiced.append(voices)

    const paced = row(block, 'Speed', 'How quickly Happy speaks. The pitch stays the same.')
    const speeds = element('div', 'speech-speeds')

    speeds.setAttribute('role', 'group')
    speeds.setAttribute('aria-label', 'Speaking speed')
    for (const value of word.speech_speeds || []) {
      const choice = button(`${value}x`, () => ask({ do: 'set', key: 'speech_speed', value }))

      choice.setAttribute('aria-pressed', String(value === word.speech_speed))
      speeds.append(choice)
    }
    paced.append(speeds)

    device(block, 'Microphone', 'What Happy hears through.', 'input.device', word.microphone, word.microphones)
    device(block, 'Speaker', 'What Happy talks through.', 'output.device', word.speaker, word.speakers)
  }

  function device(block, main, sub, key, chosen, names) {
    const line = row(block, main, sub)
    const choose = element('select')
    const system = element('option', '', 'Same as the system')

    system.value = ''
    choose.append(system)

    for (const name of chosen && !(names || []).includes(chosen) ? [...(names || []), chosen] : names || []) {
      const option = element('option', '', name)

      option.value = name
      option.selected = name === chosen
      choose.append(option)
    }

    choose.onchange = () => ask({ do: 'set', key, value: choose.value })
    line.append(choose)
  }

  function model(state) {
    const current = state.options.find((each) => each.id === state.chosen)
    const block = section('model', 'Model', state.chosen === 'key' ? state.custom?.model || 'your service' : current ? current.label : 'looking…')
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
    const keyName = (word.keys.find(([id]) => id === word.key) || [, word.key])[1]
    const block = section('talking', 'Talking', `${word.name} · ${keyName}${word.wake ? '' : ' · no wake word'}`)
    const naming = row(block, 'Name', 'Saying it wakes Happy up.')
    const name = field('name', 'Happy')

    name.value = word.name
    name.style.maxWidth = '45%'
    name.onchange = () => ask({ do: 'set', key: 'name', value: name.value })
    naming.append(name)

    const calling = row(block, 'It calls you', 'Empty means your name on this computer.')
    const call = field('call_me', 'boss')

    call.value = word.call_me
    call.style.maxWidth = '45%'
    call.onchange = () => ask({ do: 'set', key: 'call_me', value: call.value })
    calling.append(call)

    const speaking = row(block, 'Personality', 'How it talks, in your words. Empty is its own way.')
    const style = element('textarea')

    speaking.classList.add('stacked')
    style.id = 'persona'
    style.rows = 3
    style.spellcheck = false
    style.placeholder = 'Like a knight from Game of Thrones: formal, a little grand, calls me my lord.'
    style.value = word.persona || ''
    style.onchange = () => ask({ do: 'persona', text: style.value })
    speaking.append(style)

    row(block, `Wake up to “${escape(word.name)}”`, 'Off means only the key wakes it.').append(
      toggle(word.wake, (on) => ask({ do: 'set', key: 'wake_word', value: on })),
    )

    row(block, 'Start when I log in', 'Reminders only go off while Happy is running.').append(
      toggle(word.login, (on) => ask({ do: 'set', key: 'start_at_login', value: on })),
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
    const block = section('whatsapp', 'WhatsApp', good ? 'linked' : state.state === 'unlinked' ? 'not linked' : state.state === 'busy' ? 'getting ready…' : 'not available', good ? 'good' : 'wait')
    const line = row(block, good ? state.text : 'Not linked', good ? 'Read, search and send messages.' : escape(state.text))

    if (state.state === 'unlinked') line.append(button('Link', () => ask({ do: 'whatsapp_link' }), true))

    // UNLINKING FORGETS THE SESSION AND ITS HISTORY, SO IT TAKES A SECOND CLICK.
    if (good) {
      const unlink = button('Unlink', () => {
        if (unlink.dataset.sure) return ask({ do: 'whatsapp_unlink' })
        unlink.dataset.sure = '1'
        unlink.textContent = 'Unlink, sure?'
        setTimeout(() => {
          delete unlink.dataset.sure
          unlink.textContent = 'Unlink'
        }, 3000)
      })

      line.append(unlink)
    }

    if (qr && !good) {
      const holder = element('div', 'qr')
      const picture = element('img')

      picture.src = qr
      holder.append(picture)
      block.append(holder)
    }
  }

  // A CHECK TAKES SECONDS, SO THE LAST ONE'S ROWS STAY UP, DIMMED, AND THE HEADER AND BODY SAY THE SAME THING WHILE IT RUNS.
  function services(list, checking) {
    const working = (list || []).filter((each) => each.state === 'connected').length
    const counted = list ? `${working} of ${list.length} working` : ''
    const summary = checking || !list ? (counted ? `${counted} · checking…` : 'checking…') : counted
    const block = section('services', 'Services', summary, checking || !list ? 'wait' : working === list.length ? 'good' : 'wait')

    if (checking || !list) block.classList.add('checking')

    if (!list) {
      for (let i = 0; i < 3; i++) block.append(element('div', 'row placeholder'))
    }

    for (const each of list || []) {
      const state = each.state === 'connected' ? `<span class="good">${escape(each.detail)}</span>` : `<span class="wait">${escape(each.state)}</span>`
      const line = row(block, each.name, `${escape(each.source)} · ${state}`)

      if (each.state === 'needs sign-in') line.append(button('Sign in', () => ask({ do: 'service_signin', name: each.name }), true))
      if (each.removable) line.append(button('Remove', () => ask({ do: 'service_remove', name: each.name })))
    }

    if (list && !list.length && !checking) row(block, 'None yet', 'Paste an install command below to add one.')

    const adding = element('div', 'adding')
    const pasted = field('service', 'Paste a claude or codex "mcp add" command, or a URL')

    pasted.onkeydown = (event) => {
      if (event.key === 'Enter') ask({ do: 'service_add', text: pasted.value })
    }

    adding.append(pasted, button('Add', () => ask({ do: 'service_add', text: pasted.value }), true))
    block.append(adding)
  }

  function permissions(list) {
    const missing = list.filter((each) => !each.granted && !each.optional).length
    const block = section('permissions', 'Permissions', missing ? `${missing} to allow` : 'all allowed', missing ? 'wait' : 'good')

    for (const each of list) {
      const line = row(block, each.title, escape(each.why))

      if (each.granted) line.append(element('span', 'good', 'allowed'))
      else line.append(button(each.optional ? 'Open' : 'Allow', () => ask({ do: 'allow', what: each.key }), !each.optional))
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
      if (word.is === 'speech_speed') {
        if (last) {
          last.speech_speed = word.speech_speed
          if (open) draw(last)
        }
        return
      }
      if (word.is === 'settings') {
        if (!last && word.first) opened = 'voice'
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
