"use client";

import { useCallback, useEffect, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  Position,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import type { PGMModel, PGMNode } from "@/lib/types";
import { formatPct } from "@/lib/utils";

// Manual layout positions for the 8-node water infrastructure graph
const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
  rainfall: { x: 0, y: 0 },
  electricity_reliability: { x: 300, y: 0 },
  household_demand: { x: 600, y: 0 },
  water_availability: { x: 0, y: 150 },
  storage_level: { x: 150, y: 150 },
  pump_availability: { x: 300, y: 150 },
  distribution_capacity: { x: 200, y: 300 },
  water_access: { x: 200, y: 450 },
};

interface PGMGraphProps {
  model: PGMModel;
  onNodeClick?: (node: PGMNode) => void;
}

function getNodeColor(node: PGMNode): string {
  if (node.name === "water_access") return "#10b981"; // emerald — target
  if (node.evidence_status === "external_evidence") return "#6366f1"; // indigo — confirmed
  if (node.evidence_status === "inferred") return "#8b5cf6"; // violet — inferred
  return "#71717a"; // zinc — assumption
}

function getConfidenceWidth(confidence: number): number {
  return 1 + confidence * 2; // 1px to 3px
}

export function PGMGraph({ model, onNodeClick }: PGMGraphProps) {
  const [selectedNode, setSelectedNode] = useState<PGMNode | null>(null);

  const rfNodes: Node[] = model.nodes.map((node) => {
    const pos = NODE_POSITIONS[node.name] ?? { x: Math.random() * 400, y: Math.random() * 400 };
    const color = getNodeColor(node);
    const isTarget = node.name === "water_access";

    return {
      id: node.name,
      position: pos,
      data: {
        label: (
          <div className="px-3 py-2 text-center">
            <div className="text-xs font-semibold text-zinc-100">{node.display_name}</div>
            <div className="mt-1 text-xs text-zinc-400">
              conf: {formatPct(node.confidence)}
            </div>
            {node.sensitivity_score != null && node.sensitivity_score > 0 && (
              <div className="mt-0.5 text-xs" style={{ color }}>
                sens: {node.sensitivity_score.toFixed(2)}
              </div>
            )}
          </div>
        ),
        node,
      },
      style: {
        background: "#18181b",
        border: `2px solid ${color}`,
        borderRadius: "8px",
        width: isTarget ? 140 : 130,
        cursor: "pointer",
        boxShadow: isTarget ? `0 0 12px ${color}40` : undefined,
      },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
    };
  });

  const rfEdges: Edge[] = model.edges.map((edge, i) => ({
    id: `e${i}-${edge.parent}-${edge.child}`,
    source: edge.parent,
    target: edge.child,
    animated: false,
    style: {
      stroke: edge.direction === "positive" ? "#6366f1" : "#ef4444",
      strokeWidth: getConfidenceWidth(edge.strength),
      opacity: 0.6,
    },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: edge.direction === "positive" ? "#6366f1" : "#ef4444",
      width: 16,
      height: 16,
    },
    label: edge.strength > 0.6 ? `${(edge.strength * 100).toFixed(0)}%` : undefined,
    labelStyle: { fill: "#71717a", fontSize: "10px" },
    labelBgStyle: { fill: "#09090b" },
  }));

  const [nodes, , onNodesChange] = useNodesState(rfNodes);
  const [edges, , onEdgesChange] = useEdgesState(rfEdges);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const pgmNode = model.nodes.find((n) => n.name === node.id);
      if (pgmNode) {
        setSelectedNode(pgmNode);
        onNodeClick?.(pgmNode);
      }
    },
    [model.nodes, onNodeClick],
  );

  return (
    <div className="relative w-full h-full" style={{ minHeight: 520 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        nodesDraggable={false}
        zoomOnScroll={true}
        panOnDrag={true}
      >
        <Background color="#27272a" gap={20} size={1} />
        <Controls className="!bg-zinc-900 !border-zinc-700" />
        <MiniMap
          nodeColor={(n) => {
            const pgmNode = model.nodes.find((mn) => mn.name === n.id);
            return pgmNode ? getNodeColor(pgmNode) : "#71717a";
          }}
          className="!bg-zinc-900 !border-zinc-700"
        />
      </ReactFlow>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 rounded border border-zinc-800 bg-zinc-950/90 p-3 text-xs space-y-1.5 backdrop-blur">
        <div className="text-zinc-500 font-medium mb-2">Node type</div>
        <LegendItem color="#10b981" label="Target outcome" />
        <LegendItem color="#6366f1" label="External evidence" />
        <LegendItem color="#8b5cf6" label="Inferred" />
        <LegendItem color="#71717a" label="Assumption" />
        <div className="mt-2 pt-2 border-t border-zinc-800 text-zinc-500 font-medium">Edge direction</div>
        <LegendItem color="#6366f1" label="Positive causal" />
        <LegendItem color="#ef4444" label="Negative causal" />
      </div>

      {/* Node detail panel */}
      {selectedNode && (
        <div className="absolute top-4 right-4 w-72 rounded border border-zinc-700 bg-zinc-950/95 p-4 backdrop-blur text-xs">
          <div className="flex items-start justify-between mb-3">
            <div>
              <div className="font-semibold text-zinc-100">{selectedNode.display_name}</div>
              <div className="text-zinc-500 mt-0.5">{selectedNode.unit}</div>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-zinc-600 hover:text-zinc-400"
            >
              ✕
            </button>
          </div>
          <p className="text-zinc-400 mb-3 leading-relaxed">{selectedNode.description}</p>
          <dl className="space-y-2">
            <DetailRow label="Confidence" value={formatPct(selectedNode.confidence)} />
            <DetailRow label="Evidence status" value={selectedNode.evidence_status} />
            <DetailRow label="Source" value={selectedNode.evidence_source} />
            {selectedNode.sensitivity_score != null && (
              <DetailRow
                label="Sensitivity"
                value={selectedNode.sensitivity_score.toFixed(3)}
              />
            )}
            <DetailRow label="Distribution" value={selectedNode.distribution.type} />
          </dl>
        </div>
      )}
    </div>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
      <span className="text-zinc-400">{label}</span>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <dt className="text-zinc-600">{label}</dt>
      <dd className="text-zinc-300 text-right">{value}</dd>
    </div>
  );
}
