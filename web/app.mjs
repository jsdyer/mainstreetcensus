import {options, selection, compare} from "./model.mjs";

const one = id => document.getElementById(id);
const form = one("compare"), groups = one("industry"), periods = one("edition");
const stamp = one("feedback"), result = one("result"), aInput = one("area-a"), bInput = one("area-b");
const fmt = new Intl.NumberFormat("en-CA");
const loc = location.pathname;
const cache = new Map();
let archive, active, geo, choices, params = new URLSearchParams(location.search), request = 0;

function read(path) {
  if (!cache.has(path)) {
    cache.set(path, fetch("./data/" + path).then(res => {
      if (!res.ok) throw new Error("The saved table could not be loaded.");
      return res.json();
    }).catch(error => { cache.delete(path); throw error; }));
  }
  return cache.get(path);
}
function node(tag, text, cls) {
  const n = document.createElement(tag);
  if (text != null) n.textContent = text;
  if (cls) n.className = cls;
  return n;
}
function count(v) { return v == null ? "—" : fmt.format(v); }

function paint(record) {
  const header = node("p", record.label + " · NAICS " + record.code, "eyebrow");
  const els = [header, node("h2", record.industry), node("p", "Operating locations with employees", "unit")];
  const max = Math.max(...record.areas.map(a => a.values[0] || 0));
  for (const [i, area] of record.areas.entries()) {
    const row = node("div", null, "bar-row"), meta = node("div", null, "bar-meta"), track = node("div", null, "track");
    const bar = node("span", null, "bar b" + i);
    bar.style.width = (max ? 100*(area.values[0] || 0)/max : 0) + "%";
    meta.append(node("span",area.name), node("strong",count(area.values[0]))); track.append(bar);
    row.append(meta, track, node("small", area.boundary + " · " + area.code)); els.push(row);
  }
  const detail = node("details"), table = node("table"), head = table.createTHead().insertRow(), body = table.createTBody();
  for (const label of ["Employees per location", ...record.areas.map(a => a.name)]) {
    const cell = node("th",label); cell.scope = "col"; head.append(cell);
  }
  record.bands.forEach((label, i) => {
    const row = body.insertRow(), th = node("th", label.replace(" employees",""));
    th.scope = "row"; row.append(th);
    for (const area of record.areas) row.insertCell().textContent = count(area.values[i+1]);
  });
  detail.append(node("summary","See counts by employee-size band"), table, node("p","A dash means no published cell. Size bands count locations.","small"));
  result.replaceChildren(...els,detail);
}
function fail(message) {
  stamp.textContent = message;
  const tip = one("hint");
  if (form.hidden) {
    const note = node("p",message + " The saved comparison and profiles are available below.");
    result.before(note);
  } else {
    tip.textContent = "You can also browse the saved profiles below.";
  }
}
async function update(replaceURL = true) {
  const version = ++request;
  const a = choices.get(aInput.value.trim()), b = choices.get(bInput.value.trim());
  if (!a || !b) {
    stamp.textContent = "Choose a matching place from each list.";
    (!a ? aInput : bInput).focus(); return;
  }
  try {
    const industry = groups.value, edition = active;
    const rows = await read(edition.id + "/" + industry + ".json");
    if (version !== request) return;
    paint(compare(edition,geo,rows,industry,a,b));
    const target = new URLSearchParams({industry, a, b, edition:edition.id});
    if (replaceURL) history.replaceState(null,"",loc+"?"+target);
    const source = node("a", "View the "+edition.label+" source table");
    source.href = "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid="+edition.id+"01";
    one("edition-source").replaceChildren(source);
    stamp.textContent = "Showing " + edition.label + ".";
  } catch { if (version === request) fail("Could not load this industry. Try again."); }
}

async function choosePeriod(edition, values, updateURL) {
  const version = ++request;
  const nextGeo = await read(edition.id+"/geographies.json");
  if (version !== request) return;
  active = edition; geo = nextGeo;
  const opts = options(geo,active);
  choices = new Map(opts.map(o=>[o.label,o.code]));
  const byCode = new Map(opts.map(o=>[o.code,o.label]));
  const state = selection(values,active,geo);
  one("places").replaceChildren(...opts.map(o=>new Option(o.label,o.label)));
  groups.replaceChildren(...Object.entries(active.industries).sort((a,b)=>a[1].localeCompare(b[1])).map(([k,label])=>new Option(label+" ("+k+")",k)));
  groups.value = state.industry; periods.value = active.id;
  aInput.value = byCode.get(state.a); bInput.value = byCode.get(state.b);
  await update(updateURL);
}
async function start() {
  try {
    archive = await read("editions.json");
    periods.replaceChildren(...archive.editions.map(entry=>new Option(entry.label,entry.id)));
    const entry = archive.editions.find(item=>item.id===params.get("edition")) || archive.editions[0];
    await choosePeriod(entry,params,false);
    form.hidden = false;
  } catch { fail("The interactive comparison is unavailable."); }
}
periods.addEventListener("change",async() => {
  const values = new URLSearchParams({industry:groups.value, a:choices.get(aInput.value)||"",b:choices.get(bInput.value)||""});
  try { await choosePeriod(archive.editions.find(e=>e.id===periods.value), values, true); }
  catch { periods.value = active.id; fail("Could not load this edition. Try again."); }
});
form.addEventListener("submit",event => {event.preventDefault();update();});
form.addEventListener("reset",event => {
  event.preventDefault();
  choosePeriod(archive.editions[0],new URLSearchParams(),true).catch(()=>fail("Could not load the opening comparison."));
});
for (const input of [aInput,bInput]) input.addEventListener("focus", () => input.select());
start();
