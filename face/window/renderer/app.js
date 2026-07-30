// EVERYTHING HAPPY SAYS ARRIVES HERE AND IS HANDED TO WHICHEVER PART OF THE
// PANEL CARES ABOUT IT. NOTHING IN HERE DECIDES ANYTHING ON ITS OWN.

const node = (id) => document.getElementById(id)

const MAC = navigator.userAgent.includes('Mac')

// THE KEY, SHORT ENOUGH FOR THE HEADER. THE SAME KEY IS CALLED DIFFERENT THINGS
// ON THE TWO PLATFORMS, AND A MAC SYMBOL ON WINDOWS IS JUST A BOX.
const CAPS = MAC
  ? { alt_r: '⌥ R', alt_l: '⌥ L', cmd_r: '⌘ R', cmd_l: '⌘ L', ctrl_r: '⌃ R', ctrl_l: '⌃ L',
      shift_r: '⇧ R', caps_lock: '⇪', f13: 'F13' }
  : { alt_r: 'Alt R', alt_l: 'Alt L', cmd_r: 'Win R', cmd_l: 'Win L', ctrl_r: 'Ctrl R',
      ctrl_l: 'Ctrl L', shift_r: 'Shift R', caps_lock: 'Caps', f13: 'F13' }

const HELD = 'Hold <b>{key}</b> to talk'

const DEAF = 'Happy only hears <b>{key}</b> while this window is in front.'

// SOUND OUTLIVES THE WORDS: HAPPY IS STILL A SENTENCE BEHIND HIMSELF WHEN THE
// STREAM ENDS, SO GOING QUIET WAITS FOR THE LAST CLIP RATHER THAN THE LAST WORD.
const TAIL_MS = 120

let mood = 'loading'
let resting = 'idle'
let sounding = null
let allowed = false // THE PERMISSION HAS BEEN ASKED FOR, AND ONLY A RESTART TAKES IT.

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

  // THE KEY IS DOWN FOR EXACTLY AS LONG AS HE IS LISTENING, WHICH IS THE ONLY
  // PROOF A GLOBAL LISTENER CAN GIVE FROM BEHIND ANOTHER WINDOW.
  node('keycap').classList.toggle('down', name === 'listening')

  // THE ORB GETS OUT OF THE WAY WHILE THERE IS SOMETHING HAPPENING TO READ.
  node('glass').classList.toggle('busy', name !== 'idle' && name !== 'gone')

  for (const word of [node('mood'), node('doing')]) {
    word.classList.add('fade')

    setTimeout(() => {
      word.textContent = found.word
      word.classList.remove('fade')
    }, 180)
  }
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

// ONCE THERE ARE WORDS, THEY GET THE PANEL AND THE ORB CARRIES ON IN THE HEADER.
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
    stats: () => Talk.spent(word),
    note: () => Talk.aside(word.text),
    trouble: () => Talk.aside(word.text, 'trouble'),
    settings: () => Knobs.show(word),
    history: () => {
      Talk.history(word.messages)
      if (word.messages.some((each) => each.who === 'you' || each.who === 'happy')) showing()
    },
    confirm: () => beg(word),
    ready: () => ready(word),
    gone: () => stopped(word),
  }

  if (doing[word.is]) doing[word.is]()
}

function ready(word) {
  const said = word.key || ''
  const cap = CAPS[word.code] || said.split(' / ')[0] || 'the key'

  node('keyname').textContent = cap
  node('keycap').hidden = !said
  node('hint').innerHTML = HELD.replace('{key}', said.split(' / ')[0])

  amiss(Boolean(word.deaf), cap)
}

function stopped(word) {
  feel('gone')
  node('hint').textContent = word.reason || 'Happy is not running'
}

// MACOS HANDS AN UNTRUSTED LISTENER ONLY THE KEYS MEANT FOR THIS WINDOW, WHICH
// LOOKS EXACTLY LIKE PUSH TO TALK WORKING UNTIL YOU CLICK ON SOMETHING ELSE. THE
// PERMISSION BELONGS TO THIS APP, SO THIS IS WHERE IT IS ASKED FOR.
function amiss(on, cap) {
  node('amiss').hidden = !on
  node('keycap').classList.toggle('deaf', on)

  if (!on) return

  node('amisswords').innerHTML = DEAF.replace('{key}', cap)
  node('amissfix').textContent = allowed ? 'Restart' : 'Allow'
}

function fixing() {
  if (allowed) {
    window.happy.restart() // A LISTENER BUILT WITHOUT THE PERMISSION STAYS DEAF.
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
  node('controls').onclick = () => visiting(!node('screen').classList.contains('on'))
  node('back').onclick = () => visiting(false)
  node('amissfix').onclick = () => fixing()

  // THE BIG ORB BACK, FOR ANYBODY WHO WOULD RATHER LOOK AT HIM THAN READ HIM.
  node('puck').onclick = () => node('glass').classList.remove('talking')

  // THE WAY OUT OF ANYTHING IS THE KEY IT IS EVERYWHERE ELSE ON THE COMPUTER.
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

  Talk.quiet('Nothing yet. Hold the key and talk, or type below.')

  composer()
  buttons()

  window.happy.hears(hear)
  ask({ do: 'hello' })
}

boot()
