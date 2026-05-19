const ALLOWED_ELEMENTS = new Set(["symbol", "path", "circle", "rect", "line", "polyline", "polygon", "ellipse", "g"]);
const ALLOWED_ATTRIBUTES = new Set([
  "id",
  "viewBox",
  "d",
  "x",
  "y",
  "x1",
  "y1",
  "x2",
  "y2",
  "cx",
  "cy",
  "r",
  "rx",
  "ry",
  "width",
  "height",
  "points",
  "transform"
]);

export function sanitizeSvgIconLibrary(svgText: string): string {
  const doc = new DOMParser().parseFromString(svgText, "image/svg+xml");
  if (doc.querySelector("parsererror")) {
    throw new Error("Playbook staging icon library is not valid SVG");
  }

  const symbols = [...doc.querySelectorAll("symbol")]
    .map((symbol) => serializeElement(symbol))
    .filter((symbol): symbol is string => Boolean(symbol));
  return `<defs>${symbols.join("")}</defs>`;
}

function serializeElement(element: Element): string | null {
  const tagName = element.tagName;
  if (!ALLOWED_ELEMENTS.has(tagName)) {
    return null;
  }
  if (tagName === "symbol" && !validIconId(element.getAttribute("id"))) {
    return null;
  }

  const attributes = [...element.attributes]
    .filter((attribute) => ALLOWED_ATTRIBUTES.has(attribute.name))
    .map((attribute) => ` ${attribute.name}="${escapeAttribute(attribute.value)}"`)
    .join("");
  const children = [...element.children]
    .map((child) => serializeElement(child))
    .filter((child): child is string => Boolean(child))
    .join("");
  return `<${tagName}${attributes}>${children}</${tagName}>`;
}

function validIconId(value: string | null): boolean {
  return value !== null && /^stage-icon-[a-z0-9-]+$/.test(value);
}

function escapeAttribute(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}
