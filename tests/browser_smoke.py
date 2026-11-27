"""Exercise the real saved edition, static profiles and an editable comparison."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import os
import threading
import json
from tempfile import TemporaryDirectory
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]


def main():
    ed=json.loads((ROOT/"dist/data/editions.json").read_text())["editions"][0]
    rows=json.loads((ROOT/"dist/data"/ed["id"]/"7225.json").read_text())
    with TemporaryDirectory() as folder:
        Path(folder,"mainstreetcensus").symlink_to(ROOT/"dist",target_is_directory=True)
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(("127.0.0.1",0),partial(Quiet,directory=folder))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f"http://127.0.0.1:{server.server_port}/mainstreetcensus/"
        try:
            with sync_playwright() as p:
                br=p.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH") or None,args=["--no-sandbox"])
                pg=br.new_page(viewport={"width":1280,"height":900})
                pg.route("**/assets/tool-metrics.js",lambda route:route.fulfill(body=""))
                pg.goto(url); expect(pg.locator("#compare")).to_be_visible()
                expect(pg.locator("#result")).to_contain_text(f'{rows["5915001"][0]:,}')
                (ROOT/"browser-checks").mkdir(exist_ok=True)
                pg.screenshot(path=str(ROOT/"browser-checks/desktop.png"))
                pg.set_viewport_size({"width":390,"height":844})
                pg.get_by_label("First place").fill("Halifax Regional Municipality, NS · 1209034")
                pg.get_by_label("Second place").fill("Halifax metro area · 205")
                pg.get_by_role("button",name="Compare locations").click()
                expect(pg.locator("#result")).to_contain_text(f'{rows["1209034"][0]:,}')
                pg.get_by_text("See counts by employee-size band").click()
                expect(pg.locator("#result table tbody tr")).to_have_count(8)
                pg.reload();expect(pg.get_by_label("Second place")).to_have_value("Halifax metro area · 205")
                pg.screenshot(path=str(ROOT/"browser-checks/mobile.png"))
                assert pg.evaluate("document.documentElement.scrollWidth <= innerWidth")
                pg.get_by_role("button",name="Use Langley example").click()
                expect(pg.locator("#result")).to_contain_text("Township of Langley")
                native=br.new_page(viewport={"width":320,"height":720},java_script_enabled=False)
                native.goto(url+"records/halifax-restaurant-locations/")
                expect(native.locator("main")).to_contain_text(f'{rows["205"][0]:,}')
                native.get_by_role("link",name="Explore this industry across Canada").click()
                native.get_by_role("link",name="Halifax metro area",exact=True).click()
                expect(native.locator("h1")).to_contain_text("Halifax metro area")
                assert native.evaluate("document.documentElement.scrollWidth <= innerWidth")
                br.close()
        finally:
            server.shutdown();thread.join()
if __name__=="__main__":main()
