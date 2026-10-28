# Guia de uso

## Construção do cliente

```python
import os
from hubsat_api import HubSatClient

api = HubSatClient(
    token=os.environ["HUBSAT_TOKEN"],
    base_url="https://api.hubsat.com.br/api/integracao",
    timeout=30,
)
```

`token` é obrigatório. `base_url` não pode conter usuário/senha, query ou fragmento. HTTP só é permitido em `localhost`, `127.0.0.1` ou `::1`. `timeout` deve ser positivo e finito. A aplicação cuida de obter/carregar o segredo. Não há login, refresh OAuth ou arquivo de configuração automático no SDK.

## Operações e parâmetros

```python
pagina = api.call("getAntenas", query={"limit": 20, "status": "ONLINE"})
detalhe = api.get_antenas_by_antena_id(path={"antenaId": pagina["data"][0]["id"]})
```

Confira a existência de itens antes de usar o primeiro. Os nomes em `path` são os nomes exatos das chaves entre `{}` no contrato. O método conveniente usa snake_case; `call()` usa o `operationId` do catálogo. Operações desconhecidas e segmentos vazios, `.` ou `..` são recusados localmente. Valores são escapados; não monte URLs concatenando identificadores.

`query` omite `None`, codifica booleanos como `true`/`false` e listas como texto separado por vírgulas. Use somente os filtros aceitos por aquela operação. `body` é serializado em JSON UTF-8. Não passe caminhos do painel à API de integração.

## Paginação por cursor

Exemplo para `GET /v1/antenas`, cuja resposta tem `data` e `meta.next_cursor`:

```python
cursor = None
while True:
    pagina = api.get_antenas(query={"limit": 100, "after": cursor})
    for antena in pagina["data"]:
        processar = antena["id"]  # Substitua pelo processamento do seu sistema.
        print(processar)
    proximo = pagina["meta"]["next_cursor"]
    if proximo is None:
        break
    if proximo == cursor:
        raise RuntimeError("Cursor não avançou; interrompido para evitar repetição.")
    cursor = proximo
```

Nesta listagem o limite padrão é 100, com faixa de 1 a 500. Outras operações podem ter parâmetros/limites diferentes. O cursor não é número da página. Filtros incrementais como `updated_since` só devem ser usados nas rotas que os documentam. Persistir o cursor e o processamento é responsabilidade do integrador.

## Cabeçalhos e leitura condicional

```python
resposta = api.call_with_response("getAntenas", query={"limit": 10})
etag = next((valor for nome, valor in resposta.headers.items() if nome.lower() == "etag"), None)
if etag:
    seguinte = api.call_with_response("getAntenas", query={"limit": 10}, if_none_match=etag)
    if seguinte.status == 304:
        print("Use a representação que você já guardou.")
```

Somente algumas operações oferecem ETag. Cabeçalhos são um mapeamento com a grafia recebida; não dependa de uma capitalização específica. Para diagnosticar limites, consulte `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` e `Retry-After` quando presentes.

## Escrita explícita

```python
import uuid

chave = str(uuid.uuid4())
# Persista chave e pedido antes de enviar.
pedido = {"nome": "Cliente de exemplo", "tipo": "PF"}
resultado = api.criar_assinante_cadastro(body=pedido, idempotency_key=chave)
```

Esse exemplo cria um cadastro: execute somente em uma conta de teste autorizada. Exige o escopo e as permissões definidos no OpenAPI. O SDK envia a chave, mas não mantém diário local, não deduplica intenções e não repete a chamada. Em timeout, confira o cadastro antes de decidir repetir. Não reaproveite uma chave com outro pedido.

Cobranças e operações de gestão têm regras próprias. `confirm`, envelope de escrita e necessidade de token do titular dependem da operação. Leia o contrato; não acrescente confirmação indiscriminadamente a corpos que não a aceitam. Este SDK não contorna permissões, licenças, desafios Starlink ou consentimento OAuth.

## Downloads

Exemplo de uma exportação financeira que já esteja pronta:

```python
from pathlib import Path

arquivo = api.call("baixarExportacaoFinanceira", path={"exportId": "ID_DA_EXPORTACAO_PRONTA"})
if not isinstance(arquivo, bytes):
    raise TypeError("A operação não retornou um arquivo binário.")
Path("exportacao.bin").write_bytes(arquivo)
```

Consulte primeiro o estado da exportação. Escolha a extensão pelo formato pedido e pelo Content-Type; PDF, CSV e XML são bytes e não devem ser tratados como JSON. Esta versão lê o arquivo inteiro em memória, sem streaming. Planeje a memória e os limites do seu processo.

## Falhas de rede, 429 e resultados incertos

`HubSatApiError` informa `status`, `code`, `request_id` e `retry_after`. Falhas de DNS/TLS/conexão continuam como exceções de `urllib.error`; timeouts também podem chegar como `TimeoutError`. Uma exceção não garante que uma escrita não foi executada.

Para leituras, a aplicação pode estabelecer orçamento limitado de tentativas respeitando o servidor. O SDK não implementa backoff. `Retry-After` pode ser segundos ou data HTTP; não trate todo valor como inteiro. Não repita automaticamente escritas nem use outra chave/tenant para contornar limites.

Uma resposta 403 de borda pode não ter o envelope de erro HubSat. Use o cliente oficial com seu User-Agent, confira o domínio e guarde o identificador de diagnóstico disponível; não desabilite certificados, WAF ou autenticação.

## Diagnóstico de compatibilidade

```python
from importlib.metadata import version
print(version("hubsat-api"))
contrato = api.get_openapi_json()
print(contrato["info"]["version"])
```

A operação pública de OpenAPI permite conferir o contrato servido; a chave ainda é exigida pelo construtor do SDK. Se o método não existir nesta distribuição, consulte o catálogo e a release compatível. Se o método existir, mas a API responder 404/403, confira a versão/rota/escopo antes de atribuir o erro à rede.

O pacote público 1.13.0 tem 82 operações da API 1.13.0. Ampliações locais ainda não publicadas no servidor não integram essa distribuição estável. A versão do SDK e o OpenAPI servido são registrados em `publication.json`.
