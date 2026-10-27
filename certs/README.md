# Extra CA certificates

These are public certificate-authority certificates, not secrets. Some official Indian sites send a leaf certificate without the intermediate, and some chains use ISRG Root YR, which older trust stores do not have yet.

`scripts/policypulse/http.py` loads every `*.pem` in this directory on top of the system trust store. Default verification still runs. Nothing here disables TLS checks.

| File | What it is |
| --- | --- |
| `isrg-root-yr.pem` | ISRG Root YR, cross-signed by ISRG Root X1 |
| `letsencrypt-yr1.pem` | Let's Encrypt intermediate YR1 (eGazette) |
| `letsencrypt-yr2.pem` | Let's Encrypt intermediate YR2 |
| `sectigo-ov-r36.pem` | Sectigo Public Server Authentication CA OV R36 (CBIC) |
