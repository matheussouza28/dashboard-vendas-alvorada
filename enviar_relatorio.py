#!/usr/bin/env python3
"""Gera as imagens do Relatório do dia (5 unidades e Osasco) + resumo em texto e envia ao webhook do n8n,
que publica no grupo do WhatsApp.

Uso: python3 scripts/enviar_relatorio.py fechamento   -> dia anterior (fechado)
     python3 scripts/enviar_relatorio.py dia          -> dia atual (parcial)
Env: N8N_WEBHOOK_URL (obrigatório para enviar; sem ele só gera os arquivos em out/).
Metas: META_SEMANA (padrão 1000) e META_OSASCO (padrão 250).
"""
import sys, os, io, csv, json, base64, datetime as dt, urllib.request
from playwright.sync_api import sync_playwright

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
modo = sys.argv[1] if len(sys.argv) > 1 else 'dia'
cfgp = os.path.join(root, 'config.json')
CFG = json.load(open(cfgp, encoding='utf-8')) if os.path.exists(cfgp) else {}
GRUPOS = CFG.get('grupos_relatorio') or [
    {'nome': '5 unidades', 'titulo': 'Relatório de Vendas', 'unidades': ['BELEM CENTRO', 'MANAUS CENTRO', 'MANAUS NORTE', 'PARINTINS', 'PORTO ALEGRE NORTE'], 'meta_semana': int(os.environ.get('META_SEMANA', '1000')), 'arquivo': 'relatorio_5_unidades.png'},
    {'nome': 'Osasco', 'titulo': 'Relatório de Vendas Osasco', 'unidades': ['OSASCO'], 'meta_semana': int(os.environ.get('META_OSASCO', '250')), 'arquivo': 'relatorio_osasco.png'},
]
REPO = CFG.get('repo', 'matheussouza28/dashboard-vendas-cdt')

now_br = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)
d = now_br.date() - dt.timedelta(days=1) if modo == 'fechamento' else now_br.date()
day = d.isoformat()
out = os.path.join(root, 'out'); os.makedirs(out, exist_ok=True)

meta = json.load(open(os.path.join(root, 'data', 'meta.json'), encoding='utf-8'))
rows = list(csv.DictReader(open(os.path.join(root, 'data', 'resumo_diario.csv'), encoding='utf-8')))
ws = d - dt.timedelta(days=(d.weekday() - 2) % 7)  # semana começa na quarta
br = lambda x: x.strftime('%d/%m/%Y')
hora = now_br.strftime('%H:%M')

def block(units, meta_sem, titulo):
    per = {u: 0 for u in units}
    for r in rows:
        if r['Dia'] == day and r['Franquia'] in units:
            per[r['Franquia']] += int(r['vendas'])
    tot = sum(per.values())
    week = sum(int(r['vendas']) for r in rows if ws.isoformat() <= r['Dia'] <= day and r['Franquia'] in units)
    rank = sorted(per.items(), key=lambda x: -x[1])
    medals = ['🥇', '🥈', '🥉']
    cab = ('*%s — %s (fechamento)*' if modo == 'fechamento' else '*%s — %s (parcial até ' + hora + ')*') % (titulo, br(d))
    lines = [cab, 'Meta da semana: %s vendas' % f'{meta_sem:,}'.replace(',', '.'), '']
    for i, (u, v) in enumerate(rank):
        lines.append('%s %s: *%d*' % (medals[i] if i < 3 else '#%d' % (i + 1), u, v))
    lines += ['', 'Total do dia: *%d*' % tot,
              'Total da semana (%s a %s): *%d*' % (ws.strftime('%d/%m'), (ws + dt.timedelta(days=6)).strftime('%d/%m'), week)]
    falta = meta_sem - week
    lines.append(('Faltam *%d* vendas para bater a meta' % falta) if falta > 0 else ('✅ Meta batida! %d acima' % -falta))
    return '\n'.join(lines)

textos = [block(g['unidades'], int(g['meta_semana']), g['titulo']) for g in GRUPOS]

files = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1100, 'height': 900}, device_scale_factor=2)
    pg.goto('file://' + os.path.join(root, 'index.html') + '#relatorio')
    pg.wait_for_selector('#rep-title')
    for i, g in enumerate(GRUPOS):
        pg.evaluate("document.getElementById('rep-g%d').click()" % i)
        pg.fill('#rep-date', day); pg.dispatch_event('#rep-date', 'change')
        pg.fill('#rep-meta', str(g['meta_semana'])); pg.dispatch_event('#rep-meta', 'change')
        pg.wait_for_timeout(500)
        path = os.path.join(out, g['arquivo'].replace('.png', '_%s.png' % day.replace('-', '')))
        pg.locator('#rep').screenshot(path=path)
        files.append(path)
    b.close()

rotulo = 'Fechamento de %s' % br(d) if modo == 'fechamento' else 'Parcial de %s até %s' % (br(d), hora)
payload = {
    'modo': modo, 'dia': day, 'gerado_em': now_br.strftime('%d/%m/%Y %H:%M'), 'base_atualizada_em': meta['atualizado_em'],
    'imagens': [
        {'nome': os.path.basename(f), 'legenda': '📊 %s — %s' % (rotulo, g['nome']), 'base64': base64.b64encode(open(f, 'rb').read()).decode()}
        for f, g in zip(files, GRUPOS)
    ],
    'texto': '\n\n'.join(textos) + '\n\n_Fonte: CTN · base atualizada em %s_' % meta['atualizado_em'],
}
print(payload['texto'])

# Publica o relatório pronto em data/relatorio/ (o agente de WhatsApp consulta latest.json e envia quando muda)
import shutil
pub = os.path.join(root, 'data', 'relatorio'); os.makedirs(pub, exist_ok=True)
for f, g in zip(files, GRUPOS):
    shutil.copy(f, os.path.join(pub, g['arquivo']))
latest = {k: v for k, v in payload.items() if k != 'imagens'}
latest['id'] = day.replace('-', '') + '-' + modo + '-' + now_br.strftime('%H%M')
latest['imagens'] = [
    {'nome': g['arquivo'], 'legenda': img['legenda'],
     'url': 'https://raw.githubusercontent.com/%s/main/data/relatorio/%s' % (REPO, g['arquivo'])}
    for img, g in zip(payload['imagens'], GRUPOS)
]
json.dump(latest, open(os.path.join(pub, 'latest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
hist = os.path.join(pub, 'historico.jsonl')
with open(hist, 'a', encoding='utf-8') as f:
    f.write(json.dumps({k: latest[k] for k in ('id', 'modo', 'dia', 'gerado_em')}, ensure_ascii=False) + '\n')
print('\npublicado em data/relatorio/latest.json (id %s)' % latest['id'])

url = os.environ.get('N8N_WEBHOOK_URL', '').strip()
if not url:
    print('N8N_WEBHOOK_URL não definido — sem envio direto por webhook (o agente pode ler data/relatorio/latest.json).')
    sys.exit(0)
req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(req, timeout=120) as r:
    print('\nwebhook:', r.status, r.read(300).decode('utf-8', 'replace'))
