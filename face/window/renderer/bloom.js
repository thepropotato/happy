// THE CAPSULE'S OWN WIRING. IT HEARS THE SAME LINES THE PANEL DOES AND KEEPS
// ONLY THE TWO IT HAS ROOM FOR: WHAT HAPPY IS DOING, AND THE LAST THING SAID.

const node = (id) => document.getElementById(id)

// A GLANCE, NOT A TRANSCRIPT. PAST THIS THE LINE IS CUT AND THE PANEL HAS THE REST.
const ONE_LINE = 90

// WHAT THE PANEL DRAWS PROPERLY AND ONE LINE CANNOT: HERE THE MARKS WOULD ONLY
// EVER SHOW AS THEMSELVES, SO THEY COME OUT.
const MARKS = /(\*\*|__|~~|`+|^\s*#{1,6}\s+|^\s*[-*+]\s+|^\s*>\s?)/gm

// ANY OF THESE MEANS A TURN IS UNDER WAY, WHICH IS WHY THE CAPSULE IS UP. IT
// RAISES ITSELF OFF THEM AS WELL AS OFF "shown", BECAUSE A shown SENT WHILE THIS
// PAGE WAS STILL LOADING IS A shown NOBODY HEARD.
const UNDER_WAY = { listening: true, hearing: true, thinking: true, speaking: true }

let mood = 'idle'
let reply = ''

function up(on) {
  node('pill').classList.toggle('up', on)
}

function say(words) {
  node('said').textContent = cut(words)
}

function cut(words) {
  const said = String(words || '').replace(MARKS, '').replace(/\s+/g, ' ').trim()

  return said.length > ONE_LINE ? `${said.slice(0, ONE_LINE - 1)}…` : said
}

function feel(name) {
  if (name === mood) return

  mood = name
  Orb.mood(name)

  const found = MOODS[name] || MOODS.idle
  const word = node('mood')

  word.classList.add('fade')

  setTimeout(() => {
    word.textContent = found.word
    word.classList.remove('fade')
  }, 160)
}

function hear(word) {
  const doing = {
    // A TURN OF HIS OWN STARTS THE LINE OVER: WHAT WAS ON IT WAS THE LAST ONE.
    state: () => {
      if (word.state === 'hearing') reply = ''

      if (UNDER_WAY[word.state]) up(true)

      feel(word.state)
    },
    level: () => Orb.level(word.level),
    envelope: () => Orb.envelope(word.values, word.seconds),
    hush: () => Orb.hush(),
    message: () => say(word.text),
    piece: () => {
      reply += word.text
      say(reply)
    },
    trouble: () => say(word.text),
    gone: () => {
      feel('gone')
      say(word.reason || 'Happy is not running')
    },
    shown: () => up(true),
    hiding: () => up(false),
  }

  if (doing[word.is]) doing[word.is]()
}

function boot() {
  Orb.start(node('blob'))

  // THE CAPSULE IS THE WAY IN: WHOEVER TAPS IT WANTED THE WHOLE THING AFTER ALL.
  node('pill').onclick = () => window.happy.show()

  window.happy.hears(hear)
}

boot()
