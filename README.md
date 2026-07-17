# Fix Pro Bridge 2.2

RepositÃ³rio oficial: <https://github.com/souzadevmg/fixpro-bridge>

### InstalaÃ§Ã£o online (Termux)

```bash
pkg update -y && pkg install -y curl git
curl -fsSL https://raw.githubusercontent.com/souzadevmg/fixpro-bridge/main/install-online.sh | bash
```

AtualizaÃ§Ã£o sem perder token ou logs:

```bash
cd ~/FixProBridge
./update.sh
./restart.sh
```

O repositÃ³rio contÃ©m apenas cÃ³digo. Nunca publique `config/config.json`: o token Ã© local e deve permanecer fora do Git.

Bridge Wake on LAN leve para Android, executado no Termux com Python, Flask e Waitress. Ele recebe comandos autenticados do Fix Pro Remote e envia o Magic Packet para a rede local do dispositivo Android. O Moto G52 foi o aparelho usado na validaÃ§Ã£o inicial, mas nÃ£o Ã© obrigatÃ³rio.

NÃ£o existe interface grÃ¡fica, APK, banco de dados, FastAPI, Pydantic, Uvicorn, Rust ou Maturin.

## Fluxo

```text
Fix Pro Remote (VPS)
        â”‚ HTTP sobre Tailscale + Bearer Token
        â–¼
Fix Pro Bridge 2.2 (Android / Termux)
        â”‚ Magic Packet UDP
        â–¼
Computador na rede local
```

O Agente Windows nÃ£o Ã© necessÃ¡rio para Wake on LAN.

## Requisitos

- celular ou tablet Android compatÃ­vel com Termux;
- Termux atualizado, instalado pelo F-Droid ou release oficial;
- Python 3.14.6 fornecido pelo Termux;
- Tailscale no dispositivo Android e na VPS;
- Wiâ€‘Fi conectado Ã  rede do computador que serÃ¡ ligado.

O instalador nÃ£o realiza downgrade, nÃ£o usa pyenv e rejeita versÃµes anteriores Ã  3.14.6 ou fora da sÃ©rie 3.14.

## InstalaÃ§Ã£o

### InstalaÃ§Ã£o por comando (recomendada)

Depois que o projeto estiver publicado no GitHub, no Termux serÃ¡ necessÃ¡rio apenas:

```bash
pkg update -y && pkg install -y curl
curl -fsSL https://raw.githubusercontent.com/souzadevmg/fixpro-bridge/main/install-online.sh | bash
```

O script clona ou atualiza o Bridge em `~/FixProBridge`, preserva o token e a configuraÃ§Ã£o
existente, instala as dependÃªncias e inicia o serviÃ§o. Para atualizar posteriormente:

```bash
cd ~/FixProBridge && ./update.sh
```

O endereÃ§o do repositÃ³rio pode ser substituÃ­do pela variÃ¡vel `FIXPRO_BRIDGE_REPO`.

Copie a pasta `FixProBridge` para o Termux e execute:

```bash
cd FixProBridge
chmod +x install.sh
./install.sh
./start.sh
```

O `install.sh`:

1. instala somente o pacote `python` do Termux;
2. confirma Python 3.14.6 ou uma revisÃ£o 3.14 mais recente;
3. cria `config/config.json` caso esteja ausente;
4. instala somente wheels universais com `--only-binary=:all:`;
5. desativa a resoluÃ§Ã£o automÃ¡tica com `--no-deps`;
6. gera um token criptograficamente seguro;
7. cria e protege o arquivo de log;
8. importa a aplicaÃ§Ã£o e verifica todos os endpoints.

Se algum pacote deixar de disponibilizar wheel universal, a instalaÃ§Ã£o Ã© interrompida. O pip nunca recebe autorizaÃ§Ã£o para compilar cÃ³digo-fonte.

## Por que o MarkupSafe estÃ¡ incorporado

Flask utiliza Jinja e Werkzeug, que importam MarkupSafe. O pacote publicado tenta construir uma aceleraÃ§Ã£o C quando nÃ£o encontra wheel compatÃ­vel com Android/Bionic.

O Bridge inclui em `app/_vendor/markupsafe` a implementaÃ§Ã£o Python oficial do MarkupSafe 3.0.3 e sua licenÃ§a BSD. Com isso, o Termux nÃ£o executa compilador, Maturin ou Rust. As demais dependÃªncias sÃ£o instaladas exclusivamente de wheels `py3-none-any` explicitamente fixadas.

## ConfiguraÃ§Ã£o

### Telemetria do Android (opcional)

Para exibir bateria, temperatura, SSID e intensidade do Wi-Fi, instale o
aplicativo **Termux:API** (pela mesma fonte do Termux) e, no Termux, execute:

```bash
pkg install termux-api
```

Sem esse pacote o Wake continua funcionando normalmente; apenas os campos de
telemetria que dependem do Android aparecem como "NÃ£o informado".

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

Na primeira instalaÃ§Ã£o, `GERAR_AUTOMATICAMENTE` Ã© substituÃ­do por um token aleatÃ³rio. O token Ã© exibido uma vez no terminal.

Para consultÃ¡-lo novamente:

```bash
python -c "import json; print(json.load(open('config/config.json'))['token'])"
```

| Campo | DescriÃ§Ã£o |
|---|---|
| `host` | Interface de escuta. Use `0.0.0.0` para Wiâ€‘Fi e Tailscale. |
| `port` | Porta do Waitress, de 1 a 65535. |
| `token` | Segredo Bearer com no mÃ­nimo oito caracteres. |
| `log` | Ativa o arquivo rotativo `logs/bridge.log`. |
| `timeout` | Timeout de canal do Waitress, entre 1 e 120 segundos. |

Depois de editar o arquivo, use `/api/reload` para recarregar o token. AlteraÃ§Ãµes em host, porta, logging ou timeout exigem `./restart.sh`.

## Iniciar, parar e reiniciar

```bash
./start.sh
./stop.sh
./restart.sh
```

O servidor Ã© iniciado em segundo plano com o equivalente a:

```bash
waitress-serve --host=0.0.0.0 --port=8080 --threads=2 app:app
```

SÃ£o utilizados apenas dois threads para reduzir RAM e consumo de CPU. O PID Ã© armazenado em `.bridge.pid`, permitindo que `stop.sh` encerre somente a instÃ¢ncia correta.

No Android, desative a otimizaÃ§Ã£o de bateria para Termux e Tailscale. `start.sh` solicita wake lock automaticamente quando o comando estiver disponÃ­vel.

## Tailscale e cadastro no painel

Consulte o IP `100.x.x.x` do dispositivo Android no aplicativo Tailscale. A VPS deve pertencer Ã  mesma tailnet.

No Fix Pro Remote, cadastre:

```text
URL: http://100.x.x.x:8080/api/wake
Token: token exibido pelo install.sh
```

O painel aceita HTTP somente para endereÃ§os privados, loopback, faixa Tailscale `100.64.0.0/10` ou nomes `.ts.net`. A criptografia do transporte Ã© fornecida pela rede Tailscale. EndereÃ§os pÃºblicos continuam exigindo HTTPS por meio de um proxy reverso.

NÃ£o abra a porta 8080 diretamente na internet.

## AutenticaÃ§Ã£o

Todos os endpoints, inclusive `/` e `/health`, exigem:

```http
Authorization: Bearer SEU_TOKEN
```

A comparaÃ§Ã£o utiliza `hmac.compare_digest()`. Chamadas sem header, com esquema incorreto ou token invÃ¡lido recebem HTTP 401 e sÃ£o registradas no log.

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

- corpo JSON e campos obrigatÃ³rios;
- tipos de todos os valores;
- formato do endereÃ§o MAC;
- broadcast IPv4;
- porta entre 1 e 65535;
- identificador positivo;
- hostname nÃ£o vazio com atÃ© 190 caracteres.

Dados invÃ¡lidos retornam HTTP 400. Sucesso:

```json
{
  "success": true,
  "message": "Wake enviado."
}
```

### `GET /api/info`

Retorna modelo e versÃ£o do Android, hostname, IP Wiâ€‘Fi, IP Tailscale, uptime, versÃ£o do Bridge, Python e PID.

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

Retorna no mÃ¡ximo as Ãºltimas 100 linhas:

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

O arquivo `logs/bridge.log` possui rotaÃ§Ã£o em 2 MB e mantÃ©m trÃªs histÃ³ricos. Registra:

- inicializaÃ§Ã£o e parada;
- Wake enviado ou com erro;
- tokens invÃ¡lidos;
- JSON invÃ¡lido;
- erros internos;
- IP do cliente, computador, hostname e data.

```bash
tail -f logs/bridge.log
```

## Testes rÃ¡pidos

```bash
TOKEN="$(python -c "import json; print(json.load(open('config/config.json'))['token'])")"

curl http://127.0.0.1:8080/ -H "Authorization: Bearer $TOKEN"
curl http://127.0.0.1:8080/health -H "Authorization: Bearer $TOKEN"
curl -X POST http://127.0.0.1:8080/api/test -H "Authorization: Bearer $TOKEN"
curl http://127.0.0.1:8080/api/info -H "Authorization: Bearer $TOKEN"
curl http://127.0.0.1:8080/api/logs -H "Authorization: Bearer $TOKEN"
```

Sem o header de autenticaÃ§Ã£o, todos devem responder HTTP 401.

## SoluÃ§Ã£o de problemas

### O painel mostra o Bridge offline

- confirme `./start.sh` e consulte `logs/bridge.log`;
- verifique se o dispositivo Android e a VPS estÃ£o na mesma tailnet;
- teste `/health` a partir da VPS usando o token;
- confira IP Tailscale, porta e token;
- confirme que o Android nÃ£o suspendeu Termux ou Tailscale.

### O Bridge responde, mas o computador nÃ£o liga

- habilite Wake on LAN na BIOS/UEFI e no driver de rede;
- confira MAC, broadcast e porta;
- confirme que o celular estÃ¡ no mesmo segmento da rede local;
- prefira Ethernet no computador alvo;
- desative isolamento de clientes do ponto de acesso, se necessÃ¡rio.

## DependÃªncias e compatibilidade

Todas as versÃµes estÃ£o fixadas em `requirements.txt`. O instalador usa apenas wheels universais e nunca executa setup de cÃ³digo-fonte. Flask 3.1.3 requer Python 3.9+, Waitress Ã© um servidor WSGI puramente Python, wakeonlan 4.0 suporta Python 3.10+ e requests 2.34.2 suporta Python 3.10+.

`requests` Ã© mantido por exigÃªncia da stack e para integraÃ§Ãµes futuras, mas nÃ£o Ã© importado durante o atendimento normal; isso reduz RAM e tempo de inicializaÃ§Ã£o.

## Estrutura

```text
FixProBridge/
â”œâ”€â”€ app/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ app.py
â”‚   â”œâ”€â”€ config.py
â”‚   â”œâ”€â”€ security.py
â”‚   â”œâ”€â”€ wake.py
â”‚   â”œâ”€â”€ utils.py
â”‚   â”œâ”€â”€ routes.py
â”‚   â””â”€â”€ _vendor/markupsafe/
â”œâ”€â”€ config/config.json
â”œâ”€â”€ logs/bridge.log
â”œâ”€â”€ install.sh
â”œâ”€â”€ start.sh
â”œâ”€â”€ stop.sh
â”œâ”€â”€ restart.sh
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ README.md
â”œâ”€â”€ .gitignore
â””â”€â”€ LICENSE
```


