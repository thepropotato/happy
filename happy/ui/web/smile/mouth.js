// THE WHOLE MOUTH AT ONE MOMENT: THE RESTING SHAPE, WHAT EACH MOOD ADDS TO IT, THEN THE PAINT.

function mascot(paint, w, h, mood, clock, energy) {
  let { wide, curve: sag, open, lip } = holding
  let liftL = 0, liftR = 0, shiftX = 0, tongue = 0, dead = 0

  // A MOOD JUST LEFT IS STILL PARTLY HERE, WHICH CARRIES THE MOTION ACROSS THE CHANGE.
  if (mixture.loading > 0.004) {
    const wake = 0.5 + 0.5 * Math.sin(clock * 1.15)
    wide += 0.04 * wake * mixture.loading
    dead += (0.45 - 0.25 * wake) * mixture.loading
  }

  if (mixture.idle > 0.004) {
    const breath = Math.sin(clock * 1.2)
    sag += 0.008 * breath * mixture.idle
    liftR += 0.018 * beat(clock, 7, 1.2) * mixture.idle
    liftL += 0.018 * beat(clock, 7, 1.2, 3.5) * mixture.idle
  }

  if (mixture.listening > 0.004) open += 0.05 * energy * mixture.listening
  if (mixture.hearing > 0.004) open += 0.008 * Math.sin(clock * 4) * mixture.hearing

  // PULLED TO ONE SIDE, ONE CORNER UP, WHILE THE DOTS TICK OVER.
  if (mixture.thinking > 0.004) {
    shiftX += 0.01 * w * Math.sin(clock * 0.7) * mixture.thinking
    liftR += (0.05 + 0.01 * Math.sin(clock * 0.9)) * mixture.thinking
  }

  // A REAL MOUTH ON REAL SOUND, NARROWING A LITTLE AS IT OPENS, THE WAY ONE ROUNDS ON A VOWEL.
  if (mixture.speaking > 0.004) {
    open += 0.07 * energy * mixture.speaking
    wide -= 0.04 * energy * mixture.speaking
    tongue += (0.55 + 0.45 * energy) * mixture.speaking
  }

  dead = Math.min(1, dead + mixture.gone)

  const W = w * wide, S = w * sag, O = w * open, L = w * lip
  const top = dead ? mix(SKIN.lip[0], SKIN.dead[0], dead) : rgb(SKIN.lip[0])
  const bottom = dead ? mix(SKIN.lip[1], SKIN.dead[1], dead) : rgb(SKIN.lip[1])
  const rim = dead ? mix(SKIN.rim, SKIN.dead[0], dead) : rgb(SKIN.rim)
  const deep = dead ? mix(SKIN.deep, '#1a1b22', dead) : rgb(SKIN.deep)

  const left = [-W / 2, -w * liftL]
  const right = [W / 2, -w * liftR]

  // THE UPPER LIP RISES AS THE MOUTH OPENS AND THE LOWER DROPS FURTHER, SO IT STAYS A SMILE.
  const upper = curve(left, right, S - O * 0.25)
  const lower = curve(left, right, S + O)
  const full = 1 + 0.25 * mixture.idle
  const upperHalf = (t) => L * (0.5 + 0.28 * Math.sin(t * Math.PI))
  const lowerHalf = (t) => L * (0.5 + 0.5 * full * Math.sin(t * Math.PI))

  paint.clearRect(0, 0, w, h)
  paint.save()
  paint.translate(w / 2 + shiftX, h / 2 - (S + O * 0.4) / 2)

  const band = paint.createLinearGradient(0, -L, 0, S + O + L)
  band.addColorStop(0, tint(top, 1))
  band.addColorStop(1, tint(bottom, 1))

  if (O > 0.5) {
    paint.save()
    paint.shadowColor = tint(bottom, dead ? 0 : 0.45)
    paint.shadowBlur = w * 0.08
    opening(paint, upper, lower)
    paint.fillStyle = tint(deep, 1)
    paint.fill()
    paint.restore()

    paint.save()
    opening(paint, upper, lower)
    paint.clip()
    inside(paint, lower, W, O, tongue, mixture.hearing, clock, w)
    paint.restore()
  }

  paint.save()
  paint.shadowColor = tint(bottom, dead ? 0 : 0.55)
  paint.shadowBlur = w * 0.06
  paint.fillStyle = band
  bandAlong(paint, lower, lowerHalf)
  bandAlong(paint, upper, upperHalf)
  paint.restore()

  // THE SHINE IS FOR A SHUT MOUTH ONLY, DOWN THE MIDDLE OF THE LIPS, AND IT FADES AS THEY PART.
  const shut = Math.max(0, 1 - O / (L * 0.5))

  if (shut > 0.01) {
    paint.fillStyle = tint(rim, (dead ? 0.25 : 0.7) * shut)
    bandAlongRange(paint, upper, (t) => lowerHalf(t) * 0.17, 0.16, 0.84, () => 0)
  }

  const radius = L * 1.1

  corner(paint, left[0], left[1], radius, top, bottom, dead)
  corner(paint, right[0], right[1], radius, top, bottom, dead)

  const sounding = Math.max(mixture.listening, mixture.speaking)
  const reach = W / 2 + radius * 1.4

  if (sounding > 0.01) {
    const strength = (0.45 + 0.55 * energy) * sounding
    arcs(paint, -reach, left[1] + O * 0.3, -1, w * 0.1, rgb(SKIN.lip[0]), strength)
    arcs(paint, reach, right[1] + O * 0.3, 1, w * 0.1, rgb(SKIN.lip[0]), strength)
  }

  if (mixture.thinking > 0.01) dots(paint, W * 0.3, right[1] - w * 0.08, w, rgb(SKIN.rim), mixture.thinking, clock)

  paint.restore()
}

function bandAlong(paint, along, half) {
  band(paint, along, half)
  paint.fill()
}

function bandAlongRange(paint, along, half, from, to, offset) {
  band(paint, along, half, from, to, offset)
  paint.fill()
}

// THE TONGUE AT THE BOTTOM OF THE OPENING, AND A PALE BAND READING ACROSS IT WHILE IT HEARS.
function inside(paint, lower, W, O, tongue, hearing, clock, w) {
  if (tongue > 0.02) {
    const [, y] = lower(0.5)
    const glow = paint.createLinearGradient(0, y - O, 0, y)
    glow.addColorStop(0, tint(rgb(SKIN.tongue[0]), 1))
    glow.addColorStop(1, tint(rgb(SKIN.tongue[1]), 1))
    paint.beginPath()
    paint.ellipse(0, y, W * 0.24, O * 0.55 * tongue, 0, 0, Math.PI * 2)
    paint.fillStyle = glow
    paint.fill()
  }

  if (hearing > 0.01) {
    const x = -W * 0.6 + ((clock * 0.75) % 1) * W * 1.2
    const sweep = paint.createLinearGradient(x - W * 0.2, 0, x + W * 0.2, 0)
    sweep.addColorStop(0, tint(rgb(SKIN.rim), 0))
    sweep.addColorStop(0.5, tint([255, 255, 255], 0.9 * hearing))
    sweep.addColorStop(1, tint(rgb(SKIN.rim), 0))
    paint.fillStyle = sweep
    paint.fillRect(-W, -w, W * 2, w * 2)
  }
}
