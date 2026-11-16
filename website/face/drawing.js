// ONE FRAME OF THE MOUTH. EACH LIP IS A BAND LAID ALONG A SMOOTH CURVE FROM CORNER TO CORNER,
// FULLEST IN THE MIDDLE; SHUT, THE TWO CURVES ARE ONE AND THE LIPS READ AS A SINGLE SMILE.

const STEPS = 36

// A CUBIC SAGS BY THREE QUARTERS OF ITS HANDLES, SO THE HANDLES ARE SET THAT MUCH FURTHER OUT.
function curve(left, right, sag) {
  const reach = (right[0] - left[0]) * 0.3
  const one = [left[0] + reach, left[1] + sag / 0.75]
  const two = [right[0] - reach, right[1] + sag / 0.75]

  return (t) => {
    const u = 1 - t
    const a = u * u * u, b = 3 * u * u * t, c = 3 * u * t * t, d = t * t * t

    return [a * left[0] + b * one[0] + c * two[0] + d * right[0], a * left[1] + b * one[1] + c * two[1] + d * right[1]]
  }
}

// THE OUTLINE OF A BAND ALONG A CURVE, half(t) EITHER SIDE OF offset(t), MEASURED ACROSS THE CURVE.
function band(paint, along, half, from = 0, to = 1, offset = () => 0) {
  const outer = []
  const inner = []

  for (let i = 0; i <= STEPS; i++) {
    const t = from + (to - from) * (i / STEPS)
    const [x, y] = along(t)
    const [ax, ay] = along(Math.max(0, t - 0.005))
    const [bx, by] = along(Math.min(1, t + 0.005))
    const length = Math.hypot(bx - ax, by - ay) || 1
    const nx = -(by - ay) / length
    const ny = (bx - ax) / length
    const h = half(t)
    const mid = offset(t)

    outer.push([x + nx * (mid - h), y + ny * (mid - h)])
    inner.push([x + nx * (mid + h), y + ny * (mid + h)])
  }

  paint.beginPath()
  paint.moveTo(...outer[0])
  for (const point of outer) paint.lineTo(...point)
  for (let i = inner.length - 1; i >= 0; i--) paint.lineTo(...inner[i])
  paint.closePath()
}

// THE SPACE BETWEEN THE LIPS.
function opening(paint, upper, lower) {
  paint.beginPath()
  paint.moveTo(...upper(0))
  for (let i = 1; i <= STEPS; i++) paint.lineTo(...upper(i / STEPS))
  for (let i = STEPS; i >= 0; i--) paint.lineTo(...lower(i / STEPS))
  paint.closePath()
}

// A CORNER: A LIT BALL CAPPING THE END OF THE LIPS, WHICH IS THE DIMPLE.
function corner(paint, x, y, radius, top, bottom, dead) {
  paint.save()
  paint.shadowColor = tint(bottom, dead ? 0 : 0.7)
  paint.shadowBlur = radius * 0.9

  const ball = paint.createRadialGradient(x - radius * 0.35, y - radius * 0.4, radius * 0.08, x, y, radius * 1.1)
  ball.addColorStop(0, tint(toward(top, [255, 255, 255], dead ? 0.15 : 0.5), 1))
  ball.addColorStop(0.6, tint(top, 1))
  ball.addColorStop(1, tint(bottom, 1))

  paint.beginPath()
  paint.arc(x, y, radius, 0, Math.PI * 2)
  paint.fillStyle = ball
  paint.fill()
  paint.restore()

  paint.beginPath()
  paint.arc(x - radius * 0.32, y - radius * 0.36, radius * 0.24, 0, Math.PI * 2)
  paint.fillStyle = tint([255, 255, 255], dead ? 0.08 : 0.45)
  paint.fill()
}

// THREE NESTED BRACKETS BESIDE A CORNER, OPENING AWAY FROM THE MOUTH.
function arcs(paint, x, y, sign, size, colour, strength) {
  const facing = sign > 0 ? 0 : Math.PI

  for (let i = 0; i < 3; i++) {
    const fade = Math.max(0, strength - i * 0.22)

    if (fade <= 0.01) continue

    paint.beginPath()
    paint.lineWidth = size * 0.14
    paint.lineCap = 'round'
    paint.strokeStyle = tint(colour, fade * 0.9)
    paint.arc(x, y, size * (0.35 + i * 0.3), facing - 0.62, facing + 0.62)
    paint.stroke()
  }
}

function dots(paint, x, y, size, colour, weight, clock) {
  for (let i = 0; i < 3; i++) {
    const on = 0.25 + 0.75 * Math.max(0, Math.sin(clock * 3.2 - i * 0.7))

    paint.beginPath()
    paint.arc(x + i * size * 0.048, y, size * 0.017, 0, Math.PI * 2)
    paint.fillStyle = tint(colour, on * weight)
    paint.fill()
  }
}
