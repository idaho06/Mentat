# Local build secrets

This directory holds the local secret files used to build the Docker image
with BuildKit `--secret` mounts. Only this `README.md` is tracked by git —
everything else here is ignored (see `.gitignore`).

Create these two files locally before building:

- `secrets/password.txt` — the bot's IRC nick password
- `secrets/adminpassword.txt` — the admin command password

Each file should contain just the password value, with no trailing
newline requirements (trailing whitespace, if any, is not stripped).

See the "Building the Docker image" section in the project README for the
exact `docker build` / `docker compose build` commands, and for the
env-var-based alternative that avoids writing secrets to disk at all.
