// IT DRAWS INTO EVERY CANVAS IT WAS GIVEN, SO THE BIG MASCOT AND THE ONE IN THE
// HEADER ARE THE SAME MASCOT RATHER THAN TWO THAT DISAGREE.
//
// HAPPY IS A MOUTH — NO EYES, NO FACE. AN UPPER AND A LOWER LIP MEET AT TWO BALL
// CORNERS AND THE SPACE BETWEEN THEM IS SOLID COLOUR. IT WEARS ONE PALETTE IN
// EVERY STATE: THE MOOD IS TOLD BY HOW WIDE THE MOUTH OPENS AND BY WHAT IS GOING
// ON AROUND IT, NEVER BY RECOLOURING THE FACE, BECAUSE SEVEN HUES READ AS SEVEN
// BRANDS. ONLY "STOPPED" LEAVES THE PALETTE, BY DRAINING OUT OF IT.

const MIC_GAIN = 5.5 // SPEECH SITS LOW IN A 0 TO 1 LOUDNESS.
const CLIP_GAIN = 7
const SMOOTH = 0.16 // HOW FAST THE OPENING CHASES THE SOUND.

const SKIN = {
  lip:   ['#8b7cff', '#6d5cf0'],   // THE LIP BAND ITSELF.
  rim:   '#a99cff',                // THE LIT TOP EDGE.
  deep:  '#241a52',                // INSIDE THE MOUTH.
  tongue:['#f06ec0', '#c94fa8'],
  dead:  ['#3a3c47', '#2c2e38'],   // WHAT IT ALL FADES TO WHEN NOTHING IS RUNNING.
}

// THE MOUTH, AS A FRACTION OF THE DRAWING'S WIDTH. IT STAYS A SMILE IN EVERY
// STATE — WHAT CHANGES IS HOW WIDE, HOW OPEN, AND WHAT IS GOING ON AROUND IT.
//   wide  CORNER TO CORNER          open  HOW FAR THE LIPS PART
//   curve HOW FAR IT BOWS           lip   THE THICKNESS OF THE BAND
const SHAPES = {
  loading:   { wide:0.34, curve:0.13, open:0.00,  lip:0.030, tilt:0 },
  idle:      { wide:0.46, curve:0.20, open:0.00,  lip:0.038, tilt:0 },
  listening: { wide:0.44, curve:0.19, open:0.155, lip:0.030, tilt:0 },
  hearing:   { wide:0.44, curve:0.19, open:0.160, lip:0.030, tilt:0 },
  thinking:  { wide:0.38, curve:0.17, open:0.015, lip:0.035, tilt:0 },
  speaking:  { wide:0.42, curve:0.16, open:0.175, lip:0.030, tilt:0 },
  gone:      { wide:0.40, curve:0.13, open:0.00,  lip:0.032, tilt:0 },
}

function tint(c,a){ return `rgba(${c[0]|0}, ${c[1]|0}, ${c[2]|0}, ${a})` }
function among(vals, over, clock){
  const p=((clock/over)%1)*vals.length, i=Math.floor(p), f=p-i
  const a=vals[i], b=vals[(i+1)%vals.length]
  return a+(b-a)*(0.5-0.5*Math.cos(f*Math.PI))
}
// ONE PULSE EVERY every SECONDS, LASTING for — FOR THE THINGS A FACE DOES ONCE
// IN A WHILE RATHER THAN CONSTANTLY.
function beat(clock, every, forHowLong, offset){
  const t = ((clock + (offset||0)) % every) / forHowLong
  return t > 1 ? 0 : Math.sin(t*Math.PI)
}
function mix(a, b, t){ return toward(rgb(a), rgb(b), t) }

// THE SOUND ARCS EITHER SIDE OF THE MOUTH — THREE NESTED BRACKETS THAT BREATHE.
function arcs(paint, x, span, sign, colour, strength, clock, w){
  for (let i = 0; i < 3; i++){
    const r = span * (0.55 + i*0.30)
    const fade = Math.max(0, strength - i*0.22)
    if (fade <= 0.01) continue
    paint.beginPath()
    paint.lineWidth = w*0.016
    paint.lineCap = 'round'
    paint.strokeStyle = tint(colour, fade*0.9)
    paint.arc(x, 0, r, sign*-0.62, sign*0.62, sign < 0)
    paint.stroke()
  }
}

// HOW FAR EACH LIP SWELLS AT ITS MIDDLE, AS A MULTIPLE OF THE LIP THICKNESS.
// THE LOWER LIP IS THE FULLER OF THE TWO, WHICH IS TRUE OF MOST MOUTHS. THIS IS
// "READY" ONLY — EVERY OTHER STATE IS ONE WIDTH FROM CORNER TO CORNER.
const FULLNESS = { upper: 1.30, lower: 1.70 }
const FLAT = { upper: 0, lower: 0 }

// ONE LIP, AS A FILLED SHAPE. IT WALKS THE CURVE FROM CORNER TO CORNER AND
// OFFSETS EACH POINT PERPENDICULARLY BY A THICKNESS THAT IS FATTEST IN THE
// MIDDLE AND ZERO AT BOTH ENDS, SO THE LIP MEETS THE CORNERS IN A POINT.
function ribbon(paint, lx, ly, rx, ry, ctrlY, L, fullness){
  const STEPS = 26
  const at = (t) => {
    const u = 1-t
    return [u*u*lx + 2*u*t*0 + t*t*rx, u*u*ly + 2*u*t*ctrlY + t*t*ry]
  }

  const outer = [], inner = []

  for (let i = 0; i <= STEPS; i++){
    const t = i/STEPS
    const [x, y] = at(t)
    // THE TANGENT, SO THE THICKNESS IS LAID DOWN ACROSS THE CURVE, NOT DOWN THE PAGE.
    const [ax, ay] = at(Math.max(0, t-0.01))
    const [bx, by] = at(Math.min(1, t+0.01))
    const len = Math.hypot(bx-ax, by-ay) || 1
    const nx = -(by-ay)/len, ny = (bx-ax)/len
    // A SINE IS ZERO AT BOTH ENDS AND ONE IN THE MIDDLE — EXACTLY THE TAPER WANTED.
    // WITH NO FULLNESS THIS IS A CONSTANT, WHICH IS AN EVEN-WIDTH LIP.
    const half = L*0.92 + L * fullness * Math.sin(t*Math.PI) * 0.42
    outer.push([x + nx*half, y + ny*half])
    inner.push([x - nx*half, y - ny*half])
  }

  paint.beginPath()
  paint.moveTo(outer[0][0], outer[0][1])
  for (const [x, y] of outer) paint.lineTo(x, y)
  for (let i = inner.length-1; i >= 0; i--) paint.lineTo(inner[i][0], inner[i][1])
  paint.closePath()
  paint.fill()
}

// HOW FAST THE RESTING SHAPE WALKS FROM THE STATE IT WAS IN TO THE ONE IT IS IN
// NOW. THE OLD FACE ONLY EVER MOVED AN EYELID BETWEEN STATES; A MOUTH MOVES ITS
// WHOLE WIDTH AND ITS OPENING, SO READING THE NEW NUMBERS RAW MAKES IT POP.
const EASE = 0.09

// A MOUTH IN BETWEEN TWO STATES. IT IS KEPT HERE RATHER THAN PASSED IN BECAUSE
// EVERY CANVAS DRAWS THE SAME MOOD AT THE SAME MOMENT, SO THEY SHARE ONE.
let holding = { ...SHAPES.loading }

// HOW MUCH OF EACH STATE IS SHOWING, 0 TO 1. THE PROPS THAT BELONG TO A STATE —
// THE TONGUE, THE DOTS, THE ARCS, THE DRAIN — ARE MULTIPLIED BY ITS WEIGHT, SO
// THEY FADE WITH IT INSTEAD OF BEING SWITCHED ON THE FRAME THE MOOD CHANGES.
const mixture = {}
for (const key of Object.keys(SHAPES)) mixture[key] = key === 'loading' ? 1 : 0

// WALKS THE RESTING SHAPE AND EVERY WEIGHT ONE STEP TOWARDS THE STATE NAMED. IT
// IS DRIVEN BY THE FRAME AND NOT BY THE DRAWING, SO TWO CANVASES SHOWING THE
// SAME MOOD CANNOT WALK IT TWICE AS FAST.
function towards(mood, whole){
  const want = SHAPES[mood] || SHAPES.idle
  const step = whole ? 1 : EASE

  for (const key of ['wide', 'curve', 'open', 'lip', 'tilt']){
    holding[key] += (want[key] - holding[key]) * step
  }

  for (const key of Object.keys(mixture)){
    mixture[key] += ((key === mood ? 1 : 0) - mixture[key]) * step
  }
}

// ARRIVE AT A STATE OUTRIGHT, FOR ANYTHING DRAWING A SINGLE FRAME RATHER THAN
// RUNNING THE LOOP — THE ICONS ARE RENDERED THAT WAY AND MUST NOT COME OUT
// HALFWAY BETWEEN TWO MOODS.
function posed(mood){
  towards(mood, true)
}

// DRAWS THE MASCOT. energy IS A 0..1 LOUDNESS WHILE LISTENING OR SPEAKING.
function mascot(paint, w, h, mood, clock, energy, _unused){
  let { wide, curve, open, lip, tilt } = holding
  let shiftX = 0, shiftY = 0
  let tongue = 0        // HOW FAR THE TONGUE RISES INTO THE OPENING.
  let dead = 0          // HOW FAR THE COLOUR HAS DRAINED OUT.
  let liftL = 0, liftR = 0

  // EACH STATE ADDS WHAT IT DOES, SCALED BY HOW MUCH OF IT IS SHOWING. A MOOD
  // THAT HAS JUST BEEN LEFT IS STILL PARTLY HERE, WHICH IS WHAT CARRIES THE
  // MOTION ACROSS THE CHANGE INSTEAD OF CUTTING IT.

  // COMING TO: THE SMILE IS SMALL AND KEEPS ALMOST ARRIVING.
  if (mixture.loading > 0.004){
    const wake = 0.5+0.5*Math.sin(clock*1.15)
    wide  += 0.05*wake*mixture.loading
    curve += 0.04*wake*mixture.loading
    dead  += (0.45 - 0.25*wake)*mixture.loading
  }

  // BREATHING, AND NOW AND THEN ONE CORNER GOES UP ON ITS OWN.
  if (mixture.idle > 0.004){
    const breath = Math.sin(clock*1.2)
    curve += 0.016*breath*mixture.idle
    wide  += 0.008*breath*mixture.idle
    liftR += 0.020*beat(clock, 7, 1.2)*mixture.idle
    liftL += 0.020*beat(clock, 7, 1.2, 3.5)*mixture.idle
  }

  // THE KEY IS DOWN. IT OPENS ON YOUR VOICE AND THE ARCS COME UP EITHER SIDE.
  if (mixture.listening > 0.004){
    open  += 0.10*energy*mixture.listening
    curve += 0.02*energy*mixture.listening
  }

  // THE WORDS ARE BEING MADE OUT: A PALE BAND SWEEPS ACROSS THE OPENING.
  if (mixture.hearing > 0.004){
    open += 0.012*Math.sin(clock*4)*mixture.hearing
  }

  // TILTED, PULLED TO ONE SIDE, WITH THE DOTS TICKING OVER ABOVE IT.
  // THE MOUTH IS NOT ROTATED: TIPPING THE WHOLE SMILE MAKES IT A BANANA.
  if (mixture.thinking > 0.004){
    shiftX += 0.010*w*Math.sin(clock*0.7)*mixture.thinking
    liftR  += (0.055 + 0.012*Math.sin(clock*0.9))*mixture.thinking
    liftL  -= 0.008*mixture.thinking
  }

  // A REAL MOUTH ON REAL SOUND, WITH THE TONGUE SHOWING IN THE OPENING.
  // IT NARROWS AS IT OPENS, THE WAY A MOUTH ROUNDS ON A VOWEL.
  if (mixture.speaking > 0.004){
    open   += 0.15*energy*mixture.speaking
    curve  -= 0.03*energy*mixture.speaking
    wide   -= 0.05*energy*mixture.speaking
    tongue += (0.55 + 0.45*energy)*mixture.speaking
  }

  // DRAINED, SLACK, AND KNOCKED SLIGHTLY OFF TRUE.
  if (mixture.gone > 0.004){
    dead  += mixture.gone
    curve -= 0.03*mixture.gone
  }

  dead = Math.min(1, dead)

  const W = w*wide, C = w*curve, O = w*open, L = w*lip
  // THE CORNER BALLS. THEY ARE SIZED OFF THE LIP THEY CAP RATHER THAN OFF THE
  // CANVAS: A FIXED RADIUS STAYED PUT WHILE THE LIP THINNED AND THICKENED PER
  // STATE, SO THE SAME BALL READ AS CORRECT ON ONE MOOD AND SWOLLEN ON THE NEXT.
  // 1.34 IS MEASURED AGAINST THE LIP AT THE CORNER — WHICH IS WHERE THE RIBBON
  // HAS TAPERED TO L*0.92, NOT AT ITS FULL MID-SPAN WIDTH.
  const D = L*1.34
  const lipTop = dead ? mix(SKIN.lip[0], SKIN.dead[0], dead) : rgb(SKIN.lip[0])
  const lipBot = dead ? mix(SKIN.lip[1], SKIN.dead[1], dead) : rgb(SKIN.lip[1])
  const rimCol = dead ? mix(SKIN.rim,    SKIN.dead[0], dead) : rgb(SKIN.rim)
  const deepCol= dead ? mix(SKIN.deep,   '#1a1b22',    dead) : rgb(SKIN.deep)

  paint.clearRect(0, 0, w, h)
  paint.save()
  paint.translate(w/2 + shiftX, h/2 + shiftY)
  paint.rotate(tilt)

  const lx = -W/2, ly = -w*liftL
  const rx =  W/2, ry = -w*liftR
  const mid = (ly+ry)/2 + C

  // THE PATH THE LIPS ENCLOSE. THE UPPER LIP IS ALMOST STRAIGHT ACROSS AND THE
  // LOWER ONE CARRIES THE SMILE, WHICH IS WHY IT STILL READS AS A SMILE WIDE OPEN.
  const upperY = mid - O*0.75
  const lowerY = mid + O*0.75
  const cavity = () => {
    paint.beginPath()
    paint.moveTo(lx, ly)
    paint.quadraticCurveTo(0, upperY, rx, ry)
    paint.quadraticCurveTo(0, lowerY + L*1.1, lx, ly)
    paint.closePath()
  }

  // THE HOLE THAT IS ACTUALLY VISIBLE ONCE THE LIP BAND HAS BEEN LAID ON TOP.
  // ANYTHING INSIDE THE MOUTH IS CLIPPED TO THIS, NOT TO cavity().
  const inside = () => {
    paint.beginPath()
    paint.moveTo(lx + D*0.5, ly)
    paint.quadraticCurveTo(0, upperY + L*1.1, rx - D*0.5, ry)
    paint.quadraticCurveTo(0, lowerY + L*0.2, lx + D*0.5, ly)
    paint.closePath()
  }

  // 1 — THE DARK INSIDE, SO THE MOUTH HAS DEPTH RATHER THAN BEING A FLAT SHAPE.
  paint.save()
  paint.shadowColor = tint(rgb(SKIN.lip[1]), dead ? 0 : 0.5)
  paint.shadowBlur = w*0.10
  cavity()
  paint.fillStyle = tint(deepCol, 1)
  paint.fill()
  paint.restore()

  // 4 — THE LIP BAND, DRAWN AS A RIBBON RATHER THAN A STROKE, SO THAT READY CAN
  //     BE FULLEST IN THE MIDDLE THE WAY A REAL LIP IS. EVERY OTHER STATE ASKS
  //     FOR NO SWELL AND COMES OUT ONE EVEN WIDTH.
  paint.save()
  const band = paint.createLinearGradient(0, -W*0.3, 0, W*0.3)
  band.addColorStop(0, tint(lipTop, 1))
  band.addColorStop(1, tint(lipBot, 1))
  paint.fillStyle = band
  // ONLY READY HAS FULL LIPS, AND THEY FILL OUT AS IT ARRIVES RATHER THAN
  // APPEARING THE FRAME THE MOOD CHANGES.
  const full = {
    upper: FULLNESS.upper * mixture.idle,
    lower: FULLNESS.lower * mixture.idle,
  }
  ribbon(paint, lx, ly, rx, ry, upperY, L, full.upper)
  ribbon(paint, lx, ly, rx, ry, lowerY + L*1.1, L, full.lower)
  paint.restore()

  // 5 — THE LIT TOP EDGE ALONG THE UPPER LIP, WHICH IS WHAT MAKES IT LOOK ROUND
  //     RATHER THAN CUT OUT OF PAPER.
  paint.save()
  paint.fillStyle = tint(rimCol, dead ? 0.30 : 0.62)
  ribbon(paint, lx, ly, rx, ry, upperY - L*0.30, L*0.30, full.upper*0.85)
  paint.restore()

  // 6 — WHAT IS INSIDE THE MOUTH, PAINTED AFTER THE LIPS AND CLIPPED TO THE HOLE
  //     THEY LEAVE, SO THE BAND CAN NEVER COVER IT.
  if (tongue > 0.02){
    paint.save()
    inside()
    paint.clip()
    const ty = lowerY - L*0.2
    const grad = paint.createLinearGradient(0, ty - O*0.8, 0, ty + O*0.6)
    grad.addColorStop(0, tint(rgb(SKIN.tongue[0]), 1))
    grad.addColorStop(1, tint(rgb(SKIN.tongue[1]), 1))
    paint.beginPath()
    paint.ellipse(0, ty, W*0.32, O*0.85*tongue, 0, 0, Math.PI*2)
    paint.fillStyle = grad
    paint.fill()
    paint.restore()
  }

  // TRANSCRIBING: A PALE BAND TRAVELLING THROUGH THE OPENING, LEFT TO RIGHT —
  // THE AUDIO BEING READ THROUGH, NOT A MOOD.
  if (mixture.hearing > 0.01){
    paint.save()
    inside()
    paint.clip()
    const at = ((clock*0.75) % 1)
    const x = -W*0.62 + at*W*1.24
    const band = paint.createLinearGradient(x - W*0.20, 0, x + W*0.20, 0)
    band.addColorStop(0,   tint(rgb(SKIN.rim), 0))
    band.addColorStop(0.5, tint([255,255,255], 0.95*mixture.hearing))
    band.addColorStop(1,   tint(rgb(SKIN.rim), 0))
    paint.fillStyle = band
    paint.fillRect(-W, -h, W*2, h*2)
    paint.restore()
  }

  // 7 — THE CORNERS. A BALL AT EACH END OF THE MOUTH, WHICH IS THE DIMPLE.
  for (const [x, y] of [[lx, ly], [rx, ry]]){
    // A SOFT HALO FIRST, SO THE BALL SEPARATES FROM THE LIP IT SITS ON.
    paint.save()
    paint.shadowColor = tint(lipBot, dead ? 0 : 0.85)
    paint.shadowBlur = D*0.8
    const ball = paint.createRadialGradient(x - D*0.34, y - D*0.42, D*0.06, x, y, D*1.15)
    ball.addColorStop(0, tint(toward(lipTop, [255,255,255], dead ? 0.15 : 0.55), 1))
    ball.addColorStop(0.55, tint(toward(lipTop, [255,255,255], dead ? 0.05 : 0.12), 1))
    ball.addColorStop(1, tint(lipBot, 1))
    paint.beginPath()
    paint.arc(x, y, D, 0, Math.PI*2)
    paint.fillStyle = ball
    paint.fill()
    paint.restore()

    // A SMALL SPECULAR ON TOP LEFT — WHAT ACTUALLY MAKES IT READ AS A SPHERE.
    paint.beginPath()
    paint.arc(x - D*0.33, y - D*0.38, D*0.26, 0, Math.PI*2)
    paint.fillStyle = tint([255,255,255], dead ? 0.08 : 0.38)
    paint.fill()
  }

  // ── WHAT IS GOING ON AROUND THE MOUTH ──

  // LISTENING AND SPEAKING BOTH CARRY SOUND, SO BOTH GET ARCS: COMING IN WHILE
  // IT LISTENS, GOING OUT WHILE IT TALKS.
  const sounding = Math.max(mixture.listening, mixture.speaking)

  if (sounding > 0.01){
    const strength = (0.45 + 0.55*energy) * sounding
    arcs(paint, -W*0.62, W*0.30, -1, rgb(SKIN.lip[0]), strength, clock, w)
    arcs(paint,  W*0.62, W*0.30,  1, rgb(SKIN.lip[0]), strength, clock, w)
  }

  // THINKING TICKS OVER ABOVE THE MOUTH, ONE DOT AT A TIME.
  if (mixture.thinking > 0.01){
    for (let i = 0; i < 3; i++){
      const on = 0.25 + 0.75*Math.max(0, Math.sin(clock*3.2 - i*0.7))
      paint.beginPath()
      paint.arc(W*0.34 + i*w*0.048, -W*0.42, w*0.017, 0, Math.PI*2)
      paint.fillStyle = tint(rgb(SKIN.rim), on*mixture.thinking)
      paint.fill()
    }
  }

  // STOPPED IS KNOCKED OUT COLD: TWO SPEED-LINES WHERE THE LIFE WENT.
  if (mixture.gone > 0.01){
    paint.save()
    paint.lineWidth = w*0.018
    paint.lineCap = 'round'
    paint.strokeStyle = tint(rgb(SKIN.dead[0]), 0.9*mixture.gone)
    for (let i = 0; i < 2; i++){
      const x = W*0.46 + i*w*0.052
      paint.beginPath()
      paint.moveTo(x, -W*0.52)
      paint.lineTo(x + w*0.030, -W*0.34)
      paint.stroke()
    }
    paint.restore()
  }

  paint.restore()
}
const Smile = (() => {
  let faces = []
  let mood = 'loading'
  let energy = 0
  let clock = 0
  let mic = 0
  let clip = null

  // ONLY THE TWO STATES THAT CARRY SOUND ANSWER TO A LOUDNESS. EVERY OTHER ONE
  // IS DRIVEN BY ITS OWN CLOCK, SO A STALE LEVEL CANNOT LEAK INTO IT.
  function wanted() {
    if (mood === 'listening') return Math.min(1, mic * MIC_GAIN)
    if (mood === 'speaking' && clip) return riding()

    return 0
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

  function frame() {
    clock += 0.016
    energy += (wanted() - energy) * SMOOTH

    // ONCE PER FRAME, NOT ONCE PER CANVAS: THE SHAPE MUST NOT WALK TWICE AS FAST
    // JUST BECAUSE THE HEADER IS SHOWING THE SAME MOUTH AS THE PANEL.
    towards(mood)

    for (const face of faces) {
      const paint = face.getContext('2d')

      // THE CANVAS IS SIZED IN DEVICE PIXELS AND DRAWN IN CSS ONES, SO THE MOUTH
      // IS NOT SOFT ON A RETINA SCREEN.
      const scale = devicePixelRatio || 1
      const wide = face.clientWidth || face.width
      const tall = face.clientHeight || face.height

      if (face.width !== Math.round(wide * scale) || face.height !== Math.round(tall * scale)) {
        face.width = Math.round(wide * scale)
        face.height = Math.round(tall * scale)
      }

      paint.setTransform(scale, 0, 0, scale, 0, 0)
      mascot(paint, wide, tall, mood, clock, energy)
    }

    requestAnimationFrame(frame)
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
