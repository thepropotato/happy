// HAPPY IS A MOUTH: AN UPPER AND A LOWER LIP MEETING AT TWO BALL CORNERS. HE WEARS ONE
// PALETTE IN EVERY STATE; THE MOOD IS HOW WIDE IT OPENS AND WHAT GOES ON AROUND IT.

const SKIN = {
  lip: ['#8fb58a', '#55804f'],
  rim: '#cfe3c9', // THE LIT TOP EDGE.
  deep: '#14201a', // INSIDE THE MOUTH.
  tongue: ['#e58a8a', '#b85d5d'],
  dead: ['#3a3c3a', '#2c2e2c'], // WHAT IT ALL FADES TO WHEN NOTHING IS RUNNING.
}

// AS FRACTIONS OF THE DRAWING'S WIDTH.
//   wide  CORNER TO CORNER       curve  HOW FAR THE SMILE SAGS AT ITS MIDDLE
//   open  HOW FAR THE LIPS PART  lip    THE LIP'S THICKNESS AT ITS FULLEST
const SHAPES = {
  loading: { wide: 0.34, curve: 0.1, open: 0.0, lip: 0.026 },
  idle: { wide: 0.48, curve: 0.13, open: 0.0, lip: 0.036 },
  listening: { wide: 0.44, curve: 0.1, open: 0.075, lip: 0.03 },
  hearing: { wide: 0.44, curve: 0.1, open: 0.06, lip: 0.03 },
  thinking: { wide: 0.38, curve: 0.08, open: 0.0, lip: 0.032 },
  speaking: { wide: 0.44, curve: 0.09, open: 0.085, lip: 0.03 },
  gone: { wide: 0.38, curve: 0.05, open: 0.0, lip: 0.03 },

  // WORN FOR A MOMENT WHEN A TURN ENDS.
  pleased: { wide: 0.52, curve: 0.16, open: 0.03, lip: 0.036 },
  sorry: { wide: 0.36, curve: -0.04, open: 0.0, lip: 0.032 },
}

function tint(c, a) {
  return `rgba(${c[0] | 0}, ${c[1] | 0}, ${c[2] | 0}, ${a})`
}

function mix(a, b, t) {
  return toward(rgb(a), rgb(b), t)
}

// ONE PULSE EVERY every SECONDS, LASTING forHowLong, FOR THINGS DONE ONCE IN A WHILE.
function beat(clock, every, forHowLong, offset) {
  const t = ((clock + (offset || 0)) % every) / forHowLong

  return t > 1 ? 0 : Math.sin(t * Math.PI)
}

// HOW FAST THE RESTING SHAPE WALKS FROM ONE STATE TO THE NEXT, SO A CHANGE IS A MOVE NOT A POP.
const EASE = 0.09

// ONE SHAPE SHARED BY EVERY CANVAS, BECAUSE THEY ALL SHOW THE SAME MOOD AT THE SAME MOMENT.
let holding = { ...SHAPES.loading }

// HOW MUCH OF EACH STATE IS SHOWING, SO WHAT BELONGS TO A STATE FADES WITH IT.
const mixture = {}
for (const key of Object.keys(SHAPES)) mixture[key] = key === 'loading' ? 1 : 0

function towards(mood, whole) {
  const want = SHAPES[mood] || SHAPES.idle
  const step = whole === true ? 1 : whole || EASE

  for (const key of ['wide', 'curve', 'open', 'lip']) holding[key] += (want[key] - holding[key]) * step
  for (const key of Object.keys(mixture)) mixture[key] += ((key === mood ? 1 : 0) - mixture[key]) * step
}

// ARRIVE OUTRIGHT, FOR A SINGLE FRAME SUCH AS AN ICON.
function posed(mood) {
  towards(mood, true)
}
