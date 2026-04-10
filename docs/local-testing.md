# Local Testing Guide

Projeto: `/home/tarun/.openclaw/workspace/projects/chorus`

## Objetivo

Este guia cobre o fluxo minimo para testar o Chorus localmente:

- subir a API e a UI web
- configurar o provider LLM via variaveis de ambiente
- executar uma run manual no navegador
- verificar erros comuns sem perder tempo

## 1. Preparacao

No terminal:

```bash
cd /home/tarun/.openclaw/workspace/projects/chorus
source venv/bin/activate
```

Se precisar instalar dependencias de desenvolvimento:

```bash
./venv/bin/pip install -e ".[dev]"
```

## 2. Configurar o provider

O caminho preferido hoje e Anthropic.

Use uma chave real. Nao use placeholders como `...`.

```bash
export ANTHROPIC_API_KEY="SUA_CHAVE_REAL"

export CHORUS_MODEL_EXTRACTION=anthropic/claude-sonnet-4-6
export CHORUS_MODEL_SYNTHESIS=anthropic/claude-sonnet-4-6
export CHORUS_MODEL_CRITIC=anthropic/claude-sonnet-4-6

export CHORUS_MODEL_EXTRACTION_FALLBACKS=
export CHORUS_MODEL_SYNTHESIS_FALLBACKS=
export CHORUS_MODEL_CRITIC_FALLBACKS=

export CHORUS_LLM_TIMEOUT_SECONDS=180
```

Verifique se os nomes dos modelos ficaram corretos e sem quebra de linha:

```bash
printf '<%s>\n' "$CHORUS_MODEL_EXTRACTION"
printf '<%s>\n' "$CHORUS_MODEL_SYNTHESIS"
printf '<%s>\n' "$CHORUS_MODEL_CRITIC"
```

Saida esperada:

```text
<anthropic/claude-sonnet-4-6>
<anthropic/claude-sonnet-4-6>
<anthropic/claude-sonnet-4-6>
```

## 3. Subir a aplicacao

Escolha uma porta livre. Exemplo:

```bash
./venv/bin/python -m uvicorn web.app:app --host 127.0.0.1 --port 8011
```

Abra no navegador:

```text
http://127.0.0.1:8011
```

## 4. Teste manual pela UI

No formulario:

- escreva uma ideia crua
- selecione `idea_spec` para parar no Project Spec
- selecione `full` para gerar tambem o Implementation Spec

Exemplo de ideia:

```text
A tool that organizes receipts and exports CSV.
```

Resultado esperado:

- `POST /api/runs` responde `200`
- a UI muda para estado `running`
- a aba `Project Spec` recebe conteudo quando a run completa
- em `full`, a aba `Implementation Spec` tambem aparece

## 5. Autenticacao da API (opcional)

Por padrao, a API nao exige autenticacao — util em desenvolvimento local.

Para habilitar autenticacao, exporte `CHORUS_API_KEY` antes de subir o servidor:

```bash
export CHORUS_API_KEY="sua-chave-aqui"
```

Com a chave configurada, todos os requests a `POST /api/runs` precisam do header:

```
Authorization: Bearer sua-chave-aqui
```

Sem a variavel definida, a autenticacao e ignorada silenciosamente.

## 6. Teste rapido via API

Criar uma run (sem auth):

```bash
curl -X POST http://127.0.0.1:8011/api/runs \
  -H "Content-Type: application/json" \
  -d '{"mode":"idea_spec","idea":"A tool that organizes receipts and exports CSV"}'
```

Criar uma run (com auth habilitada):

```bash
curl -X POST http://127.0.0.1:8011/api/runs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sua-chave-aqui" \
  -d '{"mode":"idea_spec","idea":"A tool that organizes receipts and exports CSV"}'
```

Consultar uma run:

```bash
curl http://127.0.0.1:8011/api/runs/1
```

Baixar artefatos:

```bash
curl -OJ http://127.0.0.1:8011/api/runs/1/download/output.json
curl -OJ http://127.0.0.1:8011/api/runs/1/download/project-spec.md
curl -OJ http://127.0.0.1:8011/api/runs/1/download/implementation-spec.md
```

## 7. Validacao local de codigo

Rodar lint:

```bash
./venv/bin/ruff check .
```

Rodar a suite principal:

```bash
./venv/bin/pytest tests/test_cli.py tests/test_runner.py tests/test_web.py -q
```

Rodar tudo:

```bash
./venv/bin/pytest -q
```

## 8. Problemas comuns

### `invalid x-api-key`

Causa:

- `ANTHROPIC_API_KEY` existe, mas o valor e invalido

Correcao:

- gere uma chave nova
- exporte a chave correta no mesmo terminal do servidor
- reinicie o `uvicorn`

### `Missing Anthropic API Key`

Causa:

- a variavel `ANTHROPIC_API_KEY` nao foi definida no terminal onde o servidor foi iniciado

Correcao:

- exporte a chave antes de subir a app

### `not_found_error` ou modelo quebrado em varias linhas

Causa:

- o nome do modelo foi exportado com quebra de linha ou espacos extras

Correcao:

- refaca os `export CHORUS_MODEL_*` em uma unica linha
- valide com `printf`

### `address already in use`

Causa:

- a porta ja esta ocupada por outra instancia do `uvicorn`

Correcao:

- suba em outra porta, por exemplo `8011`, `8012`, `8013`
- ou mate a instancia antiga

Exemplo:

```bash
pkill -f "uvicorn web.app:app"
```

### `Caught handled exception, but response already started`

Causa:

- a run falhou dentro de `BackgroundTask` depois que o endpoint ja respondeu

Impacto:

- o erro principal continua sendo o do provider ou do pipeline
- esse traceback e secundario e hoje polui o log

## 9. Higiene de segredo

- nunca commite chaves em arquivos do repo
- nunca deixe credenciais reais em handoffs ou docs
- se uma chave apareceu no terminal compartilhado ou em conversa, revogue e gere outra

## 10. Arquivos uteis

- `README.md`
- `docs/handoff-2026-04-10.md`
- `web/app.py`
- `llm/routing.py`
- `core/runner.py`
