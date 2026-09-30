#!/usr/bin/env python3
"""Baixa as versoes mais recentes de payloads do PS5 e envia via FTP (ftpsrv).

Uso rapido (no computador que esta na mesma rede do PS5):

    python3 ps5_payloads.py                      # baixa tudo e envia para 10.0.0.10:2121
    python3 ps5_payloads.py --download-only      # so baixa para ./payloads
    python3 ps5_payloads.py --only etahen kstuff # apenas alguns payloads
    python3 ps5_payloads.py --host 10.0.0.10 --port 2121 --dest /data/pldmgr/payloads

Requer apenas Python 3.8+ (sem dependencias externas).
Defina GITHUB_TOKEN no ambiente se esbarrar no limite de requisicoes da API do GitHub.
"""

import argparse
import ftplib
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

USER_AGENT = "ps5-payloads-downloader"

# Cada payload: onde buscar o release e qual(is) arquivo(s) interessam.
# "pick" e uma regex aplicada ao nome do asset (ou ao nome dos arquivos dentro de um .zip).
PAYLOADS = {
    "pldmgr": {
        "name": "PS5 Payload Manager",
        "sources": [("github", "itsPLK/ps5-payload-manager")],
        "pick": r"^pldmgr\.elf$",
    },
    "etahen": {
        "name": "etaHEN",
        "sources": [("github", "etaHEN/etaHEN")],
        "pick": r"(?i)^etahen.*\.(bin|elf)$",
    },
    "elf-arsenal": {
        "name": "Elf Arsenal",
        # Repositorio oficial fica no Gitea do etawen; o GitHub e um espelho.
        "sources": [
            ("gitea", "https://git.etawen.dev", "soniciso/elf-arsenal"),
            ("github", "aloksaurabh/elf-arsenal"),
        ],
        "pick": r"(?i)^elf[-_]?arsenal.*\.elf$",
    },
    "game-compressor": {
        "name": "PS5 Game Compressor",
        "sources": [("github", "juma-sayeh/PS5-Game-Compressor")],
        "pick": r"(?i)\.elf$",
    },
    "shadowmountplus": {
        "name": "ShadowMountPlus",
        "sources": [("github", "drakmor/ShadowMountPlus")],
        "pick": r"(?i)^shadowmountplus.*\.elf$",
    },
    "nanodns": {
        "name": "nanoDNS",
        "sources": [("github", "drakmor/nanoDNS")],
        "pick": r"(?i)^nanodns.*\.elf$",
    },
    "kstuff": {
        "name": "kstuff-lite",
        "sources": [("github", "EchoStretch/kstuff-lite")],
        "pick": r"(?i)^kstuff.*\.elf$",
    },
}


def http_get(url, accept=None):
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def latest_release(source):
    """Retorna (tag, [(nome_asset, url_download), ...])."""
    if source[0] == "github":
        url = f"https://api.github.com/repos/{source[1]}/releases/latest"
        data = json.loads(http_get(url, "application/vnd.github+json"))
    else:
        _, base, repo = source
        data = json.loads(http_get(f"{base}/api/v1/repos/{repo}/releases/latest"))
    assets = [(a["name"], a["browser_download_url"]) for a in data.get("assets", [])]
    return data.get("tag_name", "?"), assets


def extract_from_zip(blob, pick):
    found = []
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        for info in zf.infolist():
            base = os.path.basename(info.filename)
            if base and not info.is_dir() and re.search(pick, base):
                found.append((base, zf.read(info)))
    return found


def fetch_payload(key, cfg, out_dir):
    """Baixa o payload e devolve lista de caminhos locais."""
    pick = cfg["pick"]
    last_err = None
    for source in cfg["sources"]:
        try:
            tag, assets = latest_release(source)
        except (urllib.error.URLError, ValueError, KeyError) as e:
            last_err = e
            print(f"  ! falha ao consultar {source[-1]}: {e}")
            continue

        files = []
        direct = [a for a in assets if re.search(pick, a[0])]
        if direct:
            for name, url in direct:
                print(f"  - {name} ({tag})")
                files.append((name, http_get(url)))
        else:
            # Sem asset direto: procura dentro de .zip anexados ao release.
            for name, url in assets:
                if name.lower().endswith(".zip"):
                    print(f"  - extraindo de {name} ({tag})")
                    files.extend(extract_from_zip(http_get(url), pick))

        if not files:
            names = ", ".join(a[0] for a in assets) or "nenhum"
            last_err = RuntimeError(f"nenhum asset casou com {pick!r} (assets: {names})")
            print(f"  ! {last_err}")
            continue

        paths = []
        dest = out_dir / key
        dest.mkdir(parents=True, exist_ok=True)
        for name, blob in files:
            p = dest / name
            p.write_bytes(blob)
            paths.append(p)
        (dest / "VERSION").write_text(f"{tag}\n{source[-1]}\n")
        return paths
    raise RuntimeError(f"{cfg['name']}: {last_err}")


def ftp_mkdirs(ftp, path):
    cur = ""
    for part in path.strip("/").split("/"):
        cur += "/" + part
        try:
            ftp.mkd(cur)
        except ftplib.error_perm:
            pass  # ja existe


def ftp_upload(host, port, user, password, dest, files):
    print(f"\nConectando em ftp://{host}:{port} ...")
    with ftplib.FTP() as ftp:
        ftp.connect(host, port, timeout=30)
        ftp.login(user, password)
        ftp.set_pasv(True)
        ftp_mkdirs(ftp, dest)
        for local in files:
            remote = f"{dest.rstrip('/')}/{local.name}"
            with open(local, "rb") as fh:
                ftp.storbinary(f"STOR {remote}", fh)
            print(f"  -> {remote} ({local.stat().st_size} bytes)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="10.0.0.10")
    ap.add_argument("--port", type=int, default=2121)
    ap.add_argument("--user", default="anonymous")
    ap.add_argument("--password", default="")
    ap.add_argument("--dest", default="/data/pldmgr/payloads",
                    help="pasta no PS5 (padrao: pasta de payloads do PS5 Payload Manager)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "payloads"),
                    help="pasta local de download (padrao: ps5/payloads)")
    ap.add_argument("--only", nargs="+", choices=sorted(PAYLOADS), help="baixar apenas estes")
    ap.add_argument("--download-only", action="store_true", help="nao enviar via FTP")
    args = ap.parse_args()

    out_dir = Path(args.out)
    keys = args.only or list(PAYLOADS)
    downloaded, failed = [], []
    for key in keys:
        cfg = PAYLOADS[key]
        print(f"[{cfg['name']}]")
        try:
            downloaded.extend(fetch_payload(key, cfg, out_dir))
        except Exception as e:  # segue com os demais
            print(f"  ! ERRO: {e}")
            failed.append(cfg["name"])

    if downloaded and not args.download_only:
        try:
            ftp_upload(args.host, args.port, args.user, args.password, args.dest, downloaded)
        except (OSError, ftplib.Error) as e:
            print(f"\nERRO no FTP: {e}")
            print("Confira se o PS5 esta ligado, com ftpsrv carregado, e na mesma rede.")
            return 1

    print(f"\n{len(downloaded)} arquivo(s) baixado(s) em {out_dir.resolve()}")
    if failed:
        print("Falharam: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
