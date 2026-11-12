"""End-to-end tests for Mudra against a fake Firebase (no network, no real project).

Run:  pip install playwright && python -m playwright install chromium && python tests/e2e.py
Exits non-zero if any check fails. Used by .github/workflows/deploy.yml before every deploy.
"""
import asyncio, functools, json, os, shutil, sys, tempfile, threading, re
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = tempfile.mkdtemp(prefix='mudra-site-')
shutil.copytree(os.path.join(ROOT, 'public'), SITE, dirs_exist_ok=True)
with open(os.path.join(SITE, 'config.js'), 'w') as f:
    f.write("window.MUDRA_ENV={name:'test',firebase:{apiKey:'fake',authDomain:'fake',projectId:'fake',appId:'fake'}};")
FAKE = {n: open(os.path.join(ROOT, 'tests', 'fake', n)).read() for n in os.listdir(os.path.join(ROOT, 'tests', 'fake'))}

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=SITE))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_address[1]}/'

async def fake_sdk(route):
    await route.fulfill(status=200, body=FAKE[route.request.url.rsplit('/', 1)[1]],
                        headers={'content-type': 'application/javascript', 'access-control-allow-origin': '*'})

RESULTS = []
def check(name, cond, extra=''):
    RESULTS.append((name, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + name + (f'  [{extra}]' if extra and not cond else ''))

async def new_page(b, sw=False, mobile=False, **kw):
    ctx = await b.new_context(viewport={'width': 412 if mobile else 1100, 'height': 900},
                              service_workers='allow' if sw else 'block', **kw)
    await ctx.route('https://www.gstatic.com/firebasejs/**', fake_sdk)
    pg = await ctx.new_page()
    pg.dialogs = []
    def on_dialog(d):
        pg.dialogs.append(d.message)
        asyncio.ensure_future(d.accept('ERASE') if d.type == 'prompt' else d.accept())
    pg.on('dialog', on_dialog)
    pg.errors = []
    pg.on('pageerror', lambda e: pg.errors.append(str(e)))
    return ctx, pg

async def signed_in_with_sample(pg):
    await pg.goto(URL); await pg.wait_for_timeout(300)
    await pg.click('text=Sign in with Google'); await pg.wait_for_timeout(400)
    await pg.click('text=Load sample data'); await pg.wait_for_timeout(300)
    await pg.evaluate("window.__opened=[];window.open=u=>{window.__opened.push(u)}")

fs = lambda pg: pg.evaluate('JSON.parse(localStorage.fakefs||"{}")')

async def core(b):
    ctx, pg = await new_page(b)
    await pg.goto(URL); await pg.wait_for_timeout(300)
    check('signed-out gate shown', await pg.locator('text=Sign in with Google').count() == 1)
    check('nav hidden before sign-in', not await pg.locator('nav').is_visible())
    check('TEST tag in header', (await pg.inner_text('#envtag')) == 'TEST')
    await pg.click('text=Sign in with Google'); await pg.wait_for_timeout(400)
    check('empty account -> create batch', await pg.locator('text=Start by creating a batch').count() == 1)
    await pg.click('text=Load sample data'); await pg.wait_for_timeout(300)
    d = await fs(pg)
    check('sample data written to cloud', sum('/students/' in k for k in d) == 9 and 'studios/mudra' in d)
    ops0 = await pg.evaluate('window.__ops')
    await pg.locator('.tile').first.click(); await pg.wait_for_timeout(200)
    # layout guard: the filter bar must span the page (a CSS clash once squashed it)
    w = await pg.evaluate("document.querySelector('main .bar').getBoundingClientRect().width")
    check('layout: top bar spans the page', w > 600, f'width={w}')
    check('one toggle = exactly 1 write', await pg.evaluate('window.__ops') - ops0 == 1)
    await pg.click('nav >> text=Fees'); await pg.wait_for_timeout(200)
    check('no write loop after snapshots', await pg.evaluate('window.__ops') - ops0 == 1)
    await pg.reload(); await pg.wait_for_timeout(500); await pg.click('nav >> text=Students')
    check('data persists after reload', await pg.locator('#s-list .item').count() == 9)
    bid = next(v['batchId'] for k, v in (await fs(pg)).items() if '/students/' in k)
    await pg.evaluate(f"window.__fakeRemote('studios/mudra/students/zzremote',{{name:'Remote Riya',phone:'',batchId:'{bid}',fee:1000,joined:'2026-01-01',notes:'',active:true}})")
    await pg.wait_for_timeout(200)
    check('remote change appears live', await pg.locator('text=Remote Riya').count() == 1)
    # search keeps the same input element (Android keyboards) and filters
    inp = await pg.evaluate_handle("document.getElementById('s-search')")
    await pg.type('#s-search', 'Rem', delay=30)
    same = await pg.evaluate("i=>i===document.getElementById('s-search')", inp)
    check('search: input not rebuilt while typing', same)
    check('search: filters list', await pg.locator('#s-list .item').count() == 1)
    await pg.fill('#s-search', '')
    await pg.dispatch_event('#s-search', 'input')
    # edit while a remote update arrives
    await pg.locator('#s-list .item').first.click(); await pg.click('[data-act=student-edit]'); await pg.wait_for_timeout(100)
    await pg.evaluate(f"window.__fakeRemote('studios/mudra/students/zzremote2',{{name:'Another',phone:'',batchId:'{bid}',fee:1000,joined:'2026-01-01',notes:'',active:true}})")
    await pg.fill('textarea[name=notes]', 'edited during sync'); await pg.click('dialog button.primary'); await pg.wait_for_timeout(200)
    check('edit during remote update saved', any(v.get('notes') == 'edited during sync' for k, v in (await fs(pg)).items() if '/students/' in k))
    # delete prompt wording
    await pg.click('[data-act=student-edit]'); pg.dialogs.clear()
    await pg.evaluate("window.__realConfirm=window.confirm;window.confirm=m=>{window.__lastConfirm=m;return false}")
    await pg.click('[data-act=student-delete]')
    check('delete prompt says "Mark as left"', 'Mark as left' in (await pg.evaluate('window.__lastConfirm||""')))
    await pg.keyboard.press('Escape')
    await pg.evaluate("window.confirm=window.__realConfirm")
    # settings
    await pg.click('nav >> text=Settings')
    await pg.fill('#set-msg', 'Hi {name} {amount}'); await pg.dispatch_event('#set-msg', 'change'); await pg.wait_for_timeout(100)
    check('reminder template synced', (await fs(pg))['studios/mudra'].get('waTemplate') == 'Hi {name} {amount}')
    await pg.fill('#set-receipt', 'Got {amount} for {month}'); await pg.dispatch_event('#set-receipt', 'change'); await pg.wait_for_timeout(100)
    check('receipt template synced', (await fs(pg))['studios/mudra'].get('receiptTemplate') == 'Got {amount} for {month}')
    # erase
    await pg.click('text=Advanced'); await pg.click('text=Erase all data'); await pg.wait_for_timeout(300)
    check('erase deletes cloud docs', not any('/students/' in k for k in await fs(pg)))
    await pg.click('nav >> text=Settings'); await pg.click('text=Sign out'); await pg.wait_for_timeout(500)
    check('sign out -> gate', await pg.locator('text=Sign in with Google').count() == 1)
    await pg.evaluate("localStorage.setItem('fake-deny','1');localStorage.setItem('fake-email','stranger@gmail.com')")
    await pg.click('text=Sign in with Google'); await pg.wait_for_timeout(300)
    check('stranger gets No access', await pg.locator('text=No access').count() == 1)
    check('no JS errors (core)', not pg.errors, pg.errors[:2])
    await ctx.close()

async def features(b):
    ctx, pg = await new_page(b)
    await signed_in_with_sample(pg)
    # --- no class day
    await pg.click('nav >> text=Today')
    if await pg.locator('[data-act=clear-day]').count():
        await pg.click('[data-act=clear-day]'); await pg.wait_for_timeout(150)
    await pg.click('[data-act=no-class]'); await pg.click('dialog button.primary'); await pg.wait_for_timeout(200)
    check('no class: Today shows it', await pg.locator('text=No class — Holiday').count() == 1)
    d = await fs(pg)
    check('no class: stored as off day', any(v.get('off') for k, v in d.items() if '/attendance/' in k))
    await pg.click('nav >> text=History'); await pg.wait_for_timeout(150)
    check('no class: History shows chip', await pg.locator('.chip >> text=No class').count() >= 1)
    await pg.click('nav >> text=Today'); await pg.click('[data-act=class-on]'); await pg.wait_for_timeout(150)
    check('no class: undo restores tiles', await pg.locator('.tile').count() > 0)
    # --- receipt after Mark paid, phone with leading 0
    d = await fs(pg)
    sid = next(k.split('/')[-1] for k, v in d.items() if '/students/' in k and v.get('phone'))
    await pg.evaluate(f"""(()=>{{const k='studios/mudra/students/{sid}';const v=JSON.parse(localStorage.fakefs)[k];v.phone='09876500001';window.__fakeRemote(k,v)}})()""")
    await pg.wait_for_timeout(200)
    await pg.click('nav >> text=Fees'); await pg.wait_for_timeout(150)
    nm = d[f'studios/mudra/students/{sid}']['name']
    row = pg.locator('.item', has=pg.locator(f'text={nm}')).first
    if await row.locator('[data-act=pay]').count() == 0:   # make sure this student owes this month
        p = next((k for k, v in d.items() if '/payments/' in k and v['studentId'] == sid and v['month'] == await pg.evaluate("document.getElementById('f-month').value")), None)
        if p: await pg.evaluate(f"window.__fakeRemote('{p}',null)"); await pg.wait_for_timeout(200)
    await row.locator('[data-act=remind]').click(); await pg.wait_for_timeout(100)
    opened = await pg.evaluate('window.__opened')
    check('remind: 0-prefixed phone -> +91 number', bool(opened) and 'wa.me/919876500001' in opened[-1], opened[-1:] )
    await row.locator('[data-act=pay]').click(); await pg.wait_for_timeout(100)
    check('receipt checkbox offered, unticked by default', await pg.locator('dialog input[name=receipt]').count() == 1 and not await pg.locator('dialog input[name=receipt]').is_checked())
    await pg.check('dialog input[name=receipt]')
    await pg.click('dialog button.primary'); await pg.wait_for_timeout(200)
    opened = await pg.evaluate('window.__opened')
    check('receipt opens WhatsApp with message', bool(opened) and 'Received' in __import__('urllib.parse').parse.unquote(opened[-1]))
    check('resend receipt link shown', await pg.locator('[data-act=receipt]').count() >= 1)
    # --- income
    await pg.click('text=Money received in'); await pg.wait_for_timeout(150)
    check('income card shown', await pg.locator('text=Money received').count() >= 1 and await pg.locator('text=Financial year').count() == 1)
    check('income: 12 month bars', await pg.locator('.barc').count() == 12)
    w = await pg.evaluate("document.querySelector('main .bar').getBoundingClientRect().width")
    check('layout: reports month bar not squashed', w > 300, f'width={w}')
    async with pg.expect_download() as dl: await pg.click('[data-act=csv-pay]')
    check('payments CSV downloads', (await dl.value).suggested_filename == 'mudra-payments.csv')
    # --- batch move keeps history
    d = await fs(pg)
    batches = {k.split('/')[-1]: v['name'] for k, v in d.items() if '/batches/' in k}
    att = {k.split('/')[-1]: v for k, v in d.items() if '/attendance/' in k and not v.get('off')}
    mover = None
    for k, v in sorted(att.items()):
        if v['present'] and k.split('|')[0] < await pg.evaluate('new Date().toISOString().slice(0,10)'):
            mover, past_date, old_b = v['present'][0], k.split('|')[0], k.split('|')[1]; break
    new_b = next(b for b in batches if b != old_b)
    await pg.click('nav >> text=Students'); await pg.click(f"[data-act=open-student][data-id='{mover}']"); await pg.click('[data-act=student-edit]')
    await pg.select_option('select[name=batchId]', new_b); await pg.click('dialog button.primary'); await pg.wait_for_timeout(200)
    mv = (await fs(pg))[f'studios/mudra/students/{mover}']
    check('batch move recorded', mv['batchId'] == new_b and mv.get('prevBatches', [{}])[0].get('batchId') == old_b)
    await pg.click('nav >> text=Today'); await pg.fill('#t-date', past_date); await pg.dispatch_event('#t-date', 'change')
    await pg.select_option('#t-batch', old_b); await pg.wait_for_timeout(150)
    mname = mv['name']
    in_old = await pg.locator(f'.tile .nm >> text={mname}').count()
    await pg.select_option('#t-batch', new_b); await pg.wait_for_timeout(150)
    in_new = await pg.locator(f'.tile .nm >> text={mname}').count()
    check('batch move: past class keeps old batch', in_old == 1 and in_new == 0, f'old={in_old} new={in_new}')
    # --- safe sign-out while offline
    await ctx.set_offline(True)
    await pg.click('nav >> text=Settings'); pg.dialogs.clear(); await pg.click('text=Sign out'); await pg.wait_for_timeout(300)
    check('offline sign-out blocked', any('offline' in m for m in pg.dialogs) and await pg.locator('nav').is_visible())
    await ctx.set_offline(False)
    check('no JS errors (features)', not pg.errors, pg.errors[:2])
    await ctx.close()

async def resilience(b):
    # date rollover while the app stays open
    ctx, pg = await new_page(b, mobile=True)
    await pg.clock.install(time='2026-11-12T10:00:00')
    await signed_in_with_sample(pg)
    before = await pg.input_value('#t-date')
    await pg.clock.set_system_time('2026-11-13T09:00:00')
    await pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))"); await pg.wait_for_timeout(200)
    after = await pg.input_value('#t-date')
    check('date rolls over when app reopens', before == '2026-11-12' and after == '2026-11-13', f'{before}->{after}')
    await ctx.close()
    # first open offline with empty cache must not look like an empty account
    ctx, pg = await new_page(b)
    await pg.goto(URL)
    await pg.evaluate("localStorage.setItem('fakefs',JSON.stringify({'studios/mudra/students/x':{name:'X',batchId:'b',active:true}}));localStorage.setItem('fake-user',JSON.stringify({email:'a@b.c'}));localStorage.setItem('fake-offline','1');localStorage.setItem('fake-empty-cache','1')")
    await pg.reload(); await pg.wait_for_timeout(500)
    check('offline + empty cache: no fake empty app', await pg.locator('text=Start by creating a batch').count() == 0 and await pg.locator('text=Loading your data').count() == 1)
    await ctx.set_offline(True); await pg.wait_for_timeout(200)
    check("offline + empty cache: says you're offline", await pg.locator("text=You're offline").count() == 1)
    await ctx.close()
    # sync recovers after a listener error
    ctx, pg = await new_page(b)
    await pg.goto(URL)
    await pg.evaluate("localStorage.setItem('fake-user',JSON.stringify({email:'a@b.c'}));localStorage.setItem('fake-fail-once','1')")
    await pg.reload(); await pg.wait_for_timeout(6500)
    check('sync retries after an error', await pg.locator('text=Start by creating a batch').count() == 1)
    await ctx.close()

async def offline_sw(b):
    ctx, pg = await new_page(b, sw=True, mobile=True)
    await pg.goto(URL); await pg.wait_for_timeout(300)
    await pg.click('text=Sign in with Google'); await pg.wait_for_timeout(300)
    await pg.click('text=Load sample data'); await pg.wait_for_timeout(300)
    await pg.evaluate('navigator.serviceWorker.ready'); await pg.wait_for_timeout(800)
    await ctx.set_offline(True); await pg.reload(); await pg.wait_for_timeout(800)
    check('opens offline with data (service worker)', await pg.locator('.tile').count() > 0)
    await ctx.close()

async def tabbar(b):
    ctx, pg = await new_page(b, mobile=True, has_touch=False)
    await signed_in_with_sample(pg)
    await pg.click('nav >> text=Fees'); await pg.wait_for_timeout(700)
    off = await pg.evaluate("(()=>{const p=document.querySelector('.navpill').getBoundingClientRect(),b=document.querySelector('nav button.on').getBoundingClientRect();return Math.abs(p.left-b.left)+Math.abs(p.width-b.width)})()")
    check('tab bar: highlight lines up with active tab', off < 3, f'offset={off}')
    # drag from Fees to Today along the bar
    fb = await pg.locator('nav button[data-id=fees]').bounding_box(); tb = await pg.locator('nav button[data-id=today]').bounding_box()
    y = fb['y'] + fb['height'] / 2
    await pg.mouse.move(fb['x'] + fb['width'] / 2, y); await pg.mouse.down()
    for i in range(1, 11):
        await pg.mouse.move(fb['x'] + fb['width'] / 2 + (tb['x'] - fb['x']) * i / 10, y); await pg.wait_for_timeout(16)
    await pg.mouse.up(); await pg.wait_for_timeout(700)
    on = await pg.evaluate("document.querySelector('nav button.on').dataset.id")
    check('tab bar: drag to scrub switches tab', on == 'today', on)
    check('tab bar: Today content shown after drag', await pg.locator('#t-date').count() == 1)
    await pg.wait_for_timeout(2600); await pg.evaluate("document.querySelector('#toast').classList.add('show')"); await pg.wait_for_timeout(350)
    gap = await pg.evaluate("document.querySelector('nav').getBoundingClientRect().top-document.querySelector('#toast').getBoundingClientRect().bottom")
    check('toast sits above the tab bar', gap > 0, f'gap={gap}')
    check('no JS errors (tab bar)', not pg.errors, pg.errors[:2])
    await ctx.close()

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for suite in (core, features, resilience, tabbar, offline_sw):
            try: await suite(b)
            except Exception as e: check(f'{suite.__name__} crashed', False, repr(e)[:300])
        await b.close()
    failed = [n for n, ok in RESULTS if not ok]
    print(f'\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed')
    sys.exit(1 if failed else 0)

asyncio.run(main())
