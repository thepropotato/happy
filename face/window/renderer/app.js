const node = (id) => document.getElementById(id)

const WAKE = 'Say <b>{wake}</b> to talk'

// SOUND OUTLIVES THE WORDS, SO GOING QUIET WAITS FOR THE LAST CLIP.
const TAIL_MS = 120

let mood = 'loading'
let resting = 'idle'
let sounding = null
let allowed = false // ASKED FOR ALREADY; ONLY A RESTART TAKES IT.
let actionMode = 'disabled'
let easing = null

// WHAT THERE IS TO STOP: HAPPY WORKING ON A TURN, OR A CLIP STILL PLAYING. NOT
// listening — HE IS WAITING ON YOU THERE, AND THERE IS NOTHING TO INTERRUPT.
const WORKING = { hearing: true, thinking: true, speaking: true }

// THE LAST CLIP OF A REPLY LANDS A MOMENT AFTER THE REPLY ITSELF ENDS, SO THE
// BUTTON WAITS THAT LONG BEFORE GIVING PAUSE UP RATHER THAN BLINKING TWICE.
const FINISH_GRACE_MS = 400

const SEND_ICON = '<path d="m5 12 14 0 m-6 -6 6 6 -6 6" />'
const PAUSE_ICON = '<rect x="7" y="7" width="10" height="10" rx="1.5" />'

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

  node('glass').classList.toggle('busy', name !== 'idle' && name !== 'gone')

  Talk.doing(name, found.word)

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
  refresh()

  sounding = setTimeout(() => {
    sounding = null
    feel(resting)

    refresh()
  }, seconds * 1000 + TAIL_MS)
}

function quiet() {
  clearTimeout(sounding)

  sounding = null

  Orb.hush()
  feel(resting)
  refresh()
}

function showing() {
  node('glass').classList.add('talking')
}

function modeFromContext() {
  if (node('typed').value.trim()) return 'send'

  // ASKED OF THE STATE HAPPY IS ACTUALLY IN, NEVER OF A FLAG SET ALONGSIDE IT: A
  // TURN THAT ENDED IN A WAY NOBODY THOUGHT OF LEFT THE FLAG ON, AND THE BUTTON
  // SAT ON pause FOR THE REST OF THE EVENING WITH NOTHING LEFT TO PAUSE.
  return WORKING[resting] || sounding ? 'pause' : 'disabled'
}

function refresh() {
  const next = modeFromContext()

  clearTimeout(easing)
  easing = null

  // ANYTHING BUT LETTING GO OF pause HAPPENS AT ONCE. TYPING IS ANSWERED ON THE
  // KEYSTROKE, AND A TURN STARTING SHOWS UP THE MOMENT IT STARTS.
  if (next !== 'disabled' || actionMode !== 'pause') {
    setActionMode(next)
    return
  }

  easing = setTimeout(() => {
    easing = null
    setActionMode(modeFromContext())
  }, FINISH_GRACE_MS)
}

function setActionMode(next) {
  const action = node('action')
  const icon = node('action-icon')

  actionMode = next

  action.classList.remove('disabled', 'send', 'pause')
  action.classList.add(next)

  action.disabled = next === 'disabled'
  action.setAttribute('aria-label', next === 'pause' ? 'Pause' : 'Send')
  icon.innerHTML = next === 'pause' ? PAUSE_ICON : SEND_ICON
}

function hear(word) {
  const doing = {
    state: () => {
      settle(word.state)
      refresh()
    },
    level: () => Orb.level(word.level),
    envelope: () => {
      Orb.envelope(word.values, word.seconds)
      riding(word.seconds)
    },
    hush: () => quiet(),
    message: () => {
      Talk.message(word)
      showing()
    },
    piece: () => {
      Talk.piece(word.text)
      showing()
      refresh()
    },
    began: () => {
      Talk.began(word)
      showing()
    },
    step: () => {
      Talk.step(word)
      showing()
    },
    done: () => {
      Talk.done()
      refresh()
    },
    stats: () => Talk.spent(word),
    note: () => Talk.aside(word.text),
    trouble: () => Talk.aside(word.text, 'trouble'),
    settings: () => Knobs.show(word),
    history: () => {
      Talk.history(word.messages)
      if (word.messages.some((each) => each.message || each.reply)) showing()
    },
    ready: () => ready(word),
    gone: () => stopped(word),
  }

  if (doing[word.is]) doing[word.is]()
}

function ready(word) {
  const wake = word.wake || 'his name'

  node('hint').innerHTML = WAKE.replace('{wake}', wake)

  amiss(word.amiss || '')
}

function stopped(word) {
  settle('gone') // NOT feel: NOTHING IS COMING, SO THE STATE UNDERNEATH IS GONE TOO.
  refresh()

  node('hint').textContent = word.reason || 'Happy is not running'
}

// THE ONE PERMISSION HAPPY IS STILL WAITING ON, IN HIS OWN WORDS. HEARING NEEDS
// NONE NOW; READING A WINDOW AND CLICKING IN IT BOTH STILL DO.
function amiss(words) {
  node('amiss').hidden = !words

  if (!words) return

  node('amisswords').textContent = words
  node('amissfix').textContent = allowed ? 'Restart' : 'Allow'
}

function fixing() {
  if (allowed) {
    window.happy.restart() // WHAT WAS BUILT WITHOUT THE PERMISSION NEVER GETS IT.
    return
  }

  allowed = true
  window.happy.allow()
  node('amissfix').textContent = 'Restart'
}

function visiting(on) {
  node('screen').classList.toggle('on', on)
  node('controls').classList.toggle('on', on)
}

function composer() {
  const form = node('composer')
  const box = node('typed')
  const action = node('action')

  refresh()

  box.addEventListener('input', () => {
    refresh()
  })

  action.onclick = (event) => {
    if (actionMode !== 'pause') return

    event.preventDefault()
    ask({ do: 'stop' })

    // THE TURN ENDING IS WHAT PUTS THE BUTTON BACK, AND ASKING FOR IT IS NOT THE
    // SAME AS IT HAVING HAPPENED. hush AND THE END OF THE TURN BOTH COME BACK.
  }

  form.onsubmit = (event) => {
    event.preventDefault()

    if (actionMode !== 'send') return

    const words = box.value.trim()
    if (!words) return

    ask({ do: 'say', text: words })
    box.value = ''
    refresh()
  }
}

function buttons() {
  const pin = node('pin')

  pin.onclick = () => {
    const on = !pin.classList.contains('on')
    pin.classList.toggle('on', on)
    window.happy.pin(on)
  }

  node('tuck').onclick = () => window.happy.hide()
  node('controls').onclick = () => visiting(!node('screen').classList.contains('on'))
  node('back').onclick = () => visiting(false)
  node('amissfix').onclick = () => fixing()

  // THE TWO HALVES OF ONE TOGGLE. WITHOUT THE SECOND, THE BIG ORB IS A ONE WAY TRIP:
  // ONLY SOMETHING NEW BEING SAID WOULD EVER PUT IT BACK IN THE CORNER.
  node('puck').onclick = () => node('glass').classList.remove('talking')
  node('orb').onclick = () => node('glass').classList.add('talking')

  addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return

    if (node('screen').classList.contains('on')) visiting(false)
    else window.happy.hide()
  })
}

function boot() {
  Aurora.start(node('aurora'))
  Orb.start(node('orb'), node('puck'))
  Talk.start(node('stream'))
  Knobs.start(node('rows'), ask)

  Talk.quiet('Nothing yet. Say his name and talk, or type below.')

  composer()
  buttons()

  window.happy.hears(hear)
  ask({ do: 'hello' })
}

boot()