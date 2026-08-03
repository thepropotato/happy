// VS CODE'S TERMINAL EXPORTS ELECTRON_RUN_AS_NODE=1. INHERIT IT AND ELECTRON
// STARTS AS PLAIN NODE, WITH NO app AND NO WINDOW, ONLY A CONFUSING CRASH.

const { spawn } = require('node:child_process')
const electron = require('electron')

const clean = { ...process.env }

delete clean.ELECTRON_RUN_AS_NODE

spawn(electron, ['.', ...process.argv.slice(2)], { stdio: 'inherit', env: clean }).on(
  'exit',
  (code) => process.exit(code ?? 0),
)
