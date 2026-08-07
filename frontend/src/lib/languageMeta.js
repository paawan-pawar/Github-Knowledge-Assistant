// Mirrors backend/app/services/chunker.py LANGUAGE_BY_EXT values, plus a
// short display label. Kept intentionally simple -- this only drives labels
// and syntax-highlighter language ids in the UI.
export const LANGUAGE_LABELS = {
  python: "Python",
  javascript: "JavaScript",
  typescript: "TypeScript",
  java: "Java",
  kotlin: "Kotlin",
  go: "Go",
  rust: "Rust",
  ruby: "Ruby",
  php: "PHP",
  c: "C",
  cpp: "C++",
  csharp: "C#",
  swift: "Swift",
  objectivec: "Objective-C",
  scala: "Scala",
  sql: "SQL",
  bash: "Shell",
  yaml: "YAML",
  json: "JSON",
  toml: "TOML",
  markdown: "Markdown",
  html: "HTML",
  css: "CSS",
  scss: "SCSS",
  vue: "Vue",
  svelte: "Svelte",
  dockerfile: "Dockerfile",
  protobuf: "Protocol Buffers",
  graphql: "GraphQL",
  r: "R",
  julia: "Julia",
  elixir: "Elixir",
  text: "Text",
};

export function languageLabel(lang) {
  return LANGUAGE_LABELS[lang] || lang || "Text";
}

// react-syntax-highlighter uses its own (mostly overlapping) language ids.
const HIGHLIGHTER_OVERRIDES = {
  csharp: "csharp",
  cpp: "cpp",
  objectivec: "objectivec",
  dockerfile: "docker",
};

export function highlighterLanguage(lang) {
  return HIGHLIGHTER_OVERRIDES[lang] || lang || "text";
}
