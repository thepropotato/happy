// TWO PALETTES, BECAUSE THE ROOM AND THE FACE ARE ANSWERING DIFFERENT QUESTIONS.
//
// colours IS HAPPY HIMSELF — THE MOUTH'S LIP, A QUOTED SENTENCE, THE DOT THAT
// SAYS HE IS TALKING. IT STAYS GREEN THROUGH EVERY STATE, BECAUSE THE ONE
// THING ON THE PANEL THAT IS ACTUALLY HIM CANNOT CHANGE COLOUR SEVEN TIMES A
// MINUTE AND STILL READ AS ONE THING. HE IS SAGE GREEN.
//
// room IS THE LIGHT BEHIND HIM, AND IT CARRIES THE STATE: AMBER TO LISTEN,
// CYAN TO MAKE IT OUT, GREEN TO SPEAK, RED WHEN STOPPED. WITHOUT IT EVERY
// STATE WAS THE SAME COLOUR AT A DIFFERENT BRIGHTNESS, WHICH IS A DIFFERENCE
// YOU HAVE TO STARE AT THE PANEL TO SEE. WEARING IT ON THE FACE TOO IS WHAT
// MADE THIS LOOK LIKE SEVEN BRANDS ARGUING, SO THE FACE NO LONGER DOES.
const MOODS = {
  loading: { colours: ['#5b6b58', '#3a4538'], room: ['#4f554e', '#363b35'], word: 'waking up' },
  idle: { colours: ['#7fa37a', '#5d8159'], room: ['#658761', '#3f6b5a'], word: 'ready when you are' },
  listening: { colours: ['#9cbf96', '#6f9469'], room: ['#f5a524', '#f5604c'], word: 'listening' },
  hearing: { colours: ['#8fb38a', '#5d8159'], room: ['#22d3ee', '#3b82f6'], word: 'got it' },
  thinking: { colours: ['#7fa37a', '#4f7a4b'], room: ['#8fa36a', '#4f7a6a'], word: 'on it' },
  speaking: { colours: ['#9cbf96', '#7fa37a'], room: ['#34d399', '#22d3ee'], word: 'here you go' },
  gone: { colours: ['#3a3c3a', '#2c2e2c'], room: ['#ef4444', '#7f1d1d'], word: 'off duty' },
}

// HALF SIZE. IT IS ALL BLUR.
const COARSE = 2

function rgb(hex) {
  const value = parseInt(hex.slice(1), 16)
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255]
}

function toward(here, there, part) {
  return here.map((each, index) => each + (there[index] - each) * part)
}

const Aurora = (() => {
  let paint = null
  let canvas = null
  let blobs = []
  let target = MOODS.loading.room.map(rgb)
  let shown = target.map((each) => each.slice())
  let clock = 0

  function fit() {
    canvas.width = Math.max(1, Math.floor(canvas.clientWidth / COARSE))
    canvas.height = Math.max(1, Math.floor(canvas.clientHeight / COARSE))
  }

  function seed() {
    blobs = [0, 1, 2, 3].map((index) => ({
      x: 0.25 + 0.5 * (index % 2),
      y: 0.2 + 0.28 * index,
      drift: 0.4 + index * 0.31,
      swing: 0.16 + 0.05 * index,
      span: 0.5 + 0.16 * (index % 3),
      tint: index % 2,
    }))
  }

  function frame() {
    clock += 0.0045

    shown = shown.map((each, index) => toward(each, target[index], 0.03))

    const { width, height } = canvas
    paint.clearRect(0, 0, width, height)
    paint.globalCompositeOperation = 'lighter'

    for (const blob of blobs) {
      const x = (blob.x + Math.sin(clock * blob.drift) * blob.swing) * width
      const y = (blob.y + Math.cos(clock * blob.drift * 0.8) * blob.swing) * height
      const span = blob.span * width * (1 + 0.08 * Math.sin(clock * 1.7 + blob.drift))
      const [r, g, b] = shown[blob.tint]

      const wash = paint.createRadialGradient(x, y, 0, x, y, span)
      wash.addColorStop(0, `rgba(${r | 0}, ${g | 0}, ${b | 0}, 0.4)`)
      wash.addColorStop(0.55, `rgba(${r | 0}, ${g | 0}, ${b | 0}, 0.1)`)
      wash.addColorStop(1, 'rgba(0, 0, 0, 0)')

      paint.fillStyle = wash
      paint.beginPath()
      paint.arc(x, y, span, 0, Math.PI * 2)
      paint.fill()
    }

    paint.globalCompositeOperation = 'source-over'
    requestAnimationFrame(frame)
  }

  return {
    start(element) {
      canvas = element
      paint = canvas.getContext('2d')

      fit()
      seed()
      addEventListener('resize', fit)
      requestAnimationFrame(frame)
    },

    mood(name) {
      target = (MOODS[name] || MOODS.idle).room.map(rgb)
    },
  }
})()
