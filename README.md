# Fix Pro Bridge 2.0

Repositório oficial: <https://github.com/souzadevmg/fixpro-bridge>

### Instalação online (Termux)

```bash
pkg update -y && pkg install -y curl git
curl -fsSL https://raw.githubusercontent.com/souzadevmg/fixpro-bridge/main/install-online.sh | bash
```

Atualização sem perder token ou logs:

```bash
cd ~/FixProBridge
./update.sh
./restart.sh
```

O repositório contém apenas código. Nunca publique `config/config.json`: o token é local e deve permanecer fora do Git.

Bridge Wake on LAN leve para Android, executado no Termux com Python, Flask e Waitress. Ele recebe comandos autenticados do Fix Pro Remote e envia o Magic Packet para a rede local do dispositivo Android. O Moto G52 foi o aparelho usado na validação inicial, mas não é obrigatório.

Não existe interface gráfica, APK, banco de dados, FastAPI, Pydantic, Uvicorn, Rust ou Maturin.

## Fluxo

```text
Fix Pro Remote (VPS)
        │ HTTP sobre Tailscale + Bearer Token
        ▼
Fix Pro Bridge 2.0 (Android / Termux)
        │ Magic Packet UDP
        ▼
Computador na rede local
```

O Agente Windows não é necessário para Wake on LAN.

## Requisitos

- celular ou tablet Android compatível com Termux;
- Termux atualizado, instalado pelo F-Droid ou release oficial;
- Python 3.14.6 fornecido pelo Termux;
- Tailscale no dispositivo Android e na VPS;
- Wi‑Fi conectado à rede do computador que será ligado.

O instalador não realiza downgrade, não usa pyenv e rejeita versões anteriores à 3.14.6 ou fora da série 3.14.

## Instalação

### Instalação por comando (recomendada)

Depois que o projeto estiver publicado no GitHub, no Termux será necessário apenas:

```bash
pkg update -y && pkg install -y curl
curl -fsSL https://raw.githubusercontent.com/souzadevmg/fixpro-bridge/main/install-online.sh | bash
```

O script clona ou atualiza o Bridge em `~/FixProBridge`, preserva o token e a configuração
existente, instala as dependências e inicia o serviço. Para atualizar posteriormente:

```bash
cd ~/FixProBridge && ./update.sh
```

O endereço do repositório pode ser substituído pela variável `FIXPRO_BRIDGE_REPO`.

Copie a pasta `FixProBridge` para o Termux e execute:

```bash
cd FixProBridge
chmod +x install.sh
./install.sh
./start.sh
```

O `install.sh`:

1. instala somente o pacote `python` do Termux;
2. confirma Python 3.14.6 ou uma revisão 3.14 mais recente;
3. cria `config/config.json` caso esteja ausente;
4. instala somente wheels universais com `--only-binary=:all:`;
5. desativa a resolução automática com `--no-deps`;
6. gera um token criptograficamente seguro;
7. cria e protege o arquivo de log;
8. importa a aplicação e verifica todos os endpoints.

Se algum pacote deixar de disponibilizar wheel universal, a instalação é interrompida. O pip nunca recebe autorização para compilar código-fonte.

## Por que o MarkupSafe está incorporado

Flask utiliza Jinja e Werkzeug, que importam MarkupSafe. O pacote publicado tenta construir uma aceleração C quando não encontra wheel compatível com Android/Bionic.

O Bridge inclui em `app/_vendor/markupsafe` a implementação Python oficial do MarkupSafe 3.0.3 e sua licença BSD. Com isso, o Termux não executa compilador, Maturin ou Rust. As demais dependências são instaladas exclusivamente de wheels `py3-none-any` explicitamente fixadas.

## Configuração

### Telemetria do Android (opcional)

Para exibir bateria, temperatura, SSID e intensidade do Wi-Fi, instale o
aplicativo **Termux:API** (pela mesma fonte do Termux) e, no Termux, execute:

```bash
pkg install termux-api
```

Sem esse pacote o Wake continua funcionando normalmente; apenas os campos de
telemetria que dependem do Android aparecem como "Não informado".

Arquivo `config/config.json`:

```json
{
  "host": "0.0.0.0",
  "port": 8080,
  "token": "GERAR_AUTOMATICAMENTE",
  "log": true,
  "timeout": 10
}
```

Na primeira instalação, `GERAR_AUTOMATICAMENTE` é substituído por um token aleatório. O token é exibido uma vez no terminal.

Para consultá-lo novamente:

```bash
python -c "import json; print(json.load(open('config/config.json'))['token'])"
```

| Campo | Descrição |
|---|---|
| `host` | Interface de escuta. Use `0.0.0.0` para Wi‑Fi e Tailscale. |
| `port` | Porta do Waitress, de 1 a 65535. |
| `token` | Segredo Bearer com no mínimo oito caracteres. |
| `log` | Ativa o arquivo rotativo `logs/bridge.log`. |
| `timeout` | Timeout de canal do Waitress, entre 1 e 120 segundos. |

Depois de editar o arquivo, use `/api/reload` para recarregar o token. Alterações em host, porta, logging ou timeout exigem `./restart.sh`.

## Iniciar, parar e reiniciar

```bash
./start.sh
./stop.sh
./restart.sh
```

O servidor é iniciado em segundo plano com o equivalente a:

```bash
waitress-serve --host=0.0.0.0 --port=8080 --threads=2 app:app
```

São utilizados apenas dois threads para reduzir RAM e consumo de CPU. O PID é armazenado em `.bridge.pid`, permitindo que `stop.sh` encerre somente a instância correta.

No Android, desative a otimização de bateria para Termux e Tailscale. `start.sh` solicita wake lock automaticamente quando o comando estiver disponível.

## Tailscale e cadastro no painel

Consulte o IP `100.x.x.x` do dispositivo Android no aplicativo Tailscale. A VPS deve pertencer à mesma tailnet.

No Fix Pro Remote, cadastre:

```text
URL: http://100.x.x.x:8080/api/wake
Token: token exibido pelo install.sh
```

O painel aceita HTTP somente para endereços privados, loopback, faixa Tailscale `100.64.0.0/10` ou nomes `.ts.net`. A criptografia do transporte é fornecida pela rede Tailscale. Endereços públicos continuam exigindo HTTPS por meio de um proxy reverso.

Não abra a porta 8080 diretamente na internet.

## Autenticação

Todos os endpoints, inclusive `/` e `/health`, exigem:

```http
Authorization: Bearer SEU_TOKEN
```

A comparação utiliza `hmac.compare_digest()`. Chamadas sem header, com esquema incorreto ou token inválido recebem HTTP 401 e são registradas no log.

## Endpoints

### `GET /`

```bash
curl http://100.x.x.x:8080/ -H "Authorization: Bearer TOKEN"
```

```json
{
  "service": "Fix Pro Bridge",
  "version": "2.0",
  "status": "online"
}
```

### `GET /health`

```bash
curl http://100.x.x.x:8080/health -H "Authorization: Bearer TOKEN"
```

```json
{
  "status": "ok",
  "uptime": "1 day, 2:03:04",
  "python": "3.14.6"
}
```

### `POST /api/wake`

```bash
curl -X POST http://100.x.x.x:8080/api/wake \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address":"00:06:E2:07:02:B3",
    "broadcast":"192.168.3.255",
    "port":9,
    "computer_id":1,
    "hostname":"Desktop"
  }'
```

O Bridge valida manualmente:

- corpo JSON e campos obrigatórios;
- tipos de todos os valores;
- formato do endereço MAC;
- broadcast IPv4;
- porta entre 1 e 65535;
- identificador positivo;
- hostname não vazio com até 190 caracteres.

Dados inválidos retornam HTTP 400. Sucesso:

```json
{
  "success": true,
  "message": "Wake enviado."
}
```

### `GET /api/info`

Retorna modelo e versão do Android, hostname, IP Wi‑Fi, IP Tailscale, uptime, versão do Bridge, Python e PID.

```bash
curl http://100.x.x.x:8080/api/info -H "Authorization: Bearer TOKEN"
```

### `POST /api/test`

```bash
curl -X POST http://100.x.x.x:8080/api/test \
  -H "Authorization: Bearer TOKEN"
```

Resposta: `{"success":true}`.

### `GET /api/logs`

Retorna no máximo as últimas 100 linhas:

```bash
curl http://100.x.x.x:8080/api/logs \
  -H "Authorization: Bearer TOKEN"
```

### `POST /api/reload`

Recarrega e valida `config/config.json` atomicamente:

```bash
curl -X POST http://100.x.x.x:8080/api/reload \
  -H "Authorization: Bearer TOKEN_ATUAL"
```

Se o token tiver sido alterado no arquivo, a chamada de reload ainda deve usar o token atualmente carregado.

## Logs

O arquivo `logs/bridge.log` possui rotação em 2 MB e mantém três históricos. Registra:

- inicialização e parada;
- Wake enviado ou com erro;
- tokens inválidos;
- JSON inválido;
- erros internos;
- IP do cliente, computador, hostname e data.

```bash
tail -f logs/bridge.log
```

## Testes rápidos

```bash
TOKEN="$(python -c "import json; print(json.load(open('config/config.json'))['token'])")"

curl http://127.0.0.1:8080/ -H "Authorization: Bearer $TOKEN"
curl http://127.0.0.1:8080/health -H "Authorization: Bearer $TOKEN"
curl -X POST http://127.0.0.1:8080/api/test -H "Authorization: Bearer $TOKEN"
curl http://127.0.0.1:8080/api/info -H "Authorization: Bearer $TOKEN"
curl http://127.0.0.1:8080/api/logs -H "Authorization: Bearer $TOKEN"
```

Sem o header de autenticação, todos devem responder HTTP 401.

## Solução de problemas

### O painel mostra o Bridge offline

- confirme `./start.sh` e consulte `logs/bridge.log`;
- verifique se o dispositivo Android e a VPS estão na mesma tailnet;
- teste `/health` a partir da VPS usando o token;
- confira IP Tailscale, porta e token;
- confirme que o Android não suspendeu Termux ou Tailscale.

### O Bridge responde, mas o computador não liga

- habilite Wake on LAN na BIOS/UEFI e no driver de rede;
- confira MAC, broadcast e porta;
- confirme que o celular está no mesmo segmento da rede local;
- prefira Ethernet no computador alvo;
- desative isolamento de clientes do ponto de acesso, se necessário.

## Dependências e compatibilidade

Todas as versões estão fixadas em `requirements.txt`. O instalador usa apenas wheels universais e nunca executa setup de código-fonte. Flask 3.1.3 requer Python 3.9+, Waitress é um servidor WSGI puramente Python, wakeonlan 4.0 suporta Python 3.10+ e requests 2.34.2 suporta Python 3.10+.

`requests` é mantido por exigência da stack e para integrações futuras, mas não é importado durante o atendimento normal; isso reduz RAM e tempo de inicialização.

## Estrutura

```text
FixProBridge/
├── app/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── security.py
│   ├── wake.py
│   ├── utils.py
│   ├── routes.py
│   └── _vendor/markupsafe/
├── config/config.json
├── logs/bridge.log
├── install.sh
├── start.sh
├── stop.sh
├── restart.sh
├── requirements.txt
├── README.md
├── .gitignore
└── LICENSE
```
