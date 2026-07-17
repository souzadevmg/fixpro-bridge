# Fix Pro Bridge 2.5.0

Bridge oficial do **Fix Pro Remote** para Android/Termux.

Repositório: <https://github.com/souzadevmg/fixpro-bridge>

## Instalação online

```bash
pkg update -y && pkg install -y curl git iproute2 termux-api
curl -fsSL https://raw.githubusercontent.com/souzadevmg/fixpro-bridge/main/install-online.sh | bash
```

## Atualização

```bash
cd ~/FixProBridge
./update.sh
./restart.sh
```

O token e os logs locais são preservados. O arquivo `config/config.json` nunca deve ser enviado ao Git.

## Recursos

- Wake on LAN pela rede Wi-Fi local;
- API autenticada por Bearer Token;
- telemetria de bateria, energia, Wi-Fi, memória e armazenamento;
- detecção do IP Tailscale, inclusive na interface `tun0`;
- terminal remoto com saída transmitida por webhook;
- logs rotativos e diagnóstico integrado.

## Configuração

```json
{
  "host": "0.0.0.0",
  "port": 8080,
  "token": "SEU_TOKEN",
  "log": true,
  "timeout": 10,
  "allow_remote_terminal": true,
  "terminal_timeout": 120
}
```

Desative `allow_remote_terminal` se o aparelho não for administrado exclusivamente por você.

## Tailscale

O Tailscale continua recomendado. Cadastre no painel `http://IP_TAILSCALE:8080`, mantenha a porta 8080 fora da internet pública e coloque o Android e a VPS na mesma tailnet.

## Operação contínua

- instale Termux e Termux:API pela mesma origem;
- remova a otimização de bateria do Termux, Termux:API e Tailscale;
- mantenha o Wi-Fi conectado à rede dos computadores;
- use `./restart.sh` depois de atualizar.

Mantido por **souzadevmg** para o produto **Fix Pro Remote**.
