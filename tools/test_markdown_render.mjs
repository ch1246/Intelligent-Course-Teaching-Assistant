/**
 * renderMarkdown 行为验证：把 chat/index.vue 里的正则管线抽出来跑一遍。
 * 用 stub 替掉 t() 与 katex，只验证「结构转换」是否正确。
 */
const t = (k) => `[${k}]`;
const katex = { renderToString: (s, o) => `<span class="katex-stub">${o && o.displayMode ? "BLOCK" : "INLINE"}:${s}</span>` };

const renderMarkdown = (content) => {
  if (!content) return "";

  let html = content.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  const stash = [];
  const keep = (s) => {
    const key = `\uE000${stash.length}\uE000`;
    stash.push(s);
    return key;
  };
  const unescapeForMath = (s) => s.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");

  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_m, lang, code) => {
    const langLabel = lang || "text";
    return keep(
      `<div class="code-block-wrap" data-lang="${langLabel}"><div class="code-block-header"><span class="code-lang">${langLabel}</span></div><pre class="code-block"><code>${code.replace(/\n$/, "")}</code></pre></div>`
    );
  });

  html = html.replace(/\$\$([\s\S]+?)\$\$/g, (_m, tex) => {
    try {
      return keep(`<div class="latex-block">${katex.renderToString(unescapeForMath(tex.trim()), { throwOnError: false, displayMode: true, strict: false })}</div>`);
    } catch {
      return keep(`<div class="latex-block latex-error">$${tex}$</div>`);
    }
  });

  html = html.replace(/^#{6} (.+)$/gm, '<h6 class="md-heading md-h6">$1</h6>');
  html = html.replace(/^#{5} (.+)$/gm, '<h5 class="md-heading md-h5">$1</h5>');
  html = html.replace(/^#{4} (.+)$/gm, '<h4 class="md-heading md-h4">$1</h4>');
  html = html.replace(/^#{3} (.+)$/gm, '<h3 class="md-heading md-h3">$1</h3>');
  html = html.replace(/^#{2} (.+)$/gm, '<h2 class="md-heading md-h2">$1</h2>');
  html = html.replace(/^#{1} (.+)$/gm, '<h1 class="md-heading md-h1">$1</h1>');

  html = html.replace(/^[ \t]*(?:-{3,}|\*{3,}|_{3,})[ \t]*$/gm, keep('<hr class="md-hr">'));

  html = html.replace(/(?:^|\n)((?:\|[^\n]*\|[ \t]*(?:\n|$))+)/g, (_m, block) => {
    const rows = block.split("\n").filter((l) => l.trim());
    if (rows.length < 2) return block;
    const cellsOf = (line) =>
      line
        .trim()
        .replace(/^\|/, "")
        .replace(/\|$/, "")
        .split("|")
        .map((c) => c.trim());
    const sep = cellsOf(rows[1] ?? "");
    if (!sep.length || !sep.every((c) => /^:?-{2,}:?$/.test(c))) return block;
    const aligns = sep.map((c) => (c.startsWith(":") && c.endsWith(":") ? "center" : c.endsWith(":") ? "right" : "left"));
    const head = cellsOf(rows[0]).map((c, i) => `<th style="text-align:${aligns[i] ?? "left"}">${c}</th>`).join("");
    const body = rows
      .slice(2)
      .map((r) => `<tr>${cellsOf(r).map((c, i) => `<td style="text-align:${aligns[i] ?? "left"}">${c}</td>`).join("")}</tr>`)
      .join("");
    return keep(
      `<div class="md-table-wrap"><table class="md-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`
    );
  });

  html = html.replace(/(?:^|\n)((?:&gt;[^\n]*(?:\n|$))+)/g, (_m, block) => {
    const inner = block
      .split("\n")
      .map((l) => l.replace(/^&gt;[ ]?/, ""))
      .filter((l) => l.trim())
      .join("<br>");
    return keep(`<blockquote class="md-quote">${inner}</blockquote>`);
  });

  html = html.replace(/(?:^|\n)((?:[ \t]*[-*+][ \t]+[^\n]*(?:\n|$))+)/g, (_m, list) => {
    const items = list
      .split("\n")
      .filter((l) => /^[\t ]*[-*+]\s/.test(l))
      .map((l) => `<li>${l.replace(/^[\t ]*[-*+]\s/, "")}</li>`)
      .join("");
    return `<ul class="md-list">${items}</ul>`;
  });

  html = html.replace(/(?:^|\n)((?:[ \t]*\d+\.[ \t]+[^\n]*(?:\n|$))+)/g, (_m, list) => {
    const items = list
      .split("\n")
      .filter((l) => /^[\t ]*\d+\.\s/.test(l))
      .map((l) => `<li>${l.replace(/^[\t ]*\d+\.\s/, "")}</li>`)
      .join("");
    return `<ol class="md-list">${items}</ol>`;
  });

  html = html.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>');
  html = html.replace(/\*\*([^*]+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/(^|[^*\w])\*([^*\n]+?)\*(?![*\w])/g, "$1<em>$2</em>");
  html = html.replace(/~~([^~\n]+?)~~/g, "<del>$1</del>");
  html = html.replace(
    /\[([^\]\n]+?)\]\((https?:\/\/[^)\s]+?)\)/g,
    '<a class="md-link" href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
  );

  html = html.replace(/(?<!\$)\$(?!\$)((?:[^$\\]|\\.)+?)\$(?!\d)/g, (_m, tex) => {
    try {
      return keep(`<span class="latex-inline">${katex.renderToString(unescapeForMath(tex.trim()), { throwOnError: false, strict: false })}</span>`);
    } catch {
      return keep(`<span class="latex-inline">$${tex}$</span>`);
    }
  });

  html = html.replace(/\n/g, "<br>");
  html = html.replace(/\uE000(\d+)\uE000/g, (_m, i) => stash[Number(i)] ?? "");
  return html;
};

const cases = [
  ["标题在中间（原 bug：不生效）", "前言一段\n\n## 二级标题\n\n正文", ["<h2", "二级标题"], ["## 二级标题"]],
  ["多级标题", "# H1\n## H2\n### H3\n#### H4", ["md-h1", "md-h2", "md-h3", "md-h4"], ["# H1"]],
  ["表格", "| 阶段 | 耗时 |\n|---|---|\n| 检索 | 1ms |", ["md-table", "<th", "<td", "检索"], []],
  ["表格对齐", "| a | b |\n|:---|---:|\n| 1 | 2 |", ['text-align:left', 'text-align:right'], []],
  ["引用块", "> 第一行\n> 第二行", ["md-quote", "第一行", "第二行"], []],
  ["分隔线", "上\n\n---\n\n下", ["md-hr"], ["---"]],
  ["代码块不被内联规则破坏", "```js\nconst a = **not bold**;\n```", ["code-block-wrap", "**not bold**"], ["<strong>"]],
  ["块级公式", "x\n\n$$a < b$$\n", ["latex-block", "BLOCK:a < b"], []],
  ["行内公式", "结果是 $a<b$ 好", ["latex-inline", "INLINE:a<b"], []],
  ["粗体斜体链接", "**粗** *斜* [链接](https://a.com)", ["<strong>粗</strong>", "<em>斜</em>", 'href="https://a.com"'], []],
  ["行内代码", "用 `code` 试试", ['<code class="inline-code">code</code>'], []],
  ["HTML 转义", "<script>alert(1)</script>", ["&lt;script&gt;"], ["<script>"]],
  ["删除线", "~~划掉~~", ["<del>划掉</del>"], []],
  ["有序无序列表", "- a\n- b\n\n1. x\n2. y", ["<ul class=\"md-list\">", "<ol class=\"md-list\">"], []],
];

let pass = 0;
let fail = 0;
for (const [name, input, mustHave, mustNotHave] of cases) {
  const out = renderMarkdown(input);
  const missing = mustHave.filter((s) => !out.includes(s));
  const leaked = mustNotHave.filter((s) => out.includes(s));
  const ok = missing.length === 0 && leaked.length === 0;
  if (ok) pass++;
  else fail++;
  console.log(`  [${ok ? "OK " : "FAIL"}] ${name}`);
  if (missing.length) console.log("        missing:", JSON.stringify(missing));
  if (leaked.length) console.log("        leaked :", JSON.stringify(leaked));
  if (!ok) console.log("        output  :", out.slice(0, 300));
}
console.log(`\nPASS=${pass} FAIL=${fail}`);
process.exit(fail ? 1 : 0);
