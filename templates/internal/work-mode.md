# Local work mode (this machine only — gitignored under /internal/)
#
# kb: read | write
#   read  — do not edit the public KB as a side effect of project work
#   write — may record repeatable platform facts into docs/ / recipes/ / data/
#   missing or any other value → read
# project: folder name under projects/ (not Integray companySlug)
#   empty — no project; KB-only unless the user names a folder
# Do not rewrite this file unless the user asks to switch.

kb: read
project:
