import test from "node:test";
import assert from "node:assert/strict";
import {options,selection,compare} from "../web/model.mjs";
const e={label:"June test",industries:{7225:"Restaurants",5415:"Software"},provinces:{12:"NS"},comparisons:[{industry:"7225",a:"205",b:"1209034"}],bands:["Total","1 to 4 employees"]};
const geo={"205":["Halifax","metro"],"1209034":["Halifax","municipality"],"1209999":["Test place","municipality"]};
test("duplicate names stay selectable by boundary and code",()=>{
 const list=options(geo,e);assert.equal(new Set(list.map(r=>r.label)).size,3);
 assert.match(list.find(r=>r.code==="205").label,/metro area/);
});
test("shared comparison accepts an extra geography and industry",()=>{
 const params=new URLSearchParams({industry:"5415",a:"1209999",b:"205"});
 assert.deepEqual(selection(params,e,geo),{industry:"5415",a:"1209999",b:"205"});
 assert.deepEqual(selection(new URLSearchParams({industry:"__proto__",a:"invalid"}),e,geo),{industry:"7225",a:"205",b:"1209034"});
});
test("missing counts are distinct from a published zero",()=>{
 const r=compare(e,geo,{"205":[3,0]},"7225","205","1209999");
 assert.equal(r.areas[0].values[1],0);assert.equal(r.areas[1].values[1],null);
 assert.equal(r.areas[0].boundary,"Metro area");
});
