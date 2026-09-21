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
