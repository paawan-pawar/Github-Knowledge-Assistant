import { useEffect, useMemo, useState } from "react";
import { ChevronRight, File, Folder, FolderOpen, Search } from "lucide-react";
import { api } from "../api/client";

function FileNode({ node, depth, selectedPath, onSelect, expanded, toggleExpanded }) {
  const isDir = node.type === "dir";
  const isOpen = expanded.has(node.path || node.name);
  const isSelected = selectedPath === node.path;

  if (isDir) {
    return (
      <div>
        <button
          type="button"
          onClick={() => toggleExpanded(node.path || node.name)}
          className="flex w-full items-center gap-1.5 rounded-sm px-1.5 py-1 text-left text-xs text-ink-muted hover:bg-surface-hover hover:text-ink"
          style={{ paddingLeft: `${depth * 14 + 6}px` }}
        >
          <ChevronRight size={12} className={`shrink-0 transition-transform ${isOpen ? "rotate-90" : ""}`} />
          {isOpen ? <FolderOpen size={13} className="shrink-0 text-det-import" /> : <Folder size={13} className="shrink-0 text-det-import" />}
          <span className="truncate">{node.name}</span>
        </button>
        {isOpen && node.children?.map((child) => (
          <FileNode
            key={child.path || child.name}
            node={child}
            depth={depth + 1}
            selectedPath={selectedPath}
            onSelect={onSelect}
            expanded={expanded}
            toggleExpanded={toggleExpanded}
          />
        ))}
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => onSelect(node.path)}
      className={`det-frame flex w-full items-center gap-1.5 rounded-sm px-1.5 py-1 text-left text-xs transition-colors ${
        isSelected ? "bg-det-function/10 text-det-function" : "text-ink-muted hover:bg-surface-hover hover:text-ink"
      }`}
      data-active={isSelected ? "true" : "false"}
      style={{ paddingLeft: `${depth * 14 + 22}px` }}
    >
      <File size={12} className="shrink-0" />
      <span className="truncate">{node.name}</span>
    </button>
  );
}

export default function FileTree({ repoId, tree, selectedPath, onSelect }) {
  const [expanded, setExpanded] = useState(() => new Set([""]));
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);

  useEffect(() => {
    if (!query.trim()) {
      setSearchResults(null);
      return;
    }
    const handle = setTimeout(async () => {
      try {
        const hits = await api.searchFiles(repoId, query.trim());
        setSearchResults(hits);
      } catch {
        setSearchResults([]);
      }
    }, 180);
    return () => clearTimeout(handle);
  }, [query, repoId]);

  function toggleExpanded(key) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  const rootChildren = useMemo(() => tree?.children || [], [tree]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-1.5 border-b border-line px-2 py-2">
        <Search size={12} className="shrink-0 text-ink-faint" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="search files..."
          className="w-full bg-transparent text-xs text-ink outline-none placeholder:text-ink-faint"
        />
      </div>
      <div className="flex-1 overflow-y-auto py-1">
        {searchResults ? (
          searchResults.length ? (
            searchResults.map((hit) => (
              <button
                key={hit.path}
                type="button"
                onClick={() => onSelect(hit.path)}
                className={`flex w-full items-center gap-1.5 px-2.5 py-1 text-left text-xs transition-colors ${
                  selectedPath === hit.path ? "bg-det-function/10 text-det-function" : "text-ink-muted hover:bg-surface-hover hover:text-ink"
                }`}
              >
                <File size={12} className="shrink-0" />
                <span className="truncate">{hit.path}</span>
              </button>
            ))
          ) : (
            <p className="px-3 py-2 text-xs text-ink-faint">No files match "{query}"</p>
          )
        ) : (
          rootChildren.map((child) => (
            <FileNode
              key={child.path || child.name}
              node={child}
              depth={0}
              selectedPath={selectedPath}
              onSelect={onSelect}
              expanded={expanded}
              toggleExpanded={toggleExpanded}
            />
          ))
        )}
      </div>
    </div>
  );
}
