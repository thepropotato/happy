// IT DRAWS INTO EVERY CANVAS IT WAS GIVEN, SO THE BIG ORB AND THE ONE IN THE
// HEADER ARE THE SAME ORB RATHER THAN TWO THAT DISAGREE.

const RESTING = { idle: 0.16, loading: 0.1, thinking: 0.42, gone: 0.06 }

const SMOOTH = 0.14 // HOW FAST THE SIZE CHASES WHAT IT SHOULD BE.
const MIC_GAIN = 5.5 // SPEECH SITS LOW IN A 0 TO 1 LOUDNESS.
const CLIP_GAIN = 7

// THE EYES ARE HOLES PUNCHED BACK OUT OF THE ORB, AND THEIR GEOMETRY IS THE
// WHOLE EXPRESSION — EVERY MEASURE BELOW IS A FRACTION OF THE ORB'S WIDTH.
const EYES = {
  loading: { dx: 0.165, dy: 0, wide: 0.15, tall: 0.035, round: 0.02 },
  idle: { dx: 0.165, dy: 0, wide: 0.15, tall: 0.28, round: 0.075 },
  listening: { dx: 0.175, dy: 0, wide: 0.13, tall: 0.44, round: 0.065 },
  hearing: { dx: 0.193, dy: -0.005, wide: 0.095, tall: 0.25, round: 0.047 },
  thinking: { dx: 0.165, dy: -0.06, wide: 0.13, tall: 0.3, round: 0.065 },
  speaking: { dx: 0.148, dy: -0.023, wide: 0.185, tall: 0.115, round: 0.1, dome: true },
  gone: { dx: 0.18, dy: 0.083, wide: 0.16, tall: 0.045, round: 0.022, splay: 0.26 },
}

// HOW FAR THE WHOLE ORB TIPS, IN RADIANS — LEANING IN IS THE POSTURE HALF.
const TILT = { listening: -0.122, thinking: 0.087, gone: -0.087 }

const WHITE = [255, 255, 255]
const BLACK = [0, 0, 0]

const SHUT = 0.035 // A CLOSED EYE, WHATEVER IT WAS OPEN.
const BLINK_FOR = 0.12

// THE HEIGHTS THINKING WALKS THROUGH, EACH SIDE ON ITS OWN CLOCK SO THE PAIR
// DRIFTS THROUGH EVERY COMBINATION AND NEVER SETTLES INTO A FIXED FACE.
// NOTHING GOES BELOW A SQUINT — AN EYE SHRUNK TO A DOT READS AS A FAULT.
const MULLING = {
  left: { over: 3.1, tall: [0.34, 0.19, 0.3, 0.16, 0.26] },
  right: { over: 3.7, tall: [0.18, 0.32, 0.17, 0.29] },
}

// WHERE THINKING LOOKS, AS THE PAIR WANDERS THE UPPER FIELD TOGETHER.
const PONDER_X = [0, -0.05, 0.045, 0.01]
const PONDER_Y = [0, -0.025, -0.045, 0.015]

// READING A LINE IN HARD STEPS, THEN A CARRIAGE RETURN BACK AND DOWN.
const PARSE = [[-0.05, 0], [-0.017, 0], [0.017, 0], [0.05, 0], [-0.05, 0.022]]

const Orb = (() => {
  let faces = []
  let mood = 'loading'
  let energy = 0
  let clock = 0
  let mic = 0
  let clip = null
  let blinking = 0 // WHEN THE EYE THAT IS SHUT OPENS AGAIN.
  let due = 3 // WHEN THE NEXT ONE IS OWED.
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

  // THE HIGHLIGHT SITS UP AND LEFT, THE MOOD RUNS THROUGH THE MIDDLE, AND THE
  // RIM DARKENS — radial-gradient(circle at 32% 28%, ...) DRAWN BY HAND.
  function skin(paint, middle, span) {
    const wash = paint.createRadialGradient(
      middle - span * 0.36, middle - span * 0.44, span * 0.04,
      middle - span * 0.36, middle - span * 0.44, span * 1.5,
    )

    wash.addColorStop(0, tint(mixed(shown[0], WHITE, 0.45), 1))
    wash.addColorStop(0.55, tint(shown[0], 1))
    wash.addColorStop(1, tint(mixed(shown[1], BLACK, 0.3), 1))

    return wash
  }

  // WALKS A RING OF VALUES SMOOTHLY, ONE FULL LAP EVERY over SECONDS.
  function among(values, over) {
    const place = ((clock / over) % 1) * values.length
    const index = Math.floor(place)
    const part = place - index
    const here = values[index]
    const next = values[(index + 1) % values.length]

    return here + (next - here) * (0.5 - 0.5 * Math.cos(part * Math.PI))
  }

  // THE SAME RING, BUT IT JUMPS RATHER THAN SLIDES.
  function stepped(values, over) {
    return values[Math.floor(((clock / over) % 1) * values.length)]
  }

  // ONE EYE, AS IT STANDS THIS INSTANT.
  function eye(side) {
    const base = EYES[mood] || EYES.idle
    const out = side === 'left' ? -1 : 1
    let { dx, dy, wide, tall, round } = base

    dx *= out

    if (mood === 'idle') {
      dx += among([0, -0.022, -0.022, 0.022, 0.022], 7)
      if (clock < blinking) tall = SHUT
    }

    // WAKING UP IS SHUT, BUT IT STRUGGLES OPEN EVERY FEW SECONDS.
    if (mood === 'loading') tall *= among([1, 1, 1, 3.4, 1], 3.4)

    if (mood === 'listening') {
      tall *= 1 + 0.05 * Math.sin(clock * 2.24)
      dy -= 0.015 * Math.sin(clock * 2.24)
      if (side === 'right') dx -= 0.02 // THE EYES SLIDE INTO THE LEAN.
    }

    if (mood === 'hearing') {
      const [across, down] = stepped(PARSE, 1.6)
      dx += across
      dy += down
    }

    if (mood === 'thinking') {
      const own = MULLING[side]

      tall = among(own.tall, own.over)
      dx += among(PONDER_X, 4.4)
      dy += among(PONDER_Y, 4.4)
    }

    // SPEAKING SQUASHES ON THE SOUND ITSELF RATHER THAN ON A FIXED BEAT.
    if (mood === 'speaking') tall *= 1 - 0.34 * Math.min(1, energy)

    return { dx, dy, wide, tall, round, dome: base.dome, splay: (base.splay || 0) * -out }
  }

  function eyes(paint, middle, span) {
    const width = span * 2

    paint.save()
    paint.globalCompositeOperation = 'destination-out'

    for (const side of ['left', 'right']) {
      const { dx, dy, wide, tall, round, dome, splay } = eye(side)
      const w = wide * width
      const h = Math.max(tall * width, 1)
      const r = Math.min(round * width, w / 2, h / 2)

      paint.save()
      paint.translate(middle + dx * width, middle + dy * width)
      if (splay) paint.rotate(splay)
      paint.beginPath()
      paint.roundRect(-w / 2, -h / 2, w, h, dome ? [r, r, 0, 0] : r)
      paint.fill()
      paint.restore()
    }

    paint.restore()
  }

  function draw(canvas) {
    const paint = canvas.getContext('2d')
    const size = canvas.width
    const middle = size / 2
    const span = size * 0.17 * (1 + energy * 0.42)

    paint.clearRect(0, 0, size, size)

    // THE POSTURE AND THE FACE TIP TOGETHER.
    paint.save()
    paint.translate(middle, middle)
    paint.rotate(lean())
    paint.translate(-middle, -middle)

    // A PLAIN CIRCLE, AND THE GLOW IS ITS SHADOW RATHER THAN A WASH BEHIND IT.
    paint.beginPath()
    paint.arc(middle, middle, span, 0, Math.PI * 2)
    paint.fillStyle = skin(paint, middle, span)
    paint.shadowColor = tint(shown[0], 0.45)
    paint.shadowBlur = span * (0.85 + energy * 0.6)
    paint.fill()
    paint.shadowBlur = 0

    eyes(paint, middle, span)
    paint.restore()
  }

  // LISTENING LEANS IN AND DRIFTS WHILE IT WAITS, THINKING TIPS BACK.
  function lean() {
    const rest = TILT[mood] || 0

    if (mood === 'listening') return rest + 0.026 * Math.sin(clock * 2.24)

    return rest
  }

  function frame() {
    clock += 0.016
    energy += (wanted() - energy) * SMOOTH

    // ONLY READY BLINKS — EVERY OTHER STATE HOLDS ITS POSE.
    if (mood === 'idle' && clock > due) {
      blinking = clock + BLINK_FOR
      due = clock + 2.4 + Math.random() * 3
    }
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

  // WHAT color-mix(in srgb, colour X%, other) COMES TO.
  function mixed(colour, other, part) {
    return colour.map((each, index) => each + (other[index] - each) * part)
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
