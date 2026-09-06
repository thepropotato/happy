// ONE PALETTE, LIKE THE MOUTH ITSELF. WHAT MOVES BETWEEN STATES IS HOW LIT THE
// ROOM IS, NEVER WHAT COLOUR IT IS: SEVEN HUES READ AS SEVEN BRANDS, AND AN
// ORANGE PANEL BEHIND A VIOLET MOUTH IS TWO PRODUCTS ARGUING. ONLY "STOPPED"
// LEAVES THE PALETTE, THE SAME WAY THE MOUTH DOES — BY DRAINING OUT OF IT.
const MOODS = {
  loading: { colours: ['#5b53a8', '#3a3568'], word: 'waking up' },
  idle: { colours: ['#8b7cff', '#6d5cf0'], word: 'ready' },
  listening: { colours: ['#a99cff', '#7c6bf5'], word: 'listening' },
  hearing: { colours: ['#9182ff', '#6d5cf0'], word: 'making it out' },
  thinking: { colours: ['#8b7cff', '#5b4bd8'], word: 'thinking' },
  speaking: { colours: ['#a99cff', '#8b7cff'], word: 'speaking' },
  gone: { colours: ['#3a3c47', '#2c2e38'], word: 'stopped' },
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
  let target = MOODS.loading.colours.map(rgb)
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
      target = (MOODS[name] || MOODS.idle).colours.map(rgb)
    },
  }
})()
