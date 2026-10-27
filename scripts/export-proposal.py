"""Render the five Mermaid diagrams and an A4 draft PDF entirely on this machine."""

import asyncio
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "docs/proposal"


async def main():
    mermaid = PROPOSAL / "tools/node_modules/mermaid/dist/mermaid.min.js"
    if not mermaid.is_file():
        raise SystemExit("Run npm ci --prefix docs/proposal/tools first")
    exported = PROPOSAL / "diagrams/exported"
    exported.mkdir(exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(
            viewport={"width": 1800, "height": 1200}, device_scale_factor=2
        )
        remote = []

        async def offline(route):
            if route.request.url.startswith(("file:", "data:", "about:")):
                await route.continue_()
            else:
                remote.append(route.request.url)
                await route.abort()

        await context.route("**/*", offline)
        page = await context.new_page()
        await page.set_content(
            "<html><body style='margin:20px;background:white'></body></html>"
        )
        await page.add_script_tag(path=str(mermaid))
        await page.evaluate("""() => mermaid.initialize({startOnLoad:false,securityLevel:'strict',
            theme:'base',fontFamily:'Segoe UI, Arial, sans-serif',
            themeVariables:{primaryColor:'#fff0df',primaryTextColor:'#222222',
                primaryBorderColor:'#cc6900',lineColor:'#666666',fontSize:'16px'},
            flowchart:{htmlLabels:false,useMaxWidth:false},
            sequence:{useMaxWidth:false},er:{useMaxWidth:false}})""")
        files = []
        for index, source in enumerate(sorted((PROPOSAL / "diagrams").glob("*.mmd"))):
            svg = await page.evaluate(
                """async ({source,id}) => {
                const result = await mermaid.render(id,source); return result.svg;
            }""",
                {"source": source.read_text(encoding="utf-8"), "id": f"diagram{index}"},
            )
            (exported / f"{source.stem}.svg").write_text(svg, encoding="utf-8")
            await page.evaluate("svg => { document.body.innerHTML = svg; }", svg)
            await page.locator("svg").screenshot(
                path=str(exported / f"{source.stem}.png")
            )
            files.append(source.name)
        await asyncio.to_thread(
            subprocess.run,
            ["node", str(PROPOSAL / "tools/render-markdown.mjs")],
            check=True,
            cwd=ROOT,
            capture_output=True,
        )
        await page.goto((PROPOSAL / "FPH_Senklok.html").as_uri())
        await page.evaluate("""async () => { await document.fonts.ready;
            await Promise.all([...document.images].map(image => image.decode())); }""")
        overflow = await page.evaluate("""() => [...document.querySelectorAll('img')]
            .filter(image => !image.naturalWidth).map(image => image.src)""")
        if overflow or remote:
            raise RuntimeError(
                f"Missing local images: {overflow}; external requests: {remote}"
            )
        pdf = PROPOSAL / "FPH_Senklok_DRAFT.pdf"
        await page.pdf(
            path=str(pdf),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            display_header_footer=True,
            header_template='<div style="font-size:8px;color:#777;width:100%;'
            'padding:0 18mm">SentriFlow · Team Senklok · Working draft</div>',
            footer_template='<div style="font-size:8px;color:#777;width:100%;'
            'text-align:right;padding:0 18mm">'
            '<span class="pageNumber"></span> / '
            '<span class="totalPages"></span></div>',
        )
        await page.screenshot(path=str(PROPOSAL / "cover-preview.png"), full_page=False)
        await browser.close()
    report = {
        "exported_at": datetime.now(UTC).isoformat(),
        "diagrams": files,
        "pdf": pdf.name,
        "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "page_count": len(re.findall(rb"/Type\s*/Page\b", pdf.read_bytes())),
        "external_requests": remote,
        "status": "Working draft; not submitted",
    }
    (PROPOSAL / "export-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
