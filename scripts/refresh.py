"""Find the latest semiannual employer-location cube and retain a bounded industry extract."""
import argparse
import csv
from datetime import datetime, timezone
from io import BytesIO, TextIOWrapper
import json
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = "https://www150.statcan.gc.ca/t1/wds/rest/getAllCubesListLite"
PREFIX = "Canadian Business Counts, with employees, census metropolitan areas and census subdivisions, "
TITLE = re.compile(re.escape(PREFIX) + r"(June|December) (20\d{2})", re.I)
BANDS = ["Total, with employees", "1 to 4 employees", "5 to 9 employees", "10 to 19 employees",
         "20 to 49 employees", "50 to 99 employees", "100 to 199 employees", "200 to 499 employees", "500 plus employees"]
PROVINCES = dict(zip("10 11 12 13 24 35 46 47 48 59 60 61 62".split(),
                     "NL PE NS NB QC ON MB SK AB BC YT NT NU".split()))
NAICS = "North American Industry Classification System (NAICS)"


def fetch(url, limit):
    req = Request(url, headers={"User-Agent": "CoolCode Main Street Census (+https://coolcode.ca/mainstreetcensus/)"})
    with urlopen(req, timeout=120) as res:
        data = res.read(limit + 1)
    if not data or len(data) > limit:
        raise ValueError("Empty or unexpectedly large Statistics Canada response")
    return data


def discover(cubes):
    editions = []
    for cube in cubes:
        title = cube.get("cubeTitleEn", "")
        match = TITLE.fullmatch(title)
        if not match:
            continue
        month, year = match.groups()
        period = year + ("-06" if month.lower() == "june" else "-12")
        product_id = str(cube["productId"])
        if not re.fullmatch(r"33\d{6}", product_id):
            raise ValueError("Unexpected table identifier")
        editions.append({"id": product_id, "period": period, "label": month.title()+" "+year,
                         "release": cube["releaseTime"][:10], "title": title})
    if not editions:
        raise ValueError("No matching local employer location table in the publisher catalogue")
    return max(editions, key=lambda e: (e["period"], e["release"], e["id"]))


def write(path, obj):
    path.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False)+"\n", encoding="utf-8")


def extract(archive, edition, config, target):
    product = edition["id"]
    labels, geo, counts = {}, {}, {code:{} for code in config["industries"]}
    with ZipFile(archive) as z:
        if sum(i.file_size for i in z.infolist()) > 512_000_000:
            raise ValueError("Unexpected uncompressed cube size")
        with z.open(product+"_MetaData.csv") as source:
            metadata = csv.reader(TextIOWrapper(source, encoding="utf-8-sig"))
            next(metadata)
            identity = next(metadata)
            if identity[:2] != [edition["title"], product]:
                raise ValueError("Table identity differs from the catalogue")
        with z.open(product+".csv") as source:
            rows = csv.reader(TextIOWrapper(source, encoding="utf-8-sig", newline=""))
            fields = next(rows)
            i_geo,i_name,i_group,i_band,i_value,i_status,i_unit,i_scalar = map(fields.index,(
                "DGUID","GEO",NAICS,"Employment size","VALUE","STATUS","UOM","SCALAR_FACTOR"))
            band_ids = {name:i for i,name in enumerate(BANDS)}
            geo_codes = {}
            for row in rows:
                group = row[i_group]
                code = group.rpartition("[")[2].removesuffix("]")
                if code not in counts and code != "1":
                    continue
                if row[i_unit] != "Number" or row[i_scalar] != "units":
                    raise ValueError("Location unit changed")
                dguid = row[i_geo]
                if dguid not in geo_codes:
                    match = re.fullmatch(r"\d{4}(?:A0005(\d{7})|S0503(\d{3}))", dguid)
                    if not match:
                        raise ValueError("Unknown boundary type: "+dguid)
                    area = match[1] or match[2]
                    geo_codes[dguid] = area
                    if area in geo:
                        raise ValueError("Ambiguous area identifier")
                    geo[area] = [config["names"].get(area,row[i_name]), dguid]
                area = geo_codes[dguid]
                if code == "1":
                    continue
                label = group.rpartition(" [")[0]
                if labels.setdefault(code,label) != label:
                    raise ValueError("Industry classification label changed inside one cube")
                band = band_ids[row[i_band]]
                series = counts[code].setdefault(area,[None]*len(BANDS))
                if series[band] is not None:
                    raise ValueError("Duplicate published cell")
                value = row[i_value]
                if value and (row[i_status] or not re.fullmatch(r"\d+",value)):
                    raise ValueError("Unrecognized numeric status in employer count")
                series[band] = int(value) if value else None
    if set(labels) != set(counts) or not geo:
        raise ValueError("Missing configured industry or geography coverage")
    for example in config["comparisons"]:
        group = counts[example["industry"]]
        if any(area not in group or group[area][0] is None for area in (example["a"],example["b"])):
            raise ValueError("Missing featured published employer-location total")
    target.mkdir()
    write(target/"geographies.json",geo)
    for code, records in counts.items():
        write(target/(code+".json"), records)
    return {**edition, "industries": labels, "geographies":len(geo), "bands":BANDS,
            "provinces":PROVINCES, "comparisons":config["comparisons"], "featured_areas":config["featured_areas"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalogue",type=Path,help="Replay a saved official WDS catalogue")
    parser.add_argument("--zip",type=Path,help="Replay the matching official English table export")
    args = parser.parse_args()
    config = json.loads((ROOT/"sources.json").read_text())
    catalogue = args.catalogue.read_bytes() if args.catalogue else fetch(CATALOGUE,32_000_000)
    edition = discover(json.loads(catalogue))
    data = ROOT/"web/data"
    data.mkdir(parents=True,exist_ok=True)
    index = data/"editions.json"
    previous = json.loads(index.read_text()) if index.exists() else {"editions":[]}
    if previous["editions"] and previous["editions"][0]["period"] > edition["period"]:
        raise ValueError("Source catalogue regressed to an earlier edition")
    archive = args.zip or BytesIO(fetch(f"https://www150.statcan.gc.ca/n1/tbl/csv/{edition['id']}-eng.zip",100_000_000))
    with TemporaryDirectory(dir=data) as temp:
        stage = Path(temp)/edition["id"]
        entry = extract(archive,edition,config,stage)
        entries = [entry]+[item for item in previous["editions"] if item["id"]!=edition["id"]]
        write(Path(temp)/"editions.json", {"checked_at":datetime.now(timezone.utc).isoformat(timespec="seconds"), "editions":entries})
        dest = data/entry["id"]
        if dest.exists():
            dest.rename(Path(temp)/"previous")
        try:
            stage.rename(dest)
            (Path(temp)/"editions.json").replace(index)
        except Exception:
            if dest.exists():
                shutil.rmtree(dest)
            if (Path(temp)/"previous").exists():
                (Path(temp)/"previous").rename(dest)
            raise
    print(f"{entry['label']}: {entry['geographies']} areas and {len(entry['industries'])} industry groups")


if __name__ == "__main__":
    main()
