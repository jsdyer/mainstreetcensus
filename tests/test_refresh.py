"""Exercise original and revised cells through the same official-format CSV adapter."""
import csv
from io import BytesIO, StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from refresh import BANDS, NAICS, PREFIX, extract


class RefreshTests(unittest.TestCase):
    def test_revision_and_suppression_in_a_single_edition(self):
        edition = {"id": "33101176", "title": PREFIX + "June 2026"}
        config = {"industries": ["7225"], "names": {}, "featured_areas": [],
                  "comparisons": [{"a": "5915001", "b": "5915002", "industry": "7225"}]}
        # Four published totals in the 2026-11-27 retrieval. Revised totals and
        # size-band observations below are synthetic cases for the same table ID.
        places = [("2021A00055915001", "Langley", 302),
                  ("2021A00055915002", "Langley", 61),
                  ("2021A00051209034", "Halifax", 915),
                  ("2021S0503205", "Halifax", 935)]
        for township_total in (302, 303):
            with self.subTest(township_total=township_total), TemporaryDirectory() as folder:
                contents = StringIO()
                writer = csv.writer(contents)
                writer.writerow(["DGUID", "GEO", NAICS, "Employment size", "VALUE", "STATUS", "UOM", "SCALAR_FACTOR"])
                industry = "Full-service restaurants and limited-service eating places [7225]"
                for dguid, name, count in places:
                    total = township_total if dguid == places[0][0] else count
                    writer.writerow([dguid, name, industry, BANDS[0], total, "", "Number", "units"])
                dguid, name, _ = places[0]
                writer.writerow([dguid, name, industry, BANDS[1], 0, "", "Number", "units"])
                writer.writerow([dguid, name, industry, BANDS[2], "", "x", "Number", "units"])
                writer.writerow([dguid, name, "Other industry [5415]", BANDS[0], 10, "", "Number", "units"])
                raw = BytesIO()
                with ZipFile(raw, "w") as archive:
                    archive.writestr("33101176_MetaData.csv", 'Title,ID\n"' + edition["title"] + '",33101176\n')
                    archive.writestr("33101176.csv", contents.getvalue())
                target = Path(folder) / "edition"
                result = extract(raw, edition, config, target)
                self.assertEqual(list(result["industries"]), ["7225"])
                self.assertFalse((target / "5415.json").exists())
                rows = json.loads((target / "7225.json").read_text())
                self.assertEqual({area: cells[0] for area, cells in rows.items()},
                                 {"5915001": township_total, "5915002": 61, "1209034": 915, "205": 935})
                self.assertEqual(rows["5915001"][1:4], [0, None, None])
