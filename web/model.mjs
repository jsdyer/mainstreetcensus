export function areaName(code, geography, edition) {
  const name = geography[code][0];
  return code.length === 3 ? name + " metro area" : name + ", " + (edition.provinces[code.slice(0, 2)] || code.slice(0, 2));
}

export function options(geography, edition) {
  return Object.keys(geography).map(code => ({
    code, label: areaName(code, geography, edition) + " · " + code
  })).sort((a, b) => a.label.localeCompare(b.label, "en-CA"));
}

export function selection(params, edition, geography) {
  const preset = edition.comparisons[0];
  const group = params.get("industry");
  const a = params.get("a"), b = params.get("b");
  return {industry: Object.hasOwn(edition.industries, group) ? group : preset.industry,
    a: Object.hasOwn(geography, a) ? a : preset.a, b: Object.hasOwn(geography, b) ? b : preset.b};
}

export function compare(edition, geography, rows, industry, a, b) {
  return {label: edition.label, industry: edition.industries[industry], code: industry, bands: edition.bands.slice(1),
    areas: [a, b].map(code => ({code, name: areaName(code, geography, edition),
      boundary: code.length === 3 ? "Metro area" : "Census subdivision",
      values: rows[code] || Array(edition.bands.length).fill(null)}))};
}
