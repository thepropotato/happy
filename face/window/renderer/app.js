// EVERYTHING HAPPY SAYS ARRIVES HERE AND IS HANDED TO WHICHEVER PART OF THE
// PANEL CARES ABOUT IT. NOTHING IN HERE DECIDES ANYTHING ON ITS OWN.

const node = (id) => document.getElementById(id)

const HELD = 'Hold {key} to talk'

// SOUND OUTLIVES THE WORDS: HAPPY IS STILL A SENTENCE BEHIND HIMSELF WHEN THE
// STREAM ENDS, SO GOING QUIET WAITS FOR THE LAST CLIP RATHER THAN THE LAST WORD.
const TAIL_MS = 120

let mood = 'loading'
let key = ''
let resting = 'idle'
let sounding = null

function ask(order) {
  window.happy.ask(order)
}

function feel(name) {
  if (name === mood) return

  mood = name

  const found = MOODS[name] || MOODS.idle
  const root = document.documentElement

  root.style.setProperty('--glow', found.colours[0])
  root.style.setProperty('--glow-soft', `${found.colours[0]}88`)

  Aurora.mood(name)
  Orb.mood(name)

  const word = node('mood')
  word.classList.add('fade')

  setTimeout(() => {
    word.textContent = found.word
    word.classList.remove('fade')
  }, 180)
}

function settle(name) {
  resting = name

  if (name === 'idle' && sounding) return // STILL TALKING. GO QUIET WHEN THE SOUND DOES.

  clearTimeout(sounding)
  sounding = null

  feel(name)
}

function riding(seconds) {
  clearTimeout(sounding)

  feel('speaking')

  sounding = setTimeout(() => {
    sounding = null
    feel(resting)
  }, seconds * 1000 + TAIL_MS)
}

function quiet() {
  clearTimeout(sounding)

  sounding = null

  Orb.hush()
  feel(resting)
}

function hear(word) {
  const doing = {
    state: () => settle(word.state),
    level: () => Orb.level(word.level),
    envelope: () => {
      Orb.envelope(word.values, word.seconds)
      riding(word.seconds)
    },
    hush: () => quiet(),
    message: () => Talk.message(word),
    piece: () => Talk.piece(word.text),
    stats: () => Talk.spent(word),
    note: () => Talk.aside(word.text),
    trouble: () => Talk.aside(word.text, 'trouble'),
    settings: () => Knobs.show(word),
    history: () => Talk.history(word.messages),
    confirm: () => beg(word),
    ready: () => ready(word),
    gone: () => stopped(word),
  }

  if (doing[word.is]) doing[word.is]()
}

function ready(word) {
  key = word.key || ''
  node('hint').textContent = HELD.replace('{key}', key)
}

function stopped(word) {
  feel('gone')
  node('hint').textContent = word.reason || 'Happy is not running'
}

function beg(word) {
  const asking = node('asking')

  node('why').textContent = word.reason
  node('what').textContent = word.what
  asking.hidden = false

  const answer = (yes) => {
    ask({ do: 'answer', id: word.id, yes })
    asking.hidden = true
  }

  node('yes').onclick = () => answer(true)
  node('no').onclick = () => answer(false)
}

function tabs() {
  for (const tab of document.querySelectorAll('.tab')) {
    tab.onclick = () => {
      for (const other of document.querySelectorAll('.tab')) other.classList.remove('on')
      for (const pane of document.querySelectorAll('.pane')) pane.classList.remove('on')

      tab.classList.add('on')
      node(tab.dataset.pane).classList.add('on')
      node('slide').classList.toggle('right', tab.dataset.pane === 'controls')
    }
  }
}

function composer() {
  const form = node('composer')
  const box = node('typed')

  form.onsubmit = (event) => {
    event.preventDefault()

    const words = box.value.trim()
    if (!words) return

    ask({ do: 'say', text: words })
    box.value = ''
  }
}

function buttons() {
  const pin = node('pin')

  pin.onclick = () => {
    const on = !pin.classList.contains('on')
    pin.classList.toggle('on', on)
    window.happy.pin(on)
  }

  node('quit').onclick = () => window.happy.quit()
}

function boot() {
  Aurora.start(node('aurora'))
  Orb.start(node('orb'))
  Talk.start(node('stream'))
  Knobs.start(node('groups'), node('knobs'), ask)

  Talk.quiet('Nothing yet. Hold the key and talk, or type below.')

  tabs()
  composer()
  buttons()

  window.happy.hears(hear)
  ask({ do: 'hello' })
}

boot()
