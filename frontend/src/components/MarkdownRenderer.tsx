import React, { Fragment } from 'react';
import ReactMarkdown, { Components } from 'react-markdown';
import { InlineMath, BlockMath } from 'react-katex';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import 'katex/dist/katex.min.css';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

/**
 * Normalise LLM outputs that use markdown definition-list syntax.
 * Lines starting with `': '` (the definition) are collapsed back onto the
 * preceding non-empty line so they render as normal inline text instead of
 * disconnected `<dd>` blocks.
 *
 * Example input:  "CustomerID\n: str"  → output: "CustomerID: str"
 */
function normalizeDefinitionLists(text: string): string {
  const lines = text.split('\n');
  const result: string[] = [];
  let inCodeBlock = false;

  for (const line of lines) {
    if (line.trimStart().startsWith('```')) {
      inCodeBlock = !inCodeBlock;
      result.push(line);
      continue;
    }

    if (!inCodeBlock && /^[ \t]*:[ \t]+\S/.test(line)) {
      // Definition list item — join it to the previous non-empty line
      const definition = line.replace(/^[ \t]*:[ \t]+/, '').trim();
      const prevIdx = result.length - 1;
      if (prevIdx >= 0 && result[prevIdx].trim() !== '') {
        result[prevIdx] = result[prevIdx].trimEnd() + ': ' + definition;
      } else {
        result.push(definition);
      }
    } else {
      result.push(line);
    }
  }

  return result.join('\n');
}

// Parse content to extract math and non-math parts
const parseContent = (text: string): Array<{ type: 'math' | 'block-math' | 'text'; content: string }> => {
  const parts = [];
  let remaining = text;

  // Regex patterns for both LaTeX and dollar delimiters
  // Block math: $$...$$ or \[...\]
  // Inline math: $...$ or \(...\)

  // We'll process in order: first block math (both types), then inline math (both types)
  const blockMathRegex = /(\$\$([\s\S]*?)\$\$|\\\[([\s\S]*?)\\\])/g;
  const inlineMathDollarRegex = /\$([^\$\n]+?)\$/g;
  const inlineMathLatexRegex = /\\\(([^\)]+?)\\\)/g;

  let lastIndex = 0;
  let match;
  const matches = [];

  // Find all block math matches
  while ((match = blockMathRegex.exec(remaining)) !== null) {
    matches.push({
      start: match.index,
      end: match.index + match[0].length,
      content: match[2] || match[3], // Either $$...$$ or \[...\]
      type: 'block-math',
    });
  }

  // Process matches and text between them
  if (matches.length > 0) {
    let textIndex = 0;
    for (const m of matches) {
      if (m.start > textIndex) {
        const textPart = remaining.substring(textIndex, m.start);
        parseInlineMath(textPart, parts);
      }
      parts.push({ type: 'block-math', content: m.content });
      textIndex = m.end;
    }
    if (textIndex < remaining.length) {
      const textPart = remaining.substring(textIndex);
      parseInlineMath(textPart, parts);
    }
  } else {
    parseInlineMath(remaining, parts);
  }

  return parts;
};

const parseInlineMath = (text: string, parts: Array<{ type: string; content: string }>) => {
  const combined: Array<{ pos: number; end: number; content: string; type: 'math' | 'text' }> = [];

  // Find all $ delimited math
  const dollarRegex = /\$([^\$\n]+?)\$/g;
  let match;
  while ((match = dollarRegex.exec(text)) !== null) {
    combined.push({
      pos: match.index,
      end: match.index + match[0].length,
      content: match[1],
      type: 'math',
    });
  }

  // Find all \(...\) delimited math
  const latexRegex = /\\\(([^\)]+?)\\\)/g;
  while ((match = latexRegex.exec(text)) !== null) {
    combined.push({
      pos: match.index,
      end: match.index + match[0].length,
      content: match[1],
      type: 'math',
    });
  }

  if (combined.length === 0) {
    parts.push({ type: 'text', content: text });
    return;
  }

  // Sort by position
  combined.sort((a, b) => a.pos - b.pos);

  let lastIndex = 0;
  for (const item of combined) {
    if (item.pos > lastIndex) {
      parts.push({ type: 'text', content: text.substring(lastIndex, item.pos) });
    }
    parts.push({ type: 'math', content: item.content });
    lastIndex = item.end;
  }

  if (lastIndex < text.length) {
    parts.push({ type: 'text', content: text.substring(lastIndex) });
  }
};

// Custom components for markdown rendering
const markdownComponents: Components = {
  code({ node, inline, className, children, ...props }: any) {
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : 'text';
    const childText = String(children);
    const isCodeBlock = Boolean(match) || childText.includes('\n');

    if (isCodeBlock) {
      return (
        <div className="my-2 rounded-lg overflow-x-auto bg-gray-900 border border-gray-700">
          <SyntaxHighlighter
            style={vscDarkPlus}
            language={language}
            PreTag="div"
            {...props}
          >
            {childText.replace(/\n$/, '')}
          </SyntaxHighlighter>
        </div>
      );
    }

    // Always render inline code with a light background regardless of the
    // `inline` flag — some markdown parsers set it to false for code inside
    // list items or definition lists.
    return (
      <code
        className={`bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono text-gray-800 ${className || ''}`}
        {...props}
      >
        {children}
      </code>
    );
  },

  h1: ({ node, ...props }: any) => (
    <h1 className="text-2xl font-bold mt-4 mb-2 text-gray-800" {...props} />
  ),
  h2: ({ node, ...props }: any) => (
    <h2 className="text-xl font-bold mt-3 mb-2 text-gray-800" {...props} />
  ),
  h3: ({ node, ...props }: any) => (
    <h3 className="text-lg font-bold mt-2 mb-1 text-gray-800" {...props} />
  ),
  h4: ({ node, ...props }: any) => (
    <h4 className="text-base font-bold mt-2 mb-1 text-gray-800" {...props} />
  ),

  p: ({ node, ...props }: any) => (
    <p className="mb-2 text-gray-700 leading-relaxed" {...props} />
  ),

  ul: ({ node, ...props }: any) => (
    <ul className="list-disc list-inside mb-2 text-gray-700 ml-2" {...props} />
  ),
  ol: ({ node, ...props }: any) => (
    <ol className="list-decimal list-inside mb-2 text-gray-700 ml-2" {...props} />
  ),
  li: ({ node, ...props }: any) => (
    <li className="mb-1 ml-2" {...props} />
  ),

  blockquote: ({ node, ...props }: any) => (
    <blockquote className="border-l-4 border-blue-500 pl-4 py-2 my-2 bg-blue-50 italic text-gray-700" {...props} />
  ),

  a: ({ node, href, ...props }: any) => (
    <a
      href={href}
      className="text-blue-600 hover:underline"
      target="_blank"
      rel="noopener noreferrer"
      {...props}
    />
  ),

  table: ({ node, ...props }: any) => (
    <div className="overflow-x-auto my-2">
      <table className="border-collapse border border-gray-300 w-full" {...props} />
    </div>
  ),
  thead: ({ node, ...props }: any) => (
    <thead className="bg-gray-100" {...props} />
  ),
  tbody: ({ node, ...props }: any) => (
    <tbody {...props} />
  ),
  tr: ({ node, ...props }: any) => (
    <tr className="border border-gray-300" {...props} />
  ),
  td: ({ node, ...props }: any) => (
    <td className="border border-gray-300 px-3 py-2" {...props} />
  ),
  th: ({ node, ...props }: any) => (
    <th className="border border-gray-300 px-3 py-2 font-bold text-left" {...props} />
  ),

  strong: ({ node, ...props }: any) => (
    <strong className="font-bold" {...props} />
  ),
  em: ({ node, ...props }: any) => (
    <em className="italic" {...props} />
  ),

  hr: ({ node, ...props }: any) => (
    <hr className="my-4 border-t border-gray-300" {...props} />
  ),

  // Definition list elements — rendered cleanly instead of as disconnected blocks.
  dl: ({ node, ...props }: any) => (
    <dl className="mb-2 text-gray-700" {...props} />
  ),
  dt: ({ node, ...props }: any) => (
    <dt className="font-semibold inline" {...props} />
  ),
  dd: ({ node, ...props }: any) => (
    <dd className="inline ml-1 text-gray-600 after:content-['\\A'] after:whitespace-pre" {...props} />
  ),

  inlineCode: ({ node, ...props }: any) => (
    <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono" {...props} />
  ),
};

// Render a single part (text, inline math, or block math)
const renderPart = (part: { type: string; content: string }, index: number) => {
  if (part.type === 'math') {
    return (
      <span key={index} className="inline-math">
        <InlineMath math={part.content} errorColor="#cc0000" />
      </span>
    );
  } else if (part.type === 'block-math') {
    return (
      <div key={index} className="block-math my-2 flex justify-center">
        <BlockMath math={part.content} errorColor="#cc0000" />
      </div>
    );
  } else {
    // For text parts, check if they contain markdown (headings, lists, code blocks, etc.)
    const hasMarkdown = /^#+\s|^\s*[-*]\s|^```|^\d+\.\s|^>|^\|/m.test(part.content.trim());
    
    if (hasMarkdown) {
      // Render with markdown processor for formatted content
      return (
        <div key={index} className="text-content">
          <ReactMarkdown components={markdownComponents}>
            {part.content}
          </ReactMarkdown>
        </div>
      );
    } else {
      // Render as plain text with reduced spacing
      const lines = part.content.split('\n').filter(line => line.trim());
      return (
        <div key={index} className="text-content">
          {lines.map((line, i) => (
            <p key={i} className={`text-gray-700 leading-relaxed ${i > 0 ? 'mt-0' : 'mb-2'}`}>
              {line}
            </p>
          ))}
        </div>
      );
    }
  }
};

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  className = '',
}) => {
  try {
    // Normalise definition-list syntax before parsing so `: value` lines
    // don't render as disconnected blocks.
    const normalizedContent = normalizeDefinitionLists(content);
    let parts = parseContent(normalizedContent);
    
    // Merge adjacent text parts to reduce excessive spacing
    const mergedParts: Array<{ type: string; content: string }> = [];
    for (const part of parts) {
      const lastPart = mergedParts[mergedParts.length - 1];
      if (lastPart && lastPart.type === 'text' && part.type === 'text') {
        // Merge consecutive text parts
        lastPart.content += part.content;
      } else {
        mergedParts.push(part);
      }
    }
    
    return (
      <div className={`prose prose-sm max-w-none ${className}`}>
        {mergedParts.map((part, index) => renderPart(part, index))}
      </div>
    );
  } catch (error) {
    console.error('[MarkdownRenderer] Error rendering content:', error);
    // Fallback: render as plain text
    return (
      <div className={`prose prose-sm max-w-none ${className}`}>
        <p className="text-gray-700 whitespace-pre-wrap">{content}</p>
      </div>
    );
  }
};

export default MarkdownRenderer;
