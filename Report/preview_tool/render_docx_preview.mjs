import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { chromium } from "playwright";

const require = createRequire(import.meta.url);

function usage() {
  console.error("Usage: node render_docx_preview.mjs <input.docx> <output_dir> [page_numbers_csv]");
  process.exit(1);
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function parseRequestedPages(raw) {
  if (!raw) return null;
  const pages = raw
    .split(",")
    .map((x) => Number.parseInt(x.trim(), 10))
    .filter((x) => Number.isInteger(x) && x > 0);
  return pages.length ? new Set(pages) : null;
}

const [, , inputPathArg, outputDirArg, pagesArg] = process.argv;

if (!inputPathArg || !outputDirArg) {
  usage();
}

const inputPath = path.resolve(inputPathArg);
const outputDir = path.resolve(outputDirArg);
const requestedPages = parseRequestedPages(pagesArg);

if (!fs.existsSync(inputPath)) {
  console.error(`Input not found: ${inputPath}`);
  process.exit(2);
}

ensureDir(outputDir);

const jszipPath = path.join(process.cwd(), "node_modules", "jszip", "dist", "jszip.min.js");
const docxPreviewPath = require.resolve("docx-preview");
const docxBytes = fs.readFileSync(inputPath);

const browser = await chromium.launch({ headless: true });

try {
  const page = await browser.newPage({
    viewport: { width: 1680, height: 1200 },
    deviceScaleFactor: 1.5,
  });

  await page.setContent(`
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          :root {
            color-scheme: light;
          }
          body {
            margin: 0;
            background: #d8d8d8;
            font-family: "WenQuanYi Zen Hei", "Noto Serif CJK SC", serif;
          }
          #container {
            padding: 24px 0 40px;
          }
        </style>
      </head>
      <body>
        <div id="container"></div>
      </body>
    </html>
  `);

  await page.addScriptTag({ path: jszipPath });
  await page.addScriptTag({ path: docxPreviewPath });

  await page.evaluate(async (arr) => {
    const container = document.getElementById("container");
    await window.docx.renderAsync(new Uint8Array(arr), container, null, {
      inWrapper: true,
      breakPages: true,
      ignoreLastRenderedPageBreak: false,
      useBase64URL: true,
      experimental: true,
    });
  }, Array.from(docxBytes));

  await page.waitForTimeout(2500);

  const pages = await page.locator("section.docx").all();
  const pageCount = pages.length;
  const rendered = [];

  for (let i = 0; i < pageCount; i += 1) {
    const pageNumber = i + 1;
    if (requestedPages && !requestedPages.has(pageNumber)) {
      continue;
    }

    const fileName = `page-${String(pageNumber).padStart(3, "0")}.png`;
    const filePath = path.join(outputDir, fileName);
    await pages[i].screenshot({ path: filePath });
    rendered.push(fileName);
  }

  fs.writeFileSync(
    path.join(outputDir, "manifest.json"),
    JSON.stringify(
      {
        input: inputPath,
        pages: pageCount,
        rendered,
      },
      null,
      2
    )
  );

  console.log(JSON.stringify({ input: inputPath, outputDir, pages: pageCount, rendered }, null, 2));
} finally {
  await browser.close();
}
