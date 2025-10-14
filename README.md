# Ring Buffer Preliminary Smoke Test

We're trying to see the kind of gains we can get by passing invariants to the compiler.

# Building and Running

```sh
docker build -t ring-buffer-smoketest . 
docker compose up -d
docker compose run --rm rust-app bash
```