import json
from html.parser import HTMLParser
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build import ROOT, build, metadata
from refresh import BANDS, PREFIX, discover


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.hrefs=[]; self.canonicals=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=="a" and attrs.get("href"): self.hrefs.append(attrs["href"])
        if tag=="link" and attrs.get("rel")=="canonical": self.canonicals.append(attrs["href"])


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        shutil.copytree(ROOT/"web",cls.root/"web")
        for f in ("tool.json","README.md"):shutil.copy(ROOT/f,cls.root/f)
        build(cls.root);cls.dist=cls.root/"dist"
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_every_sitemap_result_is_navigable_and_canonical(self):
        urls=ET.parse(self.dist/"sitemap.xml").findall(".//{*}loc")
        counts=json.loads((self.dist/"data/status.json").read_text())
        self.assertEqual(len(urls),counts["result_pages"])
        base=metadata(self.root)["url"]; seen=set()
        for node in urls:
            url=node.text
            self.assertNotIn(url,seen);seen.add(url)
            path=self.dist / urlsplit(url).path.removeprefix(base)/"index.html"
            parser=Links();parser.feed(path.read_text());self.assertEqual(parser.canonicals,[url])
            for href in parser.hrefs:
                parts=urlsplit(href)
                if parts.scheme or parts.netloc or href.startswith("#"):continue
                target=(path.parent/parts.path).resolve()
                self.assertTrue(target.exists(),str(target))
    def test_langley_halifax_and_industries(self):
        index=json.loads((self.dist/"data/editions.json").read_text())
        ed=index["editions"][0]
        for c in ed["comparisons"]:
            rows = json.loads((self.dist / "data" / ed["id"] / (c["industry"] + ".json")).read_text())
            page=(self.dist/"records"/c["slug"]/"index.html").read_text()
            for area in (c["a"],c["b"]):
                self.assertIn(f'<strong>{rows[area][0]:,}</strong>', page)
                self.assertIn(f' · {area}</small>', page)
            self.assertIn(f'NAICS {c["industry"]}', page)
        self.assertIn("counting-restaurant-locations-in-langley/",(self.dist/"records/langley-restaurant-locations/index.html").read_text())

    def test_current_edition_dimensions_and_cells(self):
        edition = json.loads((self.dist / "data/editions.json").read_text())["editions"][0]
        folder = self.dist / "data" / edition["id"]
        areas = json.loads((folder / "geographies.json").read_text())
        self.assertEqual(edition["geographies"], len(areas))
        self.assertEqual(edition["bands"], BANDS)
        config = json.loads((ROOT / "sources.json").read_text())
        self.assertEqual(set(edition["industries"]), set(config["industries"]))
        for area, (name, dguid) in areas.items():
            self.assertTrue(name.strip(), area)
            kind = "S0503" if len(area) == 3 else "A0005"
            self.assertRegex(dguid, rf"^\d{{4}}{kind}{area}$")
        for code in edition["industries"]:
            rows = json.loads((folder / (code + ".json")).read_text())
            self.assertTrue(rows, code)
            self.assertFalse(rows.keys() - areas.keys(), code)
            for area, cells in rows.items():
                self.assertEqual(len(cells), len(BANDS), (code, area))
                self.assertTrue(all(x is None or type(x) is int and x >= 0 for x in cells), (code, area))

    def test_nonmatching_and_older_tables_do_not_override_latest(self):
        fixtures=[{"cubeTitleEn":PREFIX+"June 2026","productId":33101176,"releaseTime":"2026-08-14T00:00:00Z"},
                  {"cubeTitleEn":PREFIX+"December 2026","productId":33109999,"releaseTime":"2027-02-19T00:00:00Z"},
                  {"cubeTitleEn":PREFIX.replace("with employees","without employees")+"June 2027","productId":33100001,"releaseTime":"2027-08-01"}]
        self.assertEqual(discover(fixtures)["id"],"33109999")
        with self.assertRaises(ValueError): discover([])
    def test_size_bands_are_locations_and_total_not_a_band(self):
        self.assertEqual(BANDS[0],"Total, with employees")
        self.assertIn("500 plus employees",BANDS[1:])
