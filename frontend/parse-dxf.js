const DxfParser = require("dxf-parser");
const fs = require("fs");

const content = fs.readFileSync(process.argv[2], "utf8");
const parser = new DxfParser();
const dxf = parser.parse(content);

console.log("=== INSERT ENTITIES (Block placements) ===");
const inserts = dxf.entities.filter(e => e.type === "INSERT");

// Group by block name
const byBlock = {};
inserts.forEach(ins => {
  byBlock[ins.name] = byBlock[ins.name] || [];
  byBlock[ins.name].push(ins);
});

// Show top block types and their positions
Object.entries(byBlock)
  .sort((a,b) => b[1].length - a[1].length)
  .slice(0, 10)
  .forEach(([name, instances]) => {
    console.log("\nBlock \"" + name + "\" - " + instances.length + " instances:");
    instances.slice(0, 5).forEach((ins, i) => {
      let info = "  " + (i+1) + ": X=" + ins.position.x.toFixed(2) + ", Y=" + ins.position.y.toFixed(2);
      if (ins.rotation) info += ", Rot=" + ins.rotation.toFixed(1) + "°";
      console.log(info);
    });
    if (instances.length > 5) console.log("  ... and " + (instances.length - 5) + " more");
  });

console.log("\n=== TEXT LABELS ===");
const texts = dxf.entities.filter(e => e.type === "TEXT" || e.type === "MTEXT");
texts.slice(0, 15).forEach(t => {
  const text = (t.text || t.string || "").replace(/\\P/g, " ").replace(/\\[^;]*;/g, "");
  if (text.length > 0 && text.length < 80) {
    const pos = t.position || t.startPoint;
    console.log("  \"" + text.trim() + "\"");
  }
});
