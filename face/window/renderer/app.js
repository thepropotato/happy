const node = (id) => document.getElementById(id)

const WAKE = 'Say <b>{wake}</b> to talk'

// SOUND OUTLIVES THE WORDS, SO GOING QUIET WAITS FOR THE LAST CLIP.
const TAIL_MS = 120

let mood = 'loading'
let resting = 'idle'
let sounding = null
let allowed = false // ASKED FOR ALREADY; ONLY A RESTART TAKES IT.

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

function showing() {
  node('glass').classList.add('talking')
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
    message: () => {
      Talk.message(word)
      showing()
    },
    piece: () => {
      Talk.piece(word.text)
      showing()
    },
    began: () => {
      Talk.began(word)
      showing()
    },
    step: () => {
      Talk.step(word)
      showing()
    },
    done: () => Talk.done(),
    stats: () => Talk.spent(word),
    note: () => Talk.aside(word.text),
    trouble: () => Talk.aside(word.text, 'trouble'),
    settings: () => Knobs.show(word),
    history: () => {
      Talk.history(word.messages)
      if (word.messages.some((each) => each.message || each.reply)) showing()
    },
    confirm: () => beg(word),
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
  feel('gone')
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

function beg(word) {
  const asking = node('asking')

  node('why').textContent = word.reason
  node('what').textContent = word.what
  asking.hidden = false

    const answer = (yes) => {
      console.log('CLICKED', yes, word.id)
    ask({ do: 'answer', id: word.id, yes })
    asking.hidden = true
  }

  node('yes').onclick = () => answer(true)
  node('no').onclick = () => answer(false)
}

function visiting(on) {
  node('screen').classList.toggle('on', on)
  node('controls').classList.toggle('on', on)
}

function composer() {
  const form = node('composer')
  const box = node('typed')
  const pause = node('pause')

  form.onsubmit = (event) => {
    event.preventDefault()

    const words = box.value.trim()
    if (!words) return

    ask({ do: 'say', text: words })
    box.value = ''
  }

  pause.onclick = () => {
    ask({ do: 'stop' })
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

    if (!node('asking').hidden) return

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
