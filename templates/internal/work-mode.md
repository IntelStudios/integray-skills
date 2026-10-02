# Local work mode (this machine only — gitignored under /internal/)
#
# kb: read | read-write
#   read        — read the public KB; do not edit it as a side effect of project work
#   read-write  — same, plus may record repeatable platform facts into docs/ / recipes/ / data/
#   there is no write-only mode; write always includes read
#   missing or any other value → read; legacy `write` → read-write
# project: folder name under projects/ (not Integray companySlug)
#   empty — no project; KB-only unless the user names a folder
# publish: never | ask | always
#   never   — after finishing working/ edits, do not /publish and do not ask
#   ask     — after finishing working/ edits, ask whether to /publish
#   always  — after finishing working/ edits, /publish immediately
#   missing, empty, or any other value → ask the user (explain never/ask/always), then write their choice
#   explicit /publish from the user always runs
# Do not rewrite this file unless the user asks to switch.

kb: read
project:
publish:
