// LAUNCH ELECTRON WITH AN ENVIRONMENT THAT HAS NOT BEEN GOT AT.
//
// A TERMINAL INSIDE AN ELECTRON APP, WHICH IS WHAT VS CODE IS, EXPORTS
// ELECTRON_RUN_AS_NODE=1 TO ITS CHILDREN. INHERIT THAT AND ELECTRON STARTS AS
// PLAIN NODE, WHERE THERE IS NO app AND NO WINDOW, ONLY A CONFUSING CRASH.

const { spawn } = require('node:child_process')
const electron = require('electron')

const clean = { ...process.env }

delete clean.ELECTRON_RUN_AS_NODE

spawn(electron, ['.', ...process.argv.slice(2)], { stdio: 'inherit', env: clean }).on(
  'exit',
  (code) => process.exit(code ?? 0),
)
