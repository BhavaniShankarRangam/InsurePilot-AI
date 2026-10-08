"use client";

import * as React from "react";

/**
 * Minimal, XSS-safe markdown renderer for assistant answers (no raw HTML).
 * Supports paragraphs, bullet lists, blockquotes, **bold**, _italic_/*italic* and [n] citation markers.
 */
export function Markdown({ text, onCite }: { text: string; onCite?: (n: number) => void }) {
  const blocks = React.useMemo(() => parseBlocks(text), [text]);
  return (
    <div className="prose-ai text-[15px] text-fg">
      {blocks.map((b, i) => {
        if (b.kind === "ul")
          return (
            <ul key={i}>
              {b.items.map((it, j) => (
                <li key={j}>{inline(it, onCite)}</li>
              ))}
            </ul>
          );
        if (b.kind === "quote") return <blockquote key={i}>{inline(b.text, onCite)}</blockquote>;
        return <p key={i}>{inline(b.text, onCite)}</p>;
      })}
    </div>
  );
}

type Block = { kind: "p"; text: string } | { kind: "ul"; items: string[] } | { kind: "quote"; text: string };

function parseBlocks(text: string): Block[] {
  const lines = text.split("\n");
  const out: Block[] = [];
  let para: string[] = [];
  const flush = () => {
    if (para.length) out.push({ kind: "p", text: para.join(" ") });
    para = [];
  };
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      flush();
      continue;
    }
    const li = line.match(/^\s*[-•*]\s+(.*)$/);
    if (li) {
      flush();
      const last = out[out.length - 1];
      if (last?.kind === "ul") last.items.push(li[1]);
      else out.push({ kind: "ul", items: [li[1]] });
      continue;
    }
    const q = line.match(/^>\s?(.*)$/);
    if (q) {
      flush();
      out.push({ kind: "quote", text: q[1] });
      continue;
    }
    para.push(line);
  }
  flush();
  return out;
}

function inline(text: string, onCite?: (n: number) => void): React.ReactNode[] {
  const tokens = text.split(/(\*\*[^*]+\*\*|\[\d+\]|_[^_]+_|\*[^*]+\*)/g).filter(Boolean);
  return tokens.map((t, i) => {
    if (t.startsWith("**") && t.endsWith("**")) return <strong key={i}>{t.slice(2, -2)}</strong>;
    const cite = t.match(/^\[(\d+)\]$/);
    if (cite)
      return (
        <button
          key={i}
          type="button"
          onClick={() => onCite?.(Number(cite[1]))}
          className="mx-0.5 inline-flex h-4 min-w-4 -translate-y-1 items-center justify-center rounded-md bg-accent-soft px-1 text-[10px] font-semibold text-accent hover:brightness-125"
          aria-label={`Source ${cite[1]}`}
        >
          {cite[1]}
        </button>
      );
    if ((t.startsWith("_") && t.endsWith("_")) || (t.startsWith("*") && t.endsWith("*") && t.length > 2)) return <em key={i}>{t.slice(1, -1)}</em>;
    return <React.Fragment key={i}>{t}</React.Fragment>;
  });
}
