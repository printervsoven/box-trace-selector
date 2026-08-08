#!/usr/bin/env bash
set -euo pipefail

CADABRA_VERSION="2.5.14"
CADABRA_DEB="cadabra2-${CADABRA_VERSION}-ubuntu-24.04-noble-x86_64.deb"
CADABRA_URL="https://github.com/kpeeters/cadabra2/releases/download/${CADABRA_VERSION}/${CADABRA_DEB}"
CADABRA_SHA256="b9dc00c94eda9bff5d5e2f9793f6640c0c507d6ef2fc00401273e9b8659887ad"
DOWNLOAD_DIR="${HOME}/.cache/box-trace-cadabra"

if [[ "$(. /etc/os-release && printf '%s' "${VERSION_ID}")" != "24.04" ]]; then
  echo "This installer is pinned to Ubuntu 24.04." >&2
  exit 1
fi

mkdir -p "${DOWNLOAD_DIR}"
cd "${DOWNLOAD_DIR}"

sudo apt-get update
sudo apt-get install -y ca-certificates curl jupyter-notebook python3-ipykernel

curl --fail --location --output "${CADABRA_DEB}" "${CADABRA_URL}"
printf '%s  %s\n' "${CADABRA_SHA256}" "${CADABRA_DEB}" | sha256sum --check --strict
sudo apt-get install -y "./${CADABRA_DEB}"

echo
cadabra2 --version
python3 -c "import cadabra2, cadabra2_jupyter, ipykernel; print('Cadabra Jupyter imports: PASS')"
python3 - <<'PY'
from jupyter_client.kernelspec import KernelSpecManager

specs = KernelSpecManager().find_kernel_specs()
for name, path in sorted(specs.items()):
    print(f"{name}: {path}")
assert "cadabra2" in specs, "Cadabra2 Jupyter kernel was not registered"
print("Cadabra2 kernelspec: PASS")
PY

echo "Cadabra ${CADABRA_VERSION} and its Jupyter kernel are ready."
