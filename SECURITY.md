# Security

## Reporting a vulnerability

Do not open a public issue. Use GitHub's private reporting on this repository —
**Security → Report a vulnerability** — or email <notvenupulagam@gmail.com>.

Say what the problem is, how to reproduce it, and what an attacker gets out of it. You will get
a first reply within a week. Please give a fix a reasonable chance to land before writing about
it publicly.

## What Happy actually has access to

This is worth being plain about, because the threat model is not the usual one. Happy runs on
your machine with your account's privileges, and it holds:

- **The shell.** `hands/shell/` runs commands. It is pattern-checked, not sandboxed.
- **The pointer and the keyboard.** `hands/desktop/pointer.py` injects real input.
- **The screen.** `eyes/` reads what is in front of you, including whatever else is open.
- **Your files**, through `hands/files/`.
- **Credentials for whatever you connected**, in `connection_secrets` in `data/happy.db`.
- **Your WhatsApp**, if you linked it, through a local bridge that can read and send.

Nothing is gated behind a confirmation — that is a deliberate design decision, argued in
HAPPY.md. It means a prompt injection that reaches the model reaches all of the above.

## Things that are known and accepted

Not bugs, and reports of them will be closed as such:

- **Credentials are on disk**, in `data/happy.db`, not in the system keychain. Deliberate; the
  keychain was removed. Protect it the way you protect your home directory.
- **The shell tool is checked, not sandboxed.** Genuine sandboxing is a real improvement and
  would be welcome as a change, not as a vulnerability report.
- **Linking WhatsApp through an unofficial client is against WhatsApp's terms.** That is a
  condition of the connection, said on the row before you press it.
- **The bridge listens on loopback** at port 3001, guarded by `INTERNAL_API_SECRET`. Anything
  already running as you on your machine can reach it.

## Things that are bugs, and wanted

- A model reachable by anything other than the person holding the key — a page, a file, a
  message — getting a tool called.
- Credentials read or written by something that is not the server that owns them.
- The bridge, or any loopback listener, reachable from off the machine.
- A token that survives signing out, or ends up in a log, a command line or `data/happy.log`.
- Anything in `hands/` or `mcps/` reaching outside the argument it was given.
