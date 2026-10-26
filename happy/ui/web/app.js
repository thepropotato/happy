const node = (id) => document.getElementById(id)

const HOLD = 'Hold <b>{key}</b> and tell me what you need.'
const DEAF = 'No key to talk on, so type it below.' // THE OS WOULD NOT HAND ONE OVER.

// SOUND OUTLIVES THE WORDS, SO GOING QUIET WAITS FOR THE LAST CLIP.
const TAIL_MS = 120

let mood = 'loading'
let resting = 'idle'
let sounding = null
let allowed = false // ASKED FOR ALREADY; ONLY A RESTART TAKES IT.
let actionMode = 'disabled'
let easing = null
let troubled = false // SOMETHING WENT WRONG IN THIS TURN.

let working = false // HAPPY IS MID TURN.
let reading = false // SOMETHING HAS ARRIVED WORTH THE ROOM.
let chosen = null // 'out' OR 'tucked' ONCE THE PERSON HAS SAID, AND NOTHING UNSAYS IT.

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

  const was = mood

  mood = name

  const found = MOODS[name] || MOODS.idle
  const root = document.documentElement

  root.style.setProperty('--glow', found.colours[0])
  root.style.setProperty('--glow-soft', `${found.colours[0]}88`)

  // THE STATE'S OWN COLOUR, WHICH IS NOT HIS: SEE THE TWO PALETTES IN aurora.js.
  root.style.setProperty('--state', found.room[0])
  root.style.setProperty('--state-soft', `${found.room[0]}88`)

  Aurora.mood(name)
  Smile.mood(name)

  // A TURN THAT HAS JUST ENDED GETS A FACE FOR A MOMENT: PLEASED, OR SORRY IT WENT WRONG.
  if (name === 'idle' && WORKING[was]) {
    Smile.react(troubled ? 'sorry' : 'pleased')
    troubled = false
  }

  working = name !== 'idle' && name !== 'gone'
  tucking()

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

  Smile.hush()
  feel(resting)
  refresh()
}

// THREE THINGS WOULD MOVE THE MOUTH: HAPPY IS MID TURN, SOMETHING ARRIVED TO READ,
// OR THE PERSON SAID SO. THE PERSON WINS, AND GOES ON WINNING UNTIL THEY SAY
// OTHERWISE — A CHOICE UNDONE BY THE NEXT THING HAPPY DOES WAS NEVER A CHOICE.
function tucking() {
  const tucked = chosen ? chosen === 'tucked' : working || reading

  node('glass').classList.toggle('tucked', tucked)
  node('glass').classList.toggle('blank', !reading)
}

function showing() {
  reading = true
  tucking()
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
    level: () => Smile.level(word.level),
    envelope: () => {
      Smile.envelope(word.values, word.seconds)
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
    unsaid: () => Talk.unsaid(word.text),
    began: () => {
      Talk.began(word)
      showing()
    },
    step: () => {
      if (word.failed) troubled = true
      Talk.step(word)
      showing()
    },
    done: () => {
      Talk.done()
      refresh()
    },
    stats: () => Talk.spent(word),
    trouble: () => {
      if (WORKING[resting]) troubled = true
      Talk.aside(word.text, 'trouble')
    },
    working: () => {
      Talk.aside(word.text, 'working')
      showing()
    },
    history: () => {
      Talk.history(word.messages)
      if (word.messages.some((each) => each.message || each.reply)) showing()
    },
    ready: () => ready(word),
    tint: () => Tint.apply(word.colour),
    shown: () => Talk.latest(),
    hint: () => {
      node('hint').textContent = word.text
    },
    gone: () => stopped(word),
  }

  if (doing[word.is]) doing[word.is]()
  else Settings.hear(word)

  if (word.is === 'ready' && word.name !== undefined && word.called) node('name').textContent = word.called
}

function ready(word) {
  node('hint').innerHTML = word.key ? HOLD.replace('{key}', word.key) : DEAF
  node('greeting').textContent = greeting(word.name)

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

function composer() {
  const form = node('composer')
  const box = node('typed')
  const action = node('action')

  refresh()

  box.addEventListener('input', () => {
    grown(box)
    refresh()
  })

  box.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return

    event.preventDefault()
    form.requestSubmit()
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

    box.value = ''
    grown(box)
    say(words)
  }

}

function say(words) {
  ask({ do: 'say', text: words })
  refresh()
}

// THE TIME OF DAY, AND THE FIRST NAME ON THIS COMPUTER'S ACCOUNT WHEN THERE IS ONE.
function greeting(name) {
  const hour = new Date().getHours()
  const part = hour < 5 ? 'Up late' : hour < 12 ? 'Morning' : hour < 17 ? 'Afternoon' : hour < 22 ? 'Evening' : 'Up late'

  return name ? `${part}, ${name}.` : `${part}.`
}

function grown(box) {
  const style = getComputedStyle(box)
  const edges = parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth)

  box.style.height = 'auto'
  box.style.height = `${box.scrollHeight + edges}px`
}

function buttons() {
  const pin = node('pin')

  pin.onclick = () => {
    const on = !pin.classList.contains('on')
    pin.classList.toggle('on', on)
    window.happy.pin(on)
  }

  node('tuck').onclick = () => window.happy.hide()

  // THE SETTINGS OPEN IN THE PANEL ITSELF, IN PLACE OF THE CONVERSATION.
  node('controls').onclick = () => Settings.toggle()
  node('amissfix').onclick = () => fixing()

  // THE TWO HALVES OF ONE TOGGLE, AND EITHER ONE IS THE PERSON SAYING WHERE THE
  // MOUTH BELONGS FROM NOW ON.
  node('small').onclick = () => {
    chosen = 'out'
    tucking()
  }

  node('face').onclick = () => {
    chosen = 'tucked'
    tucking()
  }

  addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return
    if (node('glass').classList.contains('tuning')) Settings.hide()
    else window.happy.hide()
  })
}

function boot() {
  Aurora.start(node('aurora'))
  Smile.start(node('face'), node('small'))
  Talk.start(node('stream'))
  Settings.start(node('settings'), node('glass'))
  Prose.away(node('stream'))

  // WHICH KEY IS NOT KNOWN YET AT BOOT, AND THE HINT UNDER THE MOUTH NAMES IT ANYWAY.
  Talk.quiet('')
  tucking()
  Ideas.start(node('ideas'), (words) => say(words))

  composer()
  buttons()

  window.happy.hears(hear)
  ask({ do: 'hello' })
}

boot()