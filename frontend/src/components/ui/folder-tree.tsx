import { useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ChevronRight, Folder, FolderOpen, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

// Adaptado de 21st.dev/@scrollxui/folder-tree: misma estética (chevron que rota, contenido que
// se despliega), pero los hijos se cargan recién al abrir la carpeta: el disco puede ser enorme.

export type TreeNode = {
  id: string;
  label: string;
  badge?: ReactNode;
  highlight?: boolean;
  leaf?: boolean;
};

type TreeProps = {
  nodes: TreeNode[];
  load: (id: string) => Promise<TreeNode[]>;
  selected: string | null;
  onSelect: (node: TreeNode) => void;
  onOpen: (node: TreeNode) => void;
  level?: number;
};

export function FolderTree({ nodes, load, selected, onSelect, onOpen, level = 0 }: TreeProps) {
  return (
    <div role={level === 0 ? "tree" : "group"} className="flex flex-col">
      {nodes.map((node, i) => (
        <FolderTreeItem
          key={node.id}
          node={node}
          index={i}
          level={level}
          load={load}
          selected={selected}
          onSelect={onSelect}
          onOpen={onOpen}
        />
      ))}
    </div>
  );
}

function FolderTreeItem({
  node,
  index,
  level,
  load,
  selected,
  onSelect,
  onOpen,
}: Omit<TreeProps, "nodes"> & { node: TreeNode; index: number; level: number }) {
  const [open, setOpen] = useState(false);
  const [hijos, setHijos] = useState<TreeNode[] | null>(null);
  const [cargando, setCargando] = useState(false);
  const isSelected = selected === node.id;

  const toggle = async () => {
    if (node.leaf) return;
    if (!open && hijos === null) {
      setCargando(true);
      try {
        setHijos(await load(node.id));
      } catch {
        setHijos([]);
      } finally {
        setCargando(false);
      }
    }
    setOpen((v) => !v);
  };

  const Icon = open ? FolderOpen : Folder;

  return (
    <div>
      <motion.div
        role="treeitem"
        aria-selected={isSelected}
        aria-expanded={node.leaf ? undefined : open}
        tabIndex={0}
        initial={{ opacity: 0, x: -8 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.18, delay: Math.min(index, 12) * 0.015 }}
        onClick={() => onSelect(node)}
        onDoubleClick={() => onOpen(node)}
        onKeyDown={(e) => {
          if (e.key === "Enter") onOpen(node);
          else if (e.key === " ") {
            e.preventDefault();
            onSelect(node);
          } else if (e.key === "ArrowRight" && !open) toggle();
          else if (e.key === "ArrowLeft" && open) setOpen(false);
        }}
        style={{ paddingLeft: 10 + level * 18 }}
        className={cn(
          "group flex cursor-pointer select-none items-center gap-2 rounded-xl py-2 pr-2 text-sm outline-none transition-colors",
          "focus-visible:ring-2 focus-visible:ring-accent/60",
          isSelected
            ? "bg-accent/15 text-ink shadow-[inset_0_0_0_1px_rgb(139_123_255/0.45)]"
            : "text-ink-2 hover:bg-white/[0.05] hover:text-ink",
        )}
      >
        <button
          type="button"
          tabIndex={-1}
          aria-label={open ? "Contraer" : "Expandir"}
          onClick={(e) => {
            e.stopPropagation();
            toggle();
          }}
          className={cn(
            "grid size-5 shrink-0 place-items-center rounded-md text-ink-3 hover:bg-white/10 hover:text-ink",
            node.leaf && "invisible",
          )}
        >
          {cargando ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <motion.span animate={{ rotate: open ? 90 : 0 }} transition={{ duration: 0.18 }} className="grid">
              <ChevronRight className="size-3.5" />
            </motion.span>
          )}
        </button>
        <Icon
          className={cn(
            "size-4 shrink-0",
            node.highlight ? "text-apart drop-shadow-[0_0_8px_rgb(245_193_74/0.6)]" : isSelected ? "text-accent" : "text-ink-3",
          )}
        />
        <span className="min-w-0 flex-1 truncate">{node.label}</span>
        {node.badge}
      </motion.div>
      <AnimatePresence initial={false}>
        {open && hijos && hijos.length > 0 ? (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.22, ease: "easeInOut" }}
            style={{ overflow: "hidden" }}
          >
            <FolderTree nodes={hijos} load={load} selected={selected} onSelect={onSelect} onOpen={onOpen} level={level + 1} />
          </motion.div>
        ) : null}
        {open && hijos && hijos.length === 0 ? (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{ paddingLeft: 46 + level * 18 }}
            className="py-1 text-xs text-ink-3"
          >
            Sin subcarpetas
          </motion.p>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
