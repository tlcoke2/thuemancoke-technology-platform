"""Accessible, script-free branded presentation for TCL staging customer gateway.

All data-derived values passed to page() must already be HTML escaped; it wraps
server-authored fragments, never raw request strings. No external assets or JS.
"""
from html import escape

STYLESHEET = "\n:root{color-scheme:light;--navy:#0b1834;--navy2:#13274a;--ink:#132440;--muted:#60718a;--line:#dfe8f1;--paper:#fff;--bg:#f4f7fb;--blue:#1763e8;--aqua:#0a9d92;--softblue:#eaf1ff;--shadow:0 18px 55px rgba(19,39,74,.09)}\n*{box-sizing:border-box}\nhtml{scroll-behavior:smooth}\nbody{margin:0;min-height:100vh;font-family:Inter,ui-sans-serif,system-ui,-apple-system,\"Segoe UI\",Arial,sans-serif;color:var(--ink);background:radial-gradient(ellipse at 85% 0%,#e8efff 0%,transparent 38%),linear-gradient(180deg,#f6f9fd,#edf3f9)}\na{color:var(--blue);text-underline-offset:.17em}a:hover{text-decoration-color:var(--aqua)}\nbutton,a.button{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:12px 20px;border-radius:11px;border:1px solid #0e54ca;background:var(--blue);color:#fff;font:inherit;font-weight:700;text-decoration:none;cursor:pointer;box-shadow:0 5px 13px rgba(23,99,232,.14);transition:background .2s,transform .2s}\nbutton:hover,a.button:hover{background:#124ab1;transform:translateY(-1px)}button:disabled{opacity:.6;cursor:not-allowed}\na.button.secondary,button.secondary{background:#fff;border-color:#d6e1ee;color:var(--ink);box-shadow:none}a.button.secondary:hover,button.secondary:hover{background:#f4f8fe}\nbutton.danger{background:#fff;color:#9c2a36;border-color:#edcbd0;box-shadow:none}button.danger:hover{background:#fff1f2}\n:focus-visible{outline:3px solid #2fb8d3;outline-offset:3px}\n.skip{position:absolute;left:-9999px;top:10px;background:#fff;padding:12px;z-index:10}.skip:focus{left:10px}\n.top{background:var(--navy);color:#e5efff;border-bottom:1px solid #283a58}\n.nav{max-width:1160px;margin:auto;min-height:82px;padding:18px 30px;display:flex;align-items:center;justify-content:space-between;gap:22px}\n.brand{display:flex;align-items:center;gap:13px;text-decoration:none;color:#fff}\n.mark{width:43px;height:43px;display:grid;place-items:center;border-radius:12px;background:linear-gradient(140deg,#2d84f5,#19afa0);font-weight:850;font-size:18px;letter-spacing:-1px}\n.brand-text{display:flex;flex-direction:column;gap:2px}.brand strong{font-size:14px;letter-spacing:.02em}.brand small{font-size:11px;color:#b8c9e4;letter-spacing:.12em;text-transform:uppercase}\n.links{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.links a{color:#dce8fa;font-size:13px;text-decoration:none;padding:9px 11px;border-radius:8px}.links a:hover{background:#223b61;color:#fff}\n.main{max-width:1160px;padding:44px 30px 60px;margin:0 auto;min-height:calc(100vh - 174px)}\n.hero{padding:4px 0 26px;max-width:820px}.eyebrow{display:inline-flex;align-items:center;gap:8px;color:#177f7d;font-weight:800;text-transform:uppercase;letter-spacing:.14em;font-size:11px;margin:0 0 14px}.eyebrow:before{content:\"\";height:8px;width:8px;background:#13b5a6;border-radius:50%;box-shadow:0 0 0 4px #d8f5ee}\nh1{font-size:clamp(29px,4vw,45px);letter-spacing:-.045em;line-height:1.12;margin:0 0 13px;color:var(--navy)}\nh2{font-size:clamp(18px,2.5vw,23px);letter-spacing:-.02em;color:var(--navy)}h3{color:var(--navy);font-size:17px}\np{line-height:1.66;margin:10px 0 18px}.lede{font-size:17px;color:var(--muted);max-width:750px;margin:0}.fine{font-size:13px;color:var(--muted)}.muted{color:var(--muted)}\n.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:22px;align-items:start}\n.card{background:var(--paper);border:1px solid var(--line);border-radius:20px;box-shadow:var(--shadow);padding:26px;margin:0 0 22px;overflow-wrap:anywhere}\n.card h2,.card h3{margin-top:0}.card p:last-child{margin-bottom:0}\n.panel-gradient{background:linear-gradient(155deg,#12284b,#0c1832);color:#edf7ff;border-color:#263e63}\n.panel-gradient h2,.panel-gradient h3{color:#fff}.panel-gradient .muted,.panel-gradient .fine{color:#bfcee5}.panel-gradient .pill{background:#22405a;color:#c3f8e9}\n.card header{margin-bottom:18px}.actions{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:18px 0}\n.stat{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:700;border-radius:999px;padding:7px 12px;white-space:normal;background:#e8f9f2;color:#106548}\n.stat::before{content:\"\";height:7px;width:7px;background:currentColor;border-radius:50%}\n.stat.pending{color:#805c13;background:#fff6dc}.stat.revoked,.stat.expired{color:#9b3442;background:#ffeff1}\n.kicker{display:block;color:#7890ae;font-size:12px;text-transform:uppercase;letter-spacing:.12em;font-weight:750;margin-bottom:10px}\n.value{font-size:16px;font-weight:750}.feature-list{margin:0;padding:0;list-style:none;display:grid;gap:14px}.feature-list li{display:flex;gap:10px;align-items:flex-start;line-height:1.5}.feature-list li:before{content:\"✓\";display:grid;place-items:center;flex:0 0 23px;height:23px;color:#24d4b5;background:#1e4260;border-radius:50%;font-size:12px;font-weight:800}\n.notice{border:1px solid #c8dcfc;background:#eef5ff;border-radius:12px;padding:13px 16px;color:#214169;margin:17px 0;font-size:14px}\n.notice.warn{background:#fff8e9;border-color:#f2dfb0;color:#775a17}.notice.danger{background:#fff1f2;border-color:#f2c8cf;color:#8f2935}\n.code{display:block;white-space:normal;overflow-wrap:anywhere;padding:12px 13px;background:#f0f4fa;border:1px solid #dfe8f2;border-radius:9px;color:#203859;font:12px/1.6 ui-monospace,SFMono-Regular,Consolas,monospace}\ndl{display:grid;grid-template-columns:minmax(100px,170px) 1fr;gap:10px;margin:15px 0 22px}dt{font-size:12px;letter-spacing:.02em;color:var(--muted);font-weight:700}dd{margin:0;font-size:14px;overflow-wrap:anywhere}\nform{max-width:100%}form label{display:block;font-size:13px;font-weight:700;color:var(--ink);margin-bottom:6px}\ninput,select,textarea{width:100%;min-width:0;max-width:600px;display:block;margin:7px 0 15px;padding:12px 13px;border:1px solid #c9d5e5;border-radius:10px;font:inherit;background:#fff;color:var(--ink)}\ninput:focus,textarea:focus{border-color:#5594e9;outline:3px solid #deebff}\ninput[type=hidden]{display:none}form button{margin:3px 0}\ntable{width:100%;border-collapse:collapse;font-size:13px;table-layout:auto}th{text-align:left;background:#eff4fa;color:#4a6281;font-size:11px;text-transform:uppercase;letter-spacing:.08em}th,td{padding:12px 14px;border-bottom:1px solid #e6edf5;vertical-align:top;overflow-wrap:anywhere}td form{margin:4px 0}td button{padding:7px 12px;min-height:37px;font-size:12px}\n.table-scroll{overflow-x:auto;border:1px solid #e6edf5;border-radius:12px}\n.segment{display:flex;align-items:center;justify-content:space-between;gap:15px;flex-wrap:wrap}\n.footer{background:#0d1a34;color:#9eafca;padding:24px 30px;font-size:12px}.footer .inside{max-width:1100px;margin:auto;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}\n.footer a{color:#d9e8ff}.footer strong{color:#fff}\n@media(max-width:720px){.nav{padding:16px 20px;align-items:flex-start;flex-direction:column}.links{gap:1px}.links a{padding:8px}.main{padding:29px 17px 45px}.card{padding:19px;border-radius:15px}.grid{gap:14px}.brand-text strong{font-size:13px}dl{grid-template-columns:1fr;gap:4px}dt{margin-top:10px}.footer{padding:20px 17px}}\n@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}button,a.button{transition:none}}\n"


def page(title, body, *, eyebrow="SECURE CUSTOMER PORTAL", intro="", notice="STAGING ENVIRONMENT"):
    safe_title = escape(str(title), quote=True)
    safe_eyebrow = escape(str(eyebrow), quote=True)
    safe_intro = escape(str(intro), quote=True)
    safe_notice = escape(str(notice), quote=True)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="color-scheme" content="light">'
        '<meta name="robots" content="noindex,nofollow,noarchive">'
        '<link rel="stylesheet" href="/assets/gateway.css">'
        '<title>' + safe_title + ' | TCL Customer Gateway</title></head><body>'
        '<a class="skip" href="#content">Skip to main content</a>'
        '<header class="top"><nav class="nav" aria-label="Main navigation">'
        '<a class="brand" href="/"><span class="mark">TCL</span>'
        '<span class="brand-text"><strong>Thueman Coke Limited</strong>'
        '<small>Customer gateway</small></span></a>'
        '<div class="links"><a href="/">Home</a><a href="/account">My account</a>'
        '<a href="/customer">Customer access</a></div></nav></header>'
        '<main class="main" id="content"><div class="hero"><div class="eyebrow">'
        + safe_eyebrow + '</div><h1>' + safe_title + '</h1>'
        + ('<p class="lede">' + safe_intro + '</p>' if intro else '')
        + '</div>' + body + '</main>'
        '<footer class="footer"><div class="inside">'
        '<span><strong>TCL</strong> · Secure software distribution · '
        + safe_notice + '</span>'
        '<span>Protected by verified identity, access controls and audit logging. '
        'A download is not a software licence.</span></div></footer></body></html>'
    )


def message_page(title, message, *, action="/", action_label="Return to gateway",
                 eyebrow="ACCOUNT INFORMATION"):
    return page(title,
        '<section class="card"><p>' + escape(str(message), quote=True)
        + '</p><div class="actions"><a class="button" href="'
        + escape(action, quote=True) + '">'
        + escape(action_label, quote=True) + '</a></div></section>',
        eyebrow=eyebrow)
