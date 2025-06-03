'use client';

import React, { useEffect, useRef, useState, useMemo } from 'react';
import { Memory } from '@/lib/api';
import { Calendar, Users, Brain, FileText, User, Info, Star, Clock, AlertTriangle, StickyNote } from 'lucide-react';

interface Node {
  id: string;
  label: string;
  type: 'memory' | 'entity';
  memoryType?: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  fx?: number;
  fy?: number;
  memory?: Memory;
  radius: number;
  color: string;
}

interface Link {
  source: string;
  target: string;
  strength: number;
}

interface MemoryGraphProps {
  memories: Memory[];
  onNodeClick: (memory: Memory) => void;
  width?: number;
  height?: number;
}

const MEMORY_TYPE_CONFIG = {
  fact: { color: '#3B82F6', icon: Info, label: 'Fact' },
  preference: { color: '#10B981', icon: Star, label: 'Preference' },
  relationship: { color: '#EC4899', icon: Users, label: 'Relationship' },
  routine: { color: '#8B5CF6', icon: Clock, label: 'Routine' },
  important_date: { color: '#F59E0B', icon: Calendar, label: 'Important Date' },
  personal_info: { color: '#6366F1', icon: User, label: 'Personal Info' },
  allergy: { color: '#EF4444', icon: AlertTriangle, label: 'Allergy' },
  note: { color: '#6B7280', icon: StickyNote, label: 'Note' },
  default: { color: '#6B7280', icon: FileText, label: 'Other' }
};

const ENTITY_COLOR = '#F59E0B'; // Orange for entity nodes

export default function MemoryGraph({ memories, onNodeClick, width = 800, height = 600 }: MemoryGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoveredNode, setHoveredNode] = useState<Node | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [draggedNode, setDraggedNode] = useState<Node | null>(null);
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const animationRef = useRef<number>();

  // Extract entities from memory content
  const extractEntities = (content: string): string[] => {
    const entities: string[] = [];
    const commonNames = ['Hisyam', 'Fafa', 'Arissa', 'Sarah', 'Ahmad', 'Siti'];
    
    commonNames.forEach(name => {
      if (content.toLowerCase().includes(name.toLowerCase())) {
        entities.push(name);
      }
    });
    
    return entities;
  };

  // Create nodes and links from memories
  const { nodes, links } = useMemo(() => {
    const nodeMap = new Map<string, Node>();
    const linkSet = new Set<string>();
    
    // Create memory nodes
    memories.forEach((memory, index) => {
      const config = MEMORY_TYPE_CONFIG[memory.type as keyof typeof MEMORY_TYPE_CONFIG] || MEMORY_TYPE_CONFIG.default;
      
      const node: Node = {
        id: memory.id,
        label: memory.content.substring(0, 30) + (memory.content.length > 30 ? '...' : ''),
        type: 'memory',
        memoryType: memory.type,
        x: Math.random() * width,
        y: Math.random() * height,
        vx: 0,
        vy: 0,
        memory,
        radius: 25,
        color: config.color
      };
      
      nodeMap.set(memory.id, node);
    });

    // Create entity nodes and links
    const entityNodes = new Map<string, Node>();
    
    memories.forEach(memory => {
      const entities = extractEntities(memory.content);
      
      entities.forEach(entity => {
        if (!entityNodes.has(entity)) {
          const entityNode: Node = {
            id: `entity-${entity}`,
            label: entity,
            type: 'entity',
            x: width / 2 + (Math.random() - 0.5) * 200,
            y: height / 2 + (Math.random() - 0.5) * 200,
            vx: 0,
            vy: 0,
            radius: entity === 'Hisyam' ? 35 : 30,
            color: ENTITY_COLOR
          };
          entityNodes.set(entity, entityNode);
          nodeMap.set(entityNode.id, entityNode);
        }
        
        // Create link between memory and entity
        const linkId = `${memory.id}-${entityNodes.get(entity)!.id}`;
        linkSet.add(linkId);
      });
    });

    return {
      nodes: Array.from(nodeMap.values()),
      links: Array.from(linkSet).map(linkId => {
        const [source, target] = linkId.split('-').slice(0, 2);
        return {
          source,
          target: target === 'entity' ? linkId.split('-').slice(1).join('-') : target,
          strength: 0.3
        };
      })
    };
  }, [memories, width, height]);

  // Force simulation
  useEffect(() => {
    const simulate = () => {
      const alpha = 0.1;
      const centerForce = 0.02;
      const linkForce = 0.3;
      const repelForce = 800;
      
      // Apply forces
      nodes.forEach(node => {
        if (node.fx !== undefined) node.x = node.fx;
        if (node.fy !== undefined) node.y = node.fy;
        
        // Center force
        const centerX = width / 2;
        const centerY = height / 2;
        node.vx += (centerX - node.x) * centerForce * alpha;
        node.vy += (centerY - node.y) * centerForce * alpha;
        
        // Repel force between nodes
        nodes.forEach(other => {
          if (node.id !== other.id) {
            const dx = node.x - other.x;
            const dy = node.y - other.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            if (distance < 100) {
              const force = repelForce / (distance * distance);
              node.vx += dx * force * alpha;
              node.vy += dy * force * alpha;
            }
          }
        });
      });
      
      // Link forces
      links.forEach(link => {
        const source = nodes.find(n => n.id === link.source);
        const target = nodes.find(n => n.id === link.target);
        
        if (source && target) {
          const dx = target.x - source.x;
          const dy = target.y - source.y;
          const distance = Math.sqrt(dx * dx + dy * dy);
          const targetDistance = 80;
          const force = (distance - targetDistance) * linkForce * alpha;
          
          const fx = dx * force / distance;
          const fy = dy * force / distance;
          
          source.vx += fx;
          source.vy += fy;
          target.vx -= fx;
          target.vy -= fy;
        }
      });
      
      // Update positions
      nodes.forEach(node => {
        if (node.fx === undefined) {
          node.x += node.vx;
          node.y += node.vy;
          node.vx *= 0.9; // Damping
          node.vy *= 0.9;
          
          // Keep nodes within bounds
          node.x = Math.max(node.radius, Math.min(width - node.radius, node.x));
          node.y = Math.max(node.radius, Math.min(height - node.radius, node.y));
        }
      });
      
      animationRef.current = requestAnimationFrame(simulate);
    };
    
    simulate();
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [nodes, links, width, height]);

  // Mouse handlers
  const handleMouseDown = (e: React.MouseEvent, node: Node) => {
    e.preventDefault();
    setIsDragging(true);
    setDraggedNode(node);
    node.fx = node.x;
    node.fy = node.y;
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging && draggedNode) {
      const rect = svgRef.current?.getBoundingClientRect();
      if (rect) {
        draggedNode.fx = (e.clientX - rect.left - transform.x) / transform.scale;
        draggedNode.fy = (e.clientY - rect.top - transform.y) / transform.scale;
      }
    }
  };

  const handleMouseUp = () => {
    if (draggedNode) {
      draggedNode.fx = undefined;
      draggedNode.fy = undefined;
    }
    setIsDragging(false);
    setDraggedNode(null);
  };

  const handleNodeClick = (node: Node) => {
    if (!isDragging && node.memory) {
      onNodeClick(node.memory);
    }
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.1, Math.min(3, transform.scale * delta));
    setTransform(prev => ({ ...prev, scale: newScale }));
  };

  const getIcon = (node: Node) => {
    if (node.type === 'entity') {
      return User;
    }
    const config = MEMORY_TYPE_CONFIG[node.memoryType as keyof typeof MEMORY_TYPE_CONFIG] || MEMORY_TYPE_CONFIG.default;
    return config.icon;
  };

  return (
    <div className="relative w-full h-full bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <svg
        ref={svgRef}
        width={width}
        height={height}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
        className="cursor-grab"
        style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
      >
        <g transform={`translate(${transform.x}, ${transform.y}) scale(${transform.scale})`}>
          {/* Links */}
          {links.map((link, index) => {
            const source = nodes.find(n => n.id === link.source);
            const target = nodes.find(n => n.id === link.target);
            
            if (!source || !target) return null;
            
            return (
              <line
                key={index}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke="#9CA3AF"
                strokeWidth="2"
                opacity="0.6"
              />
            );
          })}
          
          {/* Nodes */}
          {nodes.map(node => {
            const IconComponent = getIcon(node);
            
            return (
              <g key={node.id}>
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={node.radius}
                  fill={node.color}
                  stroke="#FFFFFF"
                  strokeWidth="3"
                  opacity={hoveredNode?.id === node.id ? 0.8 : 1}
                  onMouseDown={(e) => handleMouseDown(e, node)}
                  onMouseEnter={() => setHoveredNode(node)}
                  onMouseLeave={() => setHoveredNode(null)}
                  onClick={() => handleNodeClick(node)}
                  className="cursor-pointer hover:stroke-gray-300 transition-all duration-200"
                  style={{ filter: hoveredNode?.id === node.id ? 'drop-shadow(0 4px 8px rgba(0,0,0,0.2))' : 'none' }}
                />
                
                {/* Icon */}
                <foreignObject
                  x={node.x - 8}
                  y={node.y - 8}
                  width="16"
                  height="16"
                  className="pointer-events-none"
                >
                  <IconComponent className="w-4 h-4 text-white" />
                </foreignObject>
                
                {/* Label */}
                <text
                  x={node.x}
                  y={node.y + node.radius + 15}
                  textAnchor="middle"
                  className="text-xs fill-gray-700 dark:fill-gray-300 font-medium pointer-events-none"
                  style={{ maxWidth: `${node.radius * 2}px` }}
                >
                  {node.label}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
      
      {/* Tooltip */}
      {hoveredNode && hoveredNode.memory && (
        <div className="absolute top-4 left-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 shadow-lg max-w-xs z-10">
          <div className="text-sm font-medium text-gray-900 dark:text-white mb-2">
            {hoveredNode.memory.type.replace('_', ' ').toUpperCase()}
          </div>
          <div className="text-sm text-gray-700 dark:text-gray-300">
            {hoveredNode.memory.content}
          </div>
          {hoveredNode.memory.tags && hoveredNode.memory.tags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {hoveredNode.memory.tags.map((tag, index) => (
                <span
                  key={index}
                  className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-xs rounded-full"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
      
      {/* Controls */}
      <div className="absolute bottom-4 right-4 flex gap-2">
        <button
          onClick={() => setTransform({ x: 0, y: 0, scale: 1 })}
          className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          Reset View
        </button>
      </div>
    </div>
  );
}