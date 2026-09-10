# Dashboard de Vendas — Cartão de Todos Alvorada

Mesma estrutura do dashboard das 6 unidades, configurado só para a unidade **Alvorada** (`config.json`).

- `index.html` — o dashboard (gerado automaticamente; não existe até a primeira rodada).
- `data/` — base linha a linha (`base_vendas.csv`), resumos e `relatorio/latest.json` (relatório pronto para o agente de WhatsApp).
- `config.json` — unidades, sub-franquia do CTN, data inicial, grupos do relatório e metas.
- `build.py`, `template.html`, `scripts/` — geração.

## Como colocar no ar

1. Criar o repositório público `dashboard-vendas-alvorada` e subir todo este conteúdo (inclusive a pasta `.github`).
2. Settings → Secrets and variables → Actions: criar `CTN_COOKIE` e `MINHACONTA_COOKIE` (os mesmos valores do repositório principal).
3. Actions → *Atualizar dashboard de vendas* → Run workflow. Na primeira rodada ele baixa o histórico desde `inicio` do `config.json` (01/01/2026) e cria `index.html` e `data/`.
4. Settings → Pages → Deploy from a branch → `main` / root → Save. Link: `https://matheussouza28.github.io/dashboard-vendas-alvorada/`.

Depois disso: atualização de hora em hora (07h–22h) e relatório em `data/relatorio/latest.json` às 08:10 (fechamento de ontem) e 10:10, 12:10, 15:10, 17:10, 19:10, 21:10 (parcial).
