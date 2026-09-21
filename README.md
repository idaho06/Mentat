# Mentat, an IRC bot
This is just a learning exercise. I want to create a bot that records the activity of a list of channels and can store messages like an answering machine. Also, throw dice, tell jokes and stuff like that.

## Tests

```
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
pytest                      # unit + integration, no network needed
pytest --cov=mentat         # same, with a coverage report
```

The integration tests run the bot against the `irc` library's bundled
in-process server on a random localhost port. That server does not implement
MODE, KICK or a PART reason, so those are covered by injecting the server
lines directly (`tests/integration/test_injected_events.py`) and by an
opt-in suite against a real ngircd:

```
docker compose -f docker-compose.test.yml up -d
MENTAT_TEST_IRC=127.0.0.1:6667 pytest -m real_server -v
docker compose -f docker-compose.test.yml down
```

Without `MENTAT_TEST_IRC` the `real_server` tests are skipped. Any other IRC
server without a password works too.

## Building the Docker image

The image build needs BuildKit (default on Docker ≥ 23; otherwise set
`DOCKER_BUILDKIT=1`). The bot's nick password and admin password are passed
in as BuildKit secrets, not `--build-arg` — build args are baked into image
layer metadata and are recoverable forever via `docker history`, secrets are
not.

**Local files** (default, convenient for local dev): create
`secrets/password.txt` and `secrets/adminpassword.txt` (see
`secrets/README.md`; both are gitignored, never commit real values here),
then:

```
docker build \
  --secret id=password,src=secrets/password.txt \
  --secret id=adminpassword,src=secrets/adminpassword.txt \
  -t mentat .
```

`docker compose build` uses the same files via the `secrets:` block in
`docker-compose.yml`.

**Environment variables** (nothing touches disk — preferred for CI):

```
MENTAT_PASSWORD=... MENTAT_ADMINPASSWORD=... docker build \
  --secret id=password,env=MENTAT_PASSWORD \
  --secret id=adminpassword,env=MENTAT_ADMINPASSWORD \
  -t mentat .
```

**Security note:** the resulting image still contains a `mentat.conf` file
with the password stored in plaintext (the bot's own config format, unrelated
to how the build secret was supplied). Anyone with the built image can
extract that file, so treat the image itself as sensitive — don't push it to
a public or shared registry.

## Running with Docker

`docker-compose.yml` bind-mounts a host directory into the container at
`/var/log/mentat`, defaulting to `/srv/almacen/mentat/logs`. Override it by
setting `MENTAT_LOGDIR`, either inline:

```
MENTAT_LOGDIR=/path/to/logs docker compose up -d
```

or by copying `.env.example` to `.env` and editing it there (`docker
compose` loads `.env` automatically).

With plain `docker run` (no compose), pass the mount directly instead:

```
docker run -v /path/to/logs:/var/log/mentat mentat
```
