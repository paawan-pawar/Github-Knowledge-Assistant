import { lazy, Suspense, useEffect, useState } from "react";
import { Bug, FileText, GitCommitHorizontal, LayoutGrid, Loader2, MessageSquare, Search } from "lucide-react";
import { api } from "../api/client";
import TopBar from "./TopBar";
import FileTree from "./FileTree";
import FileViewer from "./FileViewer";

// Each tab's code (and its share of react-markdown / recharts / the syntax
// highlighter) only downloads once that tab is actually opened.
const ChatPanel = lazy(() => import("./ChatPanel"));
const SearchPanel = lazy(() => import("./SearchPanel"));
const ArchitecturePanel = lazy(() => import("./ArchitecturePanel"));
const DocsPanel = lazy(() => import("./DocsPanel"));
const BugsPanel = lazy(() => import("./BugsPanel"));
const CommitsPanel = lazy(() => import("./CommitsPanel"));

function PanelFallback() {
  return (
    <div className="flex h-full items-center justify-center text-ink-faint">
      <Loader2 size={16} className="animate-spin" />
    </div>
  );
}

const TABS = [
  { key: "chat", label: "Chat", icon: MessageSquare },
  { key: "search", label: "Search", icon: Search },
  { key: "architecture", label: "Architecture", icon: LayoutGrid },
  { key: "docs", label: "Docs", icon: FileText },
  { key: "bugs", label: "Bugs", icon: Bug },
  { key: "commits", label: "Commits", icon: GitCommitHorizontal },
];

export default function Workspace({ repo, onReindex, onClose }) {
  const [tree, setTree] = useState(null);
  const [activeTab, setActiveTab] = useState("chat");
  const [selectedPath, setSelectedPath] = useState(null);
  const [highlightRange, setHighlightRange] = useState(null);
  const [showInspector, setShowInspector] = useState(true);

  useEffect(() => {
    api.getTree(repo.repo_id).then(setTree);
  }, [repo.repo_id]);

  function jumpToSource(source) {
    setSelectedPath(source.path);
    setHighlightRange({ start_line: source.start_line, end_line: source.end_line });
    setShowInspector(true);
  }

  function selectFile(path) {
    setSelectedPath(path);
    setHighlightRange(null);
    setShowInspector(true);
  }

  return (
    <div className="flex h-screen flex-col bg-canvas">
      <TopBar repo={repo} onReindex={onReindex} onClose={onClose} />

      <div className="flex min-h-0 flex-1">
        <aside className="w-56 shrink-0 border-r border-line bg-canvas-raised">
          <FileTree repoId={repo.repo_id} tree={tree} selectedPath={selectedPath} onSelect={selectFile} />
        </aside>

        <main className="flex min-w-0 flex-1 flex-col border-r border-line">
          <nav className="flex shrink-0 items-center gap-0.5 border-b border-line bg-canvas-raised px-2">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex items-center gap-1.5 border-b-2 px-3 py-2.5 text-xs transition-colors ${
                    active
                      ? "border-det-function text-det-function"
                      : "border-transparent text-ink-muted hover:text-ink"
                  }`}
                >
                  <Icon size={13} /> {tab.label}
                </button>
              );
            })}
            <button
              type="button"
              onClick={() => setShowInspector((v) => !v)}
              className="ml-auto rounded-sm px-2 py-1 text-[11px] text-ink-faint hover:text-ink-muted lg:hidden"
            >
              {showInspector ? "hide inspector" : "show inspector"}
            </button>
          </nav>

          <div className="min-h-0 flex-1">
            <Suspense fallback={<PanelFallback />}>
              {activeTab === "chat" && <ChatPanel repoId={repo.repo_id} onJumpToSource={jumpToSource} />}
              {activeTab === "search" && <SearchPanel repoId={repo.repo_id} onJumpToSource={jumpToSource} />}
              {activeTab === "architecture" && <ArchitecturePanel repoId={repo.repo_id} />}
              {activeTab === "docs" && <DocsPanel repoId={repo.repo_id} selectedPath={selectedPath} />}
              {activeTab === "bugs" && <BugsPanel repoId={repo.repo_id} onJumpToSource={jumpToSource} />}
              {activeTab === "commits" && <CommitsPanel repoId={repo.repo_id} />}
            </Suspense>
          </div>
        </main>

        {showInspector && (
          <aside className="hidden w-[38%] max-w-2xl shrink-0 bg-canvas-raised lg:block">
            <FileViewer
              repoId={repo.repo_id}
              path={selectedPath}
              highlightRange={highlightRange}
              onClearHighlight={() => setHighlightRange(null)}
            />
          </aside>
        )}
      </div>
    </div>
  );
}
