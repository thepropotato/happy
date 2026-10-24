// THE MOUTH KEPT MOVING: ONE FRAME LOOP FOR EVERY CANVAS IT WAS GIVEN, RIDING THE MICROPHONE
// WHILE HE LISTENS AND HIS OWN VOICE WHILE HE SPEAKS, AND A FACE FOR A MOMENT WHEN A TURN ENDS.

const MIC_GAIN = 5.5 // SPEECH SITS LOW IN A 0 TO 1 LOUDNESS.
const CLIP_GAIN = 7
const SMOOTH = 0.16 // HOW FAST THE OPENING CHASES THE SOUND.

// HOW LONG A PASSING LOOK IS WORN BEFORE HE GOES BACK TO RESTING.
const MOMENT = { pleased: 1600, sorry: 2400 }

const Smile = (() => {
  let faces = []
  let mood = 'loading'
  let passing = null
  let energy = 0
  let clock = 0
  let mic = 0
  let clip = null

  function wanted() {
    if (mood === 'listening') return Math.min(1, mic * MIC_GAIN)
    if (mood === 'speaking') return clip ? riding() : Math.min(1, mic * CLIP_GAIN)

    return 0
  }

  function riding() {
    const gone = (performance.now() - clip.at) / 1000
    const index = Math.floor(gone / (clip.seconds / Math.max(1, clip.values.length)))

    if (index >= clip.values.length) {
      clip = null
      return 0.2
    }

    return Math.min(1, clip.values[index] * CLIP_GAIN)
  }

  function showing() {
    if (passing && performance.now() < passing.until) return passing.name

    passing = null

    return mood
  }

  function frame() {
    clock += 0.016
    energy += (wanted() - energy) * SMOOTH

    const now = showing()

    // ONCE PER FRAME, NOT PER CANVAS, SO TWO CANVASES CANNOT WALK THE SHAPE TWICE AS FAST.
    towards(now)

    for (const canvas of faces) {
      const scale = devicePixelRatio || 1
      const wide = canvas.clientWidth || canvas.width
      const tall = canvas.clientHeight || canvas.height

      if (canvas.width !== Math.round(wide * scale) || canvas.height !== Math.round(tall * scale)) {
        canvas.width = Math.round(wide * scale)
        canvas.height = Math.round(tall * scale)
      }

      const paint = canvas.getContext('2d')

      paint.setTransform(scale, 0, 0, scale, 0, 0)
      mascot(paint, wide, tall, now, clock, energy)
    }

    requestAnimationFrame(frame)
  }

  return {
    start(...canvases) {
      faces = canvases
      requestAnimationFrame(frame)
    },

    mood(name) {
      if (!SHAPES[name]) name = 'idle'
      if (name !== 'idle') passing = null
      if (name !== 'speaking') clip = null
      if (name !== 'listening' && name !== 'speaking') mic = 0

      mood = name
    },

    react(name) {
      if (MOMENT[name]) passing = { name, until: performance.now() + MOMENT[name] }
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
