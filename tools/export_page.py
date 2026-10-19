"""Export an artifact page source to a standalone light-theme HTML and a PDF (headless Chromium).

    python3 export_page.py <page.html> <out-dir> <base name> [image.png=path ...]

Wraps the page body in a doctype with data-theme="light", renders <pre class="mermaid"> with mermaid@11.4.1
(jsDelivr), inlines the listed images as data URIs, and prints A4 with backgrounds.
"""
import base64
import os
import subprocess
import sys

src, outdir, base = sys.argv[1], sys.argv[2], sys.argv[3]
images = dict(a.split("=", 1) for a in sys.argv[4:])
body = open(src, encoding="utf-8").read()
for name, path in images.items():
    data = base64.b64encode(open(path, "rb").read()).decode()
    body = body.replace(f'src="{name}"', f'src="data:image/png;base64,{data}"')
html = ('<!doctype html><html lang="en" data-theme="light"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<style>@page{size:A4;margin:12mm} .mermaid-wrap{break-inside:avoid} tr,figure,.card{break-inside:avoid}'
        ' details>summary{display:none} details{display:block}</style></head><body>'
        + body.replace('<details class="col">', '<details class="col" open>') +
        '<script src="https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"></script>'
        '<script>mermaid.initialize({startOnLoad:true,securityLevel:"strict",theme:"base",'
        'flowchart:{useMaxWidth:true},themeVariables:{primaryColor:"#f4efe4",primaryTextColor:"#42392e",'
        'lineColor:"#8a7f6d",primaryBorderColor:"#7a6c52",fontSize:"15px"}});</script></body></html>')
os.makedirs(outdir, exist_ok=True)
out_html = os.path.join(outdir, base + ".html")
out_pdf = os.path.join(outdir, base + ".pdf")
open(out_html, "w", encoding="utf-8").write(html)
chrome = os.path.expanduser("~/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome")
subprocess.run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--run-all-compositor-stages-before-draw",
                "--virtual-time-budget=15000", "--no-pdf-header-footer", f"--print-to-pdf={out_pdf}",
                "file://" + os.path.abspath(out_html)], capture_output=True, check=True)
print(out_html)
print(out_pdf)
