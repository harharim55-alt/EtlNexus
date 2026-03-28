import { NodeCard } from "./PlanNodeCard";
import type { ExecutionPlanNode } from "@/types/execution-plan";

export function TreeNode({
  node,
  onExpand,
  searchQuery,
}: {
  node: ExecutionPlanNode;
  onExpand: (node: ExecutionPlanNode) => void;
  searchQuery?: string;
}) {
  const isMatch =
    searchQuery != null && searchQuery.length > 0
      ? node.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (node.detail ?? "").toLowerCase().includes(searchQuery.toLowerCase())
      : false;

  return (
    <li>
      <NodeCard
        node={node}
        onExpand={onExpand}
        highlighted={isMatch}
        searchActive={!!searchQuery}
      />
      {node.children.length > 0 && (
        <ul>
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              onExpand={onExpand}
              searchQuery={searchQuery}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

export const treeStyles = `
.tree-container ul {
  padding-top: 30px;
  position: relative;
  display: flex;
  justify-content: center;
}
.tree-container li {
  float: left;
  text-align: center;
  list-style-type: none;
  position: relative;
  padding: 30px 15px 0 15px;
}
.tree-container li::before,
.tree-container li::after {
  content: '';
  position: absolute;
  top: 0;
  right: 50%;
  border-top: 2px solid var(--border-prominent);
  width: 50%;
  height: 30px;
}
.tree-container li::after {
  right: auto;
  left: 50%;
  border-left: 2px solid var(--border-prominent);
}
.tree-container li:only-child::after,
.tree-container li:only-child::before {
  display: none;
}
.tree-container li:only-child {
  padding-top: 0;
}
.tree-container li:first-child::before,
.tree-container li:last-child::after {
  border: 0 none;
}
.tree-container li:last-child::before {
  border-right: 2px solid var(--border-prominent);
  border-radius: 0 8px 0 0;
}
.tree-container li:first-child::after {
  border-radius: 8px 0 0 0;
}
.tree-container ul ul::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  border-left: 2px solid var(--border-prominent);
  width: 0;
  height: 30px;
  transform: translateX(-50%);
}
.tree-container > ul {
  padding-top: 0;
}
`;
