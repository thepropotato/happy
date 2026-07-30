// IT DRAWS INTO EVERY CANVAS IT WAS GIVEN, SO THE BIG ORB AND THE ONE IN THE
// HEADER ARE THE SAME ORB RATHER THAN TWO THAT DISAGREE.

const RESTING = { idle: 0.16, loading: 0.1, thinking: 0.42, gone: 0.06 }

const SMOOTH = 0.14 // HOW FAST THE SIZE CHASES WHAT IT SHOULD BE.
const MIC_GAIN = 5.5 // SPEECH SITS LOW IN A 0 TO 1 LOUDNESS.
const CLIP_GAIN = 7

const Orb = (() => {
  let faces = []
  let mood = 'loading'
  let energy = 0
  let clock = 0
  let mic = 0
  let clip = null
  let shown = [rgb(MOODS.loading.colours[0]), rgb(MOODS.loading.colours[1])]

  function wanted() {
    if (mood === 'listening') return Math.min(1, mic * MIC_GAIN)
    if (mood === 'speaking' && clip) return riding()

    const resting = RESTING[mood] ?? 0.2

    return resting * (1 + 0.35 * Math.sin(clock * (mood === 'thinking' ? 3.4 : 1.3)))
  }

  function riding() {
    const gone = (performance.now() - clip.at) / 1000
    const step = clip.seconds / Math.max(1, clip.values.length)
    const index = Math.floor(gone / step)

    if (index >= clip.values.length) {
      clip = null
      return 0.2
    }

    return Math.min(1, clip.values[index] * CLIP_GAIN)
  }

  function blob(paint, middle, span) {
    paint.beginPath()

    for (let step = 0; step <= 120; step += 1) {
      const angle = (step / 120) * Math.PI * 2
      const wobble =
        0.15 * Math.sin(angle * 3 + clock * 1.7) +
        0.11 * Math.sin(angle * 5 - clock * 1.1) +
        0.08 * Math.sin(angle * 7 + clock * 2.3)

      const reach = span * (1 + (0.06 + energy * 0.5) * wobble * 2)
      const x = middle + Math.cos(angle) * reach
      const y = middle + Math.sin(angle) * reach

      if (step === 0) paint.moveTo(x, y)
      else paint.lineTo(x, y)
    }

    paint.closePath()
  }

  function halo(paint, middle, span) {
    const [warm, cool] = shown
    const wash = paint.createRadialGradient(middle, middle, span * 0.2, middle, middle, span * 2.4)

    wash.addColorStop(0, tint(warm, 0.42))
    wash.addColorStop(0.4, tint(cool, 0.16))
    wash.addColorStop(1, tint(cool, 0))

    paint.fillStyle = wash
    paint.beginPath()
    paint.arc(middle, middle, span * 2.4, 0, Math.PI * 2)
    paint.fill()
  }

  function sweep(paint, middle, span, size) {
    if (mood !== 'thinking' && mood !== 'hearing') return

    const turn = clock * 1.9

    for (const [offset, width] of [[0, 1.1], [Math.PI, 0.7]]) {
      paint.beginPath()
      paint.arc(middle, middle, span * 1.5, turn + offset, turn + offset + width)
      paint.strokeStyle = tint(shown[0], 0.55)
      paint.lineWidth = size * 0.0057 // THE SAME WEIGHT AT EITHER SIZE.
      paint.lineCap = 'round'
      paint.stroke()
    }
  }

  function ring(paint, middle, span, size) {
    paint.beginPath()
    paint.arc(middle, middle, span * (1.28 + energy * 0.3), 0, Math.PI * 2)
    paint.strokeStyle = tint(shown[1], 0.22 + energy * 0.3)
    paint.lineWidth = size * 0.0027
    paint.stroke()
  }

  function draw(canvas) {
    const paint = canvas.getContext('2d')
    const size = canvas.width
    const middle = size / 2
    const span = size * 0.17 * (1 + energy * 0.42)

    paint.clearRect(0, 0, size, size)
    halo(paint, middle, span)
    sweep(paint, middle, span, size)
    ring(paint, middle, span, size)

    const skin = paint.createLinearGradient(
      middle - span, middle - span, middle + span, middle + span,
    )
    skin.addColorStop(0, tint(shown[0], 0.95))
    skin.addColorStop(1, tint(shown[1], 0.85))

    blob(paint, middle, span)
    paint.fillStyle = skin
    paint.shadowColor = tint(shown[0], 0.7)
    paint.shadowBlur = size * 0.077 + energy * size * 0.104
    paint.fill()
    paint.shadowBlur = 0
  }

  function frame() {
    clock += 0.016
    energy += (wanted() - energy) * SMOOTH
    shown = shown.map((each, index) =>
      toward(each, rgb((MOODS[mood] || MOODS.idle).colours[index]), 0.05),
    )

    for (const face of faces) draw(face)

    requestAnimationFrame(frame)
  }

  function tint(colour, alpha) {
    const [r, g, b] = colour
    return `rgba(${r | 0}, ${g | 0}, ${b | 0}, ${alpha})`
  }

  return {
    start(...canvases) {
      faces = canvases
      requestAnimationFrame(frame)
    },

    mood(name) {
      mood = name
      if (name !== 'speaking') clip = null
      if (name !== 'listening') mic = 0
    },

    level(value) {
      mic = value
    },

    envelope(values, seconds) {
      if (values && values.length) clip = { values, seconds, at: performance.now() }
    },

    hush() {
      clip = null
    },
  }
})()
