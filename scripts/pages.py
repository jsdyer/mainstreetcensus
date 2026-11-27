"""Make dated area, industry and comparison pages from one saved official edition."""
from html import escape
import json
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

from search_metadata import add_search_metadata


def e(value):
    return escape(str(value), quote=True)


def area_name(area, geo, edition):
    name = geo[area][0]
    return f"{name} metro area" if len(area)==3 else f"{name}, {edition['provinces'].get(area[:2],area[:2])}"


def place_tag(area):
    return "Metro area" if len(area)==3 else "Census subdivision"


def amount(value):
    return "—" if value is None else f"{value:,}"


def series(rows, area, entry):
    return rows.get(area, [None]*len(entry["bands"]))


def anchor(url, label):
    return f'<a href="{e(url)}">{e(label)}</a>'


def compare_url(prefix, entry, code, a, b):
    return prefix+"?"+urlencode({"industry":code,"a":a,"b":b,"edition":entry["id"]})


def chart(entry, code, geo, rows, a, b):
    names = [area_name(k,geo,entry) for k in (a,b)]
    values = [series(rows,k,entry) for k in (a,b)]
    maximum = max((v[0] or 0 for v in values),default=0)
    bars = ""
    for pos,(area,name,vals) in enumerate(zip((a,b),names,values)):
        count = vals[0]
        width = round(100*(count or 0)/maximum,2) if maximum else 0
        bars += (f'<div class="bar-row"><div class="bar-meta"><span>{e(name)}</span><strong>{amount(count)}</strong></div>'
                 f'<div class="track"><span class="bar b{pos}" style="width:{width}%"></span></div>'
                 f'<small>{place_tag(area)} · {area}</small></div>')
    body = "".join(f'<tr><th scope="row">{e(band.replace(" employees",""))}</th><td>{amount(values[0][i])}</td><td>{amount(values[1][i])}</td></tr>'
                   for i,band in enumerate(entry["bands"][1:],1))
    return (f'<p class="eyebrow">{e(entry["label"])} · NAICS {code}</p><h2>{e(entry["industries"][code])}</h2>'
            '<p class="unit">Operating locations with employees</p>'+bars+
            '<details><summary>See counts by employee-size band</summary><table><thead><tr><th>Employees per location</th>'
            +''.join('<th scope="col">'+e(n)+'</th>' for n in names)+'</tr></thead><tbody>'+body+
            '</tbody></table><p class="small">A dash means no published cell. Size bands count locations.</p></details>')


def source_note(entry):
    url="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid="+entry["id"]+"01"
    return ('<section class="notes"><h2>Reading this edition</h2><p>A chain with several stores can contribute several locations. '
            'Businesses without employees are outside this table. Metro areas include their constituent municipalities, so the two boundaries can overlap. '
            'A dash marks a missing published cell.</p><p>Statistics Canada advises against treating successive editions as a time series. '
            'Classification and register changes can affect the counts.</p><p>'
            +anchor(url,"Statistics Canada · "+entry["title"])+' · Released '+e(entry["release"])+'</p></section>')


def write_pages(stage, tool, template):
    data=stage/"data"
    archive=json.loads((data/"editions.json").read_text())
    entry=archive["editions"][0]
    base=data/entry["id"]
    geo=json.loads((base/"geographies.json").read_text())
    groups={code:json.loads((base/(code+".json")).read_text()) for code in entry["industries"]}
    featured=sorted({k for k in geo if len(k)==3} | (set(entry["featured_areas"]) & geo.keys()),key=lambda a:area_name(a,geo,entry))
    comp=entry["comparisons"]; default=comp[0]
    canonical="https://coolcode.ca"+tool["url"]
    source_url="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid="+entry["id"]+"01"
    dataset={"@type":"Dataset","@id":source_url+"#dataset","name":entry["title"],"url":source_url,
             "creator":{"@type":"Organization","name":"Statistics Canada"},"datePublished":entry["release"],
             "license":"https://www.statcan.gc.ca/en/reference/licence"}
    site_root=tool["id"]!="coolcode-tool-template" and tool["source"]=="https://github.com/jsdyer/"+tool["id"]
    paths=[]
    def save(route,title,desc,body):
        prefix="../"*route.count("/") or "./"
        p=stage/route
        p.mkdir(parents=True,exist_ok=True)
        text=template
        values={"PREFIX":prefix, "TITLE":e(title), "TOOL":e(tool["title"]), "DESCRIPTION":e(desc), "BODY":body,
                "SCRIPT":'<script type="module" src="./app.mjs"></script>' if not route else "",
                "SOURCE":e(tool["source"]), "ID":e(tool["id"]), "METRICS":'<script defer src="/assets/tool-metrics.js" referrerpolicy="no-referrer"></script>' if site_root else "",
                "ISSUE":anchor("https://coolcode.ca/report/?tool="+tool["id"],"Report an issue") if site_root else ""}
        for key,value in values.items():
            text=text.replace("{{"+key+"}}",value)
        if "{{" in text: raise ValueError("Unresolved build token")
        text=add_search_metadata(text,dict(tool,title=title,description=desc,url=tool["url"]+route),
                                 category="BusinessApplication",datasets=[dataset])
        (p/"index.html").write_text(text,encoding="utf-8")
        if route: paths.append(canonical+route)
    def links(items):
        return '<ul class="directory">'+''.join('<li>'+anchor(href,name)+'</li>' for href,name in items)+'</ul>'
    controls=('<form id="compare" hidden><div class="form-head"><h2>Compare two places</h2><button type="reset" class="quiet">Use Langley example</button></div>'
              '<div class="fields"><label for="industry">Industry<select id="industry"></select></label>'
              '<label for="edition">Source edition<select id="edition"></select></label>'
              '<label for="area-a">First place<input id="area-a" list="places" required autocomplete="off"></label>'
              '<label for="area-b">Second place<input id="area-b" list="places" required autocomplete="off"></label></div>'
              '<datalist id="places"></datalist><p id="hint" class="small">Type a municipality or metro area and choose a matching boundary.</p>'
              '<button>Compare locations</button> <span id="feedback" role="status"></span></form>')
    body=('<section class="intro"><p class="eyebrow">Canadian Business Counts</p><h1>Where are the businesses?</h1>'
          '<p>Choose an industry and two places to compare how many locations have employees. Start with restaurants in the two Langleys.</p></section>'
          +controls+'<section class="comparison" id="result" aria-label="Comparison result">'+
          chart(entry,default["industry"],geo,groups[default["industry"]],default["a"],default["b"])+
          '</section><p id="edition-source" class="small">'+anchor(source_url,"View the "+entry["label"]+" source table")+'</p>'
          '<section><h2>Explore local results</h2>'+links([("records/"+c["slug"]+"/",c["name"]) for c in comp]+[("records/","All industry and place profiles")])+'</section>'
          +source_note(entry))
    save("", "Compare Canadian business locations by industry and place",tool["description"],body)
    for c in comp:
        a,b,code=c["a"],c["b"],c["industry"]
        counts=groups[code]
        desc=(f'{entry["label"]} employer-location counts: {area_name(a,geo,entry)} had {amount(counts[a][0])} '
              f'and {area_name(b,geo,entry)} had {amount(counts[b][0])} in {entry["industries"][code].lower()}.')
        body=(f'<p class="eyebrow">Boundary comparison</p><h1>{e(c["name"])}</h1><p>{e(c["context"])}</p>'
              '<section class="comparison">'+chart(entry,code,geo,counts,a,b)+'</section><p>'
              +anchor(compare_url("../../",entry,code,a,b),"Change this comparison")+' · '
              +anchor("../industry-"+code+"/","Explore this industry across Canada")+'</p>')
        if c["slug"]=="langley-restaurant-locations":
            body+='<p>'+anchor("https://coolcode.ca/field-notes/counting-restaurant-locations-in-langley/", "Field note: counting restaurant locations in the two Langleys")+'</p>'
        if a.startswith("59"):
            body+='<p>'+anchor("https://coolcode.ca/langleytrades/","Look up named Township of Langley business licences")+'</p>'
        if a=="1209034":
            body+='<p>'+anchor("https://coolcode.ca/metroeconomy/cities/205/","Explore Halifax metro employment estimates")+'</p>'
        save("records/"+c["slug"]+"/",c["name"],desc,body+source_note(entry))
    for code,records in groups.items():
        title=entry["industries"][code]+" in Canadian communities"
        desc=f'Compare {entry["label"]} employer-location counts for {entry["industries"][code].lower()} across Canadian metro areas and selected municipalities.'
        lines=[]
        for a in featured:
            value=series(records,a,entry)[0]
            lines.append('<tr><th scope="row">'+anchor("../area-"+a+"/",area_name(a,geo,entry))+'</th><td>'+amount(value)+'</td><td>'+
                         anchor(compare_url("../../",entry,code,a,default["a"] if a!=default["a"] else default["b"]),"Compare")+'</td></tr>')
        benchmark = (anchor("https://coolcode.ca/businessbench/records/7225/","See restaurant revenue, expenses and profit in Business Bench")
                     if code == "7225" else anchor("https://coolcode.ca/businessbench/","Compare published industry revenues and expenses in Business Bench"))
        body=(f'<p class="eyebrow">Industry profile · NAICS {code}</p><h1>{e(title)}</h1><p>{e(desc)} '
              'Use Compare beside any location to change either boundary.</p><table><thead><tr><th>Boundary</th><th>Locations</th><th>Explore</th></tr></thead><tbody>'
              +''.join(lines)+'</tbody></table><p>'+benchmark+'</p>'+source_note(entry))
        save(f"records/industry-{code}/",title,desc,body)
    for a in featured:
        name=area_name(a,geo,entry); title=f"Business locations in {name}"
        desc=f'See how many locations with employees Statistics Canada counted in {name} in {entry["label"]} across {len(groups)} selected industries.'
        lines=[]
        for code in sorted(groups,key=lambda k:entry["industries"][k]):
            lines.append('<tr><th scope="row">'+anchor("../industry-"+code+"/",entry["industries"][code])+'</th><td>'+amount(series(groups[code],a,entry)[0])+'</td><td>'+
                         anchor(compare_url("../../",entry,code,a,default["a"] if a!=default["a"] else default["b"]),"Compare")+'</td></tr>')
        body=(f'<p class="eyebrow">{place_tag(a)} · {a}</p><h1>{e(title)}</h1><p>{e(desc)} '
              'This list covers selected industries only.</p><table><thead><tr><th>Industry</th><th>Locations</th><th>Explore</th></tr></thead><tbody>'
              +''.join(lines)+'</tbody></table>')
        if len(a)==3:
            body+='<p>'+anchor("https://coolcode.ca/metroeconomy/","Explore Canadian metro employment estimates")+'</p>'
        save("records/area-"+a+"/",title,desc,body+source_note(entry))
    desc=f'Browse Canadian employer counts for {entry["label"]}, with linked municipality, metro area and industry comparisons.'
    body=('<p class="eyebrow">Result directory</p><h1>Canadian employer locations by place and industry</h1><p>'+e(desc)+
          '</p><h2>Boundary comparisons</h2>'+links([(c["slug"]+"/",c["name"]) for c in comp])+
          '<h2>Industries</h2>'+links([("industry-"+k+"/",f'{v} · {k}') for k,v in sorted(entry["industries"].items(),key=lambda kv:kv[1])])+
          f'<h2>Places</h2><p>These profiles cover every published metro area and selected municipalities. The '
          +anchor("../","interactive comparison")+f' includes all {len(geo):,} areas in this edition.</p>'+
          links([("area-"+a+"/",area_name(a,geo,entry)) for a in featured])+source_note(entry))
    save("records/","Canadian employer locations by place and industry",desc,body)
    xml=ET.Element("urlset",xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for path in sorted(paths):
        ET.SubElement(ET.SubElement(xml,"url"),"loc").text=path
    (stage/"sitemap.xml").write_bytes(ET.tostring(xml,encoding="utf-8",xml_declaration=True))
    status={"checked_at":archive["checked_at"],"edition":entry["label"],"source_release":entry["release"],"geographies":len(geo),
            "industry_groups":len(groups),"result_pages":len(paths),"table":source_url}
    (stage/"data/status.json").write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n")
