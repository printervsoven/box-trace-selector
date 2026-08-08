# Cadabra2 verification notebook

This directory contains an independent Cadabra2/Jupyter starting point for the
Box trace calculation.

## Environment

The supported setup used here is:

- Windows 11 host
- WSL2 with Ubuntu 24.04
- Cadabra 2.5.14 official Ubuntu package
- Jupyter Notebook running inside WSL and opened from the Windows browser

The installation script pins both the official package URL and its SHA-256
checksum. Run it from Windows PowerShell with WSL root privileges:

```powershell
wsl.exe -d Ubuntu-24.04 -u root -- bash "/mnt/c/Users/artur/OneDrive/문서/추가 계싼/KL_codex_handoff/generated/direct_box2_verification/cadabra/install_cadabra_wsl.sh"
```

After installation, double-click `run_cadabra_jupyter.cmd`. Keep its terminal
open and open the tokenised `http://127.0.0.1:8888/...` URL that it prints.
Do not disable Jupyter's token authentication.

## Files

- `box2_verification.ipynb`: explanatory notebook using the Cadabra2 kernel.
- `verify_box2_smoke.cdb`: the same first-stage checks for command-line use.
- `install_cadabra_wsl.sh`: pinned Ubuntu installer.
- `run_cadabra_jupyter.cmd`: Windows launcher for the WSL Jupyter server.

Headless smoke test inside WSL:

```bash
cd /mnt/c/Users/artur/OneDrive/문서/추가\ 계싼/KL_codex_handoff/generated/direct_box2_verification/cadabra
cadabra2 verify_box2_smoke.cdb
```

## What is verified in this first stage

1. Antisymmetric-tensor canonicalisation.
2. A basic ordered Clifford multiplication identity.
3. Exact cancellation of all six n=2 representation moments for the proposed
   four-field combination.
4. Exact cancellation of the same moments for the original eight-field
   combination.
5. A perturbed-weight negative control which must remain nonzero.

These checks use exact rational arithmetic, not floating point arithmetic.

## Scope

This is an independent first-stage verification of the algebraic ingredients.
It does **not yet** independently rederive the 118 ordered `Box^2` blocks or all
404 canonical contracted terms. That full Cadabra encoding is the next phase;
until it exists, this notebook must not be described as a complete independent
recalculation of the full operator expansion.
