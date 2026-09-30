# PS5 payloads: baixar e enviar

`ps5_payloads.py` baixa o release mais recente de cada payload e envia por FTP
para o PS5 (ftpsrv em `10.0.0.10:2121`).

| Chave             | Payload             | Origem                                                                 |
|-------------------|---------------------|------------------------------------------------------------------------|
| `pldmgr`          | PS5 Payload Manager | [itsPLK/ps5-payload-manager](https://github.com/itsPLK/ps5-payload-manager) |
| `etahen`          | etaHEN              | [etaHEN/etaHEN](https://github.com/etaHEN/etaHEN)                       |
| `elf-arsenal`     | Elf Arsenal         | [git.etawen.dev/soniciso/elf-arsenal](https://git.etawen.dev/soniciso/elf-arsenal) (espelho: [aloksaurabh/elf-arsenal](https://github.com/aloksaurabh/elf-arsenal)) |
| `game-compressor` | PS5 Game Compressor | [juma-sayeh/PS5-Game-Compressor](https://github.com/juma-sayeh/PS5-Game-Compressor) |
| `shadowmountplus` | ShadowMountPlus     | [drakmor/ShadowMountPlus](https://github.com/drakmor/ShadowMountPlus)   |
| `nanodns`         | nanoDNS             | [drakmor/nanoDNS](https://github.com/drakmor/nanoDNS)                   |
| `kstuff`          | kstuff-lite         | [EchoStretch/kstuff-lite](https://github.com/EchoStretch/kstuff-lite)   |

## Uso

Rode no computador que esta na mesma rede do PS5 (Python 3.8+, sem dependencias):

```sh
python3 ps5/ps5_payloads.py                        # baixa tudo e envia
python3 ps5/ps5_payloads.py --download-only        # apenas baixa para ps5/payloads
python3 ps5/ps5_payloads.py --only etahen kstuff   # apenas alguns
```

Por padrao os arquivos vao para `/data/pldmgr/payloads`, a pasta que o
PS5 Payload Manager usa; depois e so abrir `http://10.0.0.10:8084` e
carregar/marcar o autoload de cada um. Use `--dest` para outra pasta.

Se a API do GitHub limitar as requisicoes, exporte `GITHUB_TOKEN`.
