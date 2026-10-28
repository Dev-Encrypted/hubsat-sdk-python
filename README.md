# HubSat SDK para Python

Cliente Python oficial para a API de integração do HubSat. **Python 3.10+**, sem dependências de runtime. Esta distribuição **1.13.0** cobre as **82 operações da API 1.13.0 publicada** no momento da preparação.

- [Documentação da API](https://hubsat.com.br/desenvolvedores)
- [Download da versão estável](https://github.com/Dev-Encrypted/hubsat-sdk-python/releases/latest)
- [Wheel 1.13.0](https://github.com/Dev-Encrypted/hubsat-sdk-python/releases/download/v1.13.0/hubsat_api-1.13.0-py3-none-any.whl)
- [Guia completo de uso](docs/usage.md), [catálogo de operações](docs/operations.md) e [OpenAPI desta versão](docs/openapi.json)

## Instalação

Windows, Linux e macOS:

```sh
python -m pip install "https://github.com/Dev-Encrypted/hubsat-sdk-python/releases/download/v1.13.0/hubsat_api-1.13.0-py3-none-any.whl"
```

Alternativas: baixar o wheel pela página de releases e executar `python -m pip install caminho/do/arquivo.whl`, ou instalar diretamente do GitHub:

```sh
python -m pip install "git+https://github.com/Dev-Encrypted/hubsat-sdk-python.git@v1.13.0"
```

A instalação via Git exige Git instalado. O wheel não exige Git. A distribuição é fornecida por este repositório e suas releases; não pressupõe que o nome `hubsat-api` esteja publicado no PyPI. As releases incluem `SHA256SUMS` para conferir os arquivos.

## API_KEY e primeira leitura

No painel HubSat, abra **Integrações → API**, crie uma chave e selecione somente os escopos necessários. Para este exemplo, habilite `read:antenas`. A conta precisa ter acesso ao módulo e ao recurso. Uma chave não amplia a licença nem as permissões do titular. Guarde o segredo no seu ambiente, não no código, no GitHub ou em mensagens de suporte.

Defina `HUBSAT_TOKEN` no ambiente do processo ou no gerenciador de segredos da sua aplicação. O SDK não carrega arquivos `.env` automaticamente. Nunca use uma chave real em um frontend público.

```python
import os
from hubsat_api import HubSatClient

api = HubSatClient(os.environ["HUBSAT_TOKEN"], timeout=30)
pagina = api.get_antenas(query={"limit": 10})
for antena in pagina["data"]:
    print(antena["id"])
print("Próximo cursor:", pagina["meta"]["next_cursor"])
```

URL padrão: `https://api.hubsat.com.br/api/integracao`. A chave tem formato `hub_` seguido de 48 caracteres hexadecimais minúsculos. A validação local de formato não comprova que a chave está ativa.

## O que está disponível

O [catálogo](docs/operations.md) relaciona cada método Python, `operationId`, verbo e caminho. O [contrato OpenAPI](docs/openapi.json) contém os parâmetros, escopos (`x-required-scope`), corpos, respostas e erros.

Inclui as operações publicadas de antenas e Starlink, assinantes, MikroTik, financeiro, cobranças, aluguel, estoque, Guest Wi-Fi, webhooks, relatórios e Zabbix. A cobertura de um módulo é a do contrato publicado; isso não significa que toda função do painel exista nesta versão da API. Consulte o contrato servido pelo seu ambiente antes de integrar uma operação nova.

```python
# Método conveniente em snake_case:
resultado = api.get_antenas(query={"limit": 10})

# O mesmo pedido pelo operationId:
resultado = api.call("getAntenas", query={"limit": 10})
```

O SDK mantém o corpo da resposta original. Não converte recursos em modelos nem busca todas as páginas automaticamente.

## Erros e limites

```python
import urllib.error
from hubsat_api import HubSatApiError

try:
    pagina = api.get_antenas(query={"limit": 10})
except HubSatApiError as erro:
    # Registre metadados para diagnóstico; não registre a chave ou dados pessoais.
    print(erro.status, erro.code, erro.request_id, erro.retry_after)
except (urllib.error.URLError, TimeoutError):
    print("Falha de transporte; confira o estado antes de repetir uma escrita.")
```

`401`: confira validade/revogação da chave. `403`: confira escopo, módulo, permissão e tenant. `404`: confira rota/recurso e versão do servidor. `409`: trate conflito ou idempotência. `429`: respeite `Retry-After`; não aumente concorrência para contornar o limite. Respostas `5xx` e falhas de rede exigem tratamento pela aplicação.

O timeout padrão é 30 segundos. Não há repetição automática, inclusive em timeout. O timeout é aplicado às operações de rede do urllib; não representa um prazo global de toda uma tarefa composta.

## Escritas e idempotência

Use somente operações oferecidas pelo contrato, com escopo próprio e, quando exigido, token do titular, confirmação e `Idempotency-Key`. Persista a chave de idempotência antes do envio. Em resultado incerto, consulte o estado e reutilize a mesma chave com o mesmo pedido, conforme o contrato. Uma nova chave representa outra intenção.

O exemplo de escrita em [examples/create_subscriber.py](examples/create_subscriber.py) só executa quando chamado explicitamente. Nenhum exemplo faz cobranças ou envia comandos a roteadores automaticamente.

## Recursos de transporte

- `call_with_response()` devolve `HubSatResponse(status, headers, data)`.
- `if_none_match` envia `If-None-Match`; HTTP 304 retorna `data=None`.
- Downloads devolvem `bytes`; salve com `Path.write_bytes()`.
- `path` escapa segmentos; `query` codifica filtros, booleanos e listas.
- Redirecionamentos são recusados; não se encaminha a chave a outra origem.
- HTTPS é obrigatório. HTTP é aceito somente em loopback para desenvolvimento.
- Proxies do ambiente não são herdados. Esta versão não oferece configuração de proxy ou cliente assíncrono.
- O cliente se identifica como `HubSatSDK-Python/1`. Não desabilite TLS ou os controles da borda.

Veja [paginação, downloads, ETag, escrita e solução de problemas](docs/usage.md).

## SDK, MCP e versões

O SDK é para programas Python que usam API_KEY. Para conectar ChatGPT ou outro assistente, siga o [guia MCP remoto](https://hubsat.com.br/desenvolvedores#api-mcp), com a URL e o OAuth publicados. Instalar este pacote não conecta o assistente automaticamente.

Esta release acompanha a API **1.13.0**, verificada durante a preparação. Funcionalidades de versões futuras só entram em uma release compatível após publicação e testes. A API disponível no seu servidor é a referência; o pacote não habilita recursos ou módulos por conta própria. Este repositório contém somente o SDK e o contrato público, sem backend, frontend, credenciais ou dados de clientes.

## Desenvolvimento e suporte

```sh
python -m pip install .
python -m unittest discover -s tests -v
```

Os testes usam HTTP em loopback e dados sintéticos; não exigem conta HubSat nem fazem alterações em produção. A CI executa essa suíte em Python 3.10 a 3.14. Para suporte, abra uma [issue](https://github.com/Dev-Encrypted/hubsat-sdk-python/issues) com versão do pacote/Python/API, `request_id`, código HTTP e exemplo reduzido com dados fictícios. Nunca publique API_KEY, cookies, OTP, credenciais ou conteúdo privado de respostas.
