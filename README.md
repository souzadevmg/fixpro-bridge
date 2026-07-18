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

## Terminal remoto e webhook

O painel envia `POST /api/terminal/run` com um comando, uma `callback_url` HTTPS
e um `callback_token` descartável. O Bridge responde `202` imediatamente e
executa o comando em segundo plano. Cada bloco de saída é devolvido ao painel:

```json
{
  "event": "chunk",
  "channel": "stdout",
  "content": "saída da linha\n"
}
```

Ao terminar, o Bridge envia:

```json
{
  "event": "finish",
  "exit_code": 0,
  "message": "Comando concluído."
}
```

Os callbacks usam `Authorization: Bearer TOKEN_DA_SESSÃO` e o token expira
junto com a sessão. O painel atualiza a tela continuamente por 500 ms, sem
depender de buffering do Nginx.

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

## Componentes Android obrigatórios

- **Termux**: ambiente que executa o Bridge;
- **Termux:API**: fornece bateria, energia, Wi-Fi e outros dados do aparelho;
- **Termux:Boot**: inicia o Bridge automaticamente depois de reiniciar o Android;
- **Tailscale**: cria o caminho privado entre a VPS e a rede local.

Instale Termux, Termux:API e Termux:Boot pela mesma origem (F-Droid ou GitHub).
Depois de instalar o Termux:Boot, abra o aplicativo uma vez. O script em
`~/.termux/boot/fixpro-bridge.sh` será executado automaticamente nos próximos
boots. A documentação oficial do Termux:Boot exige essa primeira abertura e
scripts executáveis nessa pasta.

Crie o inicializador automático:

```bash
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/fixpro-bridge.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
sleep 15
cd "$HOME/FixProBridge"
bash start.sh >> logs/boot.log 2>&1
EOF
chmod +x ~/.termux/boot/fixpro-bridge.sh
```

No Android, deixe Termux, Termux:API, Termux:Boot e Tailscale com bateria
**Sem restrições** e permita execução em segundo plano.

## Tailscale e VPN sempre ativa

Abra o Tailscale, autorize o dispositivo e ative a VPN. No Android, habilite:

`Configurações → Rede/VPN → Tailscale → VPN sempre ativa`

Cadastre no painel `http://IP_TAILSCALE:8080`, mantenha a porta 8080 fora da
internet pública e coloque o Android e a VPS na mesma tailnet. O Tailscale é
independente do Termux:Boot: ambos precisam estar habilitados para o Bridge
voltar online após um reboot.

Se o campo IP Tailscale ficar vazio, diagnostique pelo Termux:

```bash
ip -4 addr show tun0
python -c "from app.utils import tailscale_ip; print(tailscale_ip())"
```

Algumas versões do Android bloqueiam a consulta netlink usada por `ip`; o
Bridge tenta automaticamente o fallback `ifconfig` nesses aparelhos.

## Operação contínua

- mantenha o Wi-Fi conectado à rede dos computadores;
- confirme que o Tailscale voltou conectado após reiniciar;
- use `bash ./restart.sh` depois de atualizar, caso os scripts percam a
  permissão de execução;
- consulte `logs/boot.log` quando o Bridge não iniciar no boot.

Mantido por **souzadevmg** para o produto **Fix Pro Remote**.
