// HAPPY HIMSELF, RUNNING AS A CHILD PROCESS. ONE JSON OBJECT PER LINE EACH WAY.

const { spawn } = require('node:child_process')
const { EventEmitter } = require('node:events')
const fs = require('node:fs')
const path = require('node:path')

const ROOT = path.resolve(__dirname, '..', '..', '..')

const ENTRY = 'main.py'
const SERVE = '--serve'

// WHERE A VIRTUAL ENVIRONMENT USUALLY SITS, IN THE ORDER WORTH LOOKING.
const PYTHONS = {
  win32: ['.venv\\Scripts\\python.exe', 'venv\\Scripts\\python.exe'],
  other: ['.venv/bin/python', 'venv/bin/python'],
}

function interpreter() {
  if (process.env.HAPPY_PYTHON) return process.env.HAPPY_PYTHON

  const windows = process.platform === 'win32'
  const guesses = windows ? PYTHONS.win32 : PYTHONS.other

  for (const guess of guesses) {
    const full = path.join(ROOT, guess)
    if (fs.existsSync(full)) return full
  }

  return windows ? 'python' : 'python3' // NOTHING LOCAL. HOPE FOR ONE ON THE PATH.
}

class Core extends EventEmitter {
  constructor() {
    super()
    this.child = null
    this.rest = ''
    this.leaving = false
  }

  get running() {
    return Boolean(this.child)
  }

  start() {
    if (this.child) return

    this.leaving = false
    this.rest = ''

    this.child = spawn(interpreter(), ['-u', ENTRY, SERVE], {
      cwd: ROOT,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    })

    this.child.stdout.setEncoding('utf-8')
    this.child.stdout.on('data', (lump) => this.absorb(lump))

    // NOTHING PARSES STDERR. IT IS WHERE THE LIBRARIES DO THEIR COMPLAINING.
    this.child.stderr.setEncoding('utf-8')
    this.child.stderr.on('data', (text) => process.stderr.write(text))

    this.child.on('error', (problem) => this.emit('gone', { reason: problem.message }))
    this.child.on('exit', (code) => {
      this.child = null
      if (!this.leaving) this.emit('gone', { reason: `Happy stopped (${code})` })
    })

    this.emit('starting')
  }

  absorb(lump) {
    const lines = (this.rest + lump).split('\n')
    this.rest = lines.pop() // WHATEVER CAME THROUGH HALF WRITTEN WAITS FOR THE REST.

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue

      try {
        this.emit('word', JSON.parse(trimmed))
      } catch {
        process.stderr.write(`unreadable: ${trimmed}\n`)
      }
    }
  }

  ask(order) {
    if (!this.child || !order) return
    this.child.stdin.write(`${JSON.stringify(order)}\n`)
  }

  stop() {
    if (!this.child) return

    this.leaving = true
    this.child.stdin.end() // HIS OWN READER SEES THE END AND SHUTS HIM DOWN TIDILY.

    const leaving = this.child
    setTimeout(() => leaving.kill('SIGKILL'), 2000).unref()

    this.child = null
  }

  restart() {
    this.stop()
    setTimeout(() => this.start(), 300)
  }
}

module.exports = { Core, ROOT }
