'use client';

import React, { useEffect, useRef, useState, useMemo } from 'react';
import { Memory } from '@/lib/api';
import { Calendar, Users, Brain, FileText, User, Info, Star, Clock, AlertTriangle, StickyNote } from 'lucide-react';

interface Node {
  id: string;
  label: string;
  type: 'memory' | 'entity';
  memoryType?: string;
  entityType?: 'person' | 'place' | 'other';
  x: number;
  y: number;
  vx: number;
  vy: number;
  fx?: number;
  fy?: number;
  memory?: Memory;
  radius: number;
  color: string;
  frequency?: number;
  labelOffset?: { x: number; y: number };
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

// Entity colors based on type
const ENTITY_COLORS = {
  person: '#F59E0B',    // Orange for people
  place: '#10B981',     // Green for places
  other: '#8B5CF6'      // Purple for other entities
};

export default function MemoryGraph({ memories, onNodeClick, width = 800, height = 600 }: MemoryGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoveredNode, setHoveredNode] = useState<Node | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [draggedNode, setDraggedNode] = useState<Node | null>(null);
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const animationRef = useRef<number>();
  const [simulationPaused, setSimulationPaused] = useState(false);
  const [forceRedistribute, setForceRedistribute] = useState(0);

  // Extract entities with type classification and frequency
  const extractEntitiesWithMeta = (memories: Memory[]): Map<string, { type: 'person' | 'place' | 'other', frequency: number }> => {
    const entityMap = new Map<string, { type: 'person' | 'place' | 'other', frequency: number }>();
    
    // Known places for classification
    const knownPlaces = ['Cyberaya', 'Malaysia', 'Indonesia', 'Singapore', 'Thailand'];
    
    memories.forEach(memory => {
      // Extract from consolidated memory metadata (new approach)
      if (memory.extracted_from === 'limitless' && memory.metadata?.people_mentioned) {
        memory.metadata.people_mentioned.forEach((person: any) => {
          if (person.name && person.name.trim()) {
            const name = person.name.trim();
            const existing = entityMap.get(name) || { type: 'person' as const, frequency: 0 };
            entityMap.set(name, { ...existing, frequency: existing.frequency + 1 });
          }
        });
      }
      
      // Fallback: extract from content using name patterns (for backward compatibility)
      const nameMatches = memory.content.match(/\b[A-Z][a-z]{2,}( [A-Z][a-z]{2,})?\b/g);
      if (nameMatches) {
        nameMatches.forEach(name => {
          // Filter out common words that aren't names
          const excludeWords = ['You', 'The', 'And', 'But', 'For', 'With', 'From', 'Recording', 'Involves', 'Speaker', 'Discussion', 'Transitioning', 'Unknown', 'Includes'];
          if (name.length > 2 && !excludeWords.includes(name) && !name.includes('Speaker')) {
            const entityType = knownPlaces.includes(name) ? 'place' : 'other';
            const existing = entityMap.get(name) || { type: entityType, frequency: 0 };
            entityMap.set(name, { ...existing, frequency: existing.frequency + 1 });
          }
        });
      }
    });
    
    return entityMap;
  };

  // Create nodes and links from memories
  const { nodes, links } = useMemo(() => {
    const nodeMap = new Map<string, Node>();
    const linkSet = new Set<string>();
    
    // Create memory nodes with better initial distribution
    memories.forEach((memory, index) => {
      const config = MEMORY_TYPE_CONFIG[memory.type as keyof typeof MEMORY_TYPE_CONFIG] || MEMORY_TYPE_CONFIG.default;
      
      // Distribute memory nodes in a larger area, avoiding center clustering
      const memoryAngle = (index / memories.length) * 2 * Math.PI;
      const memoryDistance = 100 + Math.random() * 150;
      
      const node: Node = {
        id: memory.id,
        label: memory.content.substring(0, 30) + (memory.content.length > 30 ? '...' : ''),
        type: 'memory',
        memoryType: memory.type,
        x: width / 2 + Math.cos(memoryAngle) * memoryDistance,
        y: height / 2 + Math.sin(memoryAngle) * memoryDistance,
        vx: 0,
        vy: 0,
        memory,
        radius: 25,
        color: config.color
      };
      
      nodeMap.set(memory.id, node);
    });

    // Extract entities with metadata and create entity nodes
    const entitiesWithMeta = extractEntitiesWithMeta(memories);
    const entityNodes = new Map<string, Node>();
    
    // Calculate radius based on frequency (min 25, max 45)
    const maxFreq = Math.max(...Array.from(entitiesWithMeta.values()).map(e => e.frequency));
    
    entitiesWithMeta.forEach(({ type, frequency }, entity) => {
      if (!entityNodes.has(entity)) {
        const baseRadius = 25;
        const maxExtraRadius = 20;
        const radius = baseRadius + (frequency / Math.max(maxFreq, 1)) * maxExtraRadius;
        
        // Much better initial positioning - spiral pattern with larger distances
        const index = Array.from(entitiesWithMeta.keys()).indexOf(entity);
        const totalEntities = entitiesWithMeta.size;
        const spiralTurns = 2;
        const angle = (index / totalEntities) * spiralTurns * 2 * Math.PI;
        const distance = 200 + (index / totalEntities) * 200 + Math.random() * 80;
        
        const entityNode: Node = {
          id: `entity-${entity}`,
          label: entity,
          type: 'entity',
          entityType: type,
          x: width / 2 + Math.cos(angle) * distance,
          y: height / 2 + Math.sin(angle) * distance,
          vx: 0,
          vy: 0,
          radius,
          color: ENTITY_COLORS[type],
          frequency,
          labelOffset: { x: 0, y: 0 }
        };
        entityNodes.set(entity, entityNode);
        nodeMap.set(entityNode.id, entityNode);
      }
    });
    
    // Create links between memories and entities
    memories.forEach(memory => {
      entitiesWithMeta.forEach((meta, entity) => {
        // Check if this memory mentions this entity
        const entityLower = entity.toLowerCase();
        const contentLower = memory.content.toLowerCase();
        
        // Check if entity is mentioned in content or in metadata
        let isLinked = contentLower.includes(entityLower);
        
        // Check if this entity is in the people_mentioned metadata
        if (memory.extracted_from === 'limitless' && memory.metadata?.people_mentioned) {
          isLinked = isLinked || memory.metadata.people_mentioned.some((person: any) => 
            person.name && person.name.toLowerCase() === entityLower
          );
        }
        
        if (isLinked) {
          const linkId = `${memory.id}-entity-${entity}`;
          linkSet.add(linkId);
        }
      });
    });

    return {
      nodes: Array.from(nodeMap.values()),
      links: Array.from(linkSet).map(linkId => {
        const parts = linkId.split('-');
        const source = parts[0];
        const target = linkId.includes('-entity-') ? `entity-${parts.slice(2).join('-')}` : parts[1];
        return {
          source,
          target,
          strength: 0.3
        };
      })
    };
  }, [memories, width, height, forceRedistribute]);

  // Much stronger anti-clustering force simulation
  useEffect(() => {
    let frameCount = 0;
    const maxFrames = 2000; // Longer simulation for better settling
    
    const simulate = () => {
      if (simulationPaused || frameCount > maxFrames) return;
      
      frameCount++;
      const alpha = Math.max(0.02, 0.15 - frameCount * 0.00007); // Slower decay, stronger initial forces
      const scaleAdjustedAlpha = alpha / Math.max(transform.scale, 0.3);
      
      const centerForce = 0.005; // Much weaker center force to prevent clustering
      const linkForce = 0.15; // Weaker link force
      const repelForce = 3000; // Much stronger repulsion
      
      // Apply forces more liberally
      const shouldApplyForces = transform.scale < 3 && !isDragging;
      
      if (shouldApplyForces) {
        nodes.forEach(node => {
          if (node.fx !== undefined) node.x = node.fx;
          if (node.fy !== undefined) node.y = node.fy;
          
          // Very weak center force - mainly for boundary containment
          const centerX = width / 2;
          const centerY = height / 2;
          const distanceFromCenter = Math.sqrt((node.x - centerX) ** 2 + (node.y - centerY) ** 2);
          
          // Only apply center force if too far from center
          if (distanceFromCenter > Math.min(width, height) * 0.3) {
            node.vx += (centerX - node.x) * centerForce * scaleAdjustedAlpha;
            node.vy += (centerY - node.y) * centerForce * scaleAdjustedAlpha;
          }
          
          // MUCH stronger anti-clustering repulsion
          const baseMinDistance = 120; // Increased minimum distance
          const scaleAdjustedMinDistance = baseMinDistance / Math.max(transform.scale, 0.5);
          
          nodes.forEach(other => {
            if (node.id !== other.id) {
              const dx = node.x - other.x;
              const dy = node.y - other.y;
              const distance = Math.sqrt(dx * dx + dy * dy);
              const minDistance = node.radius + other.radius + scaleAdjustedMinDistance;
              
              if (distance < minDistance * 1.5 && distance > 0) { // Wider repulsion zone
                const force = (repelForce / Math.max(distance, 10)) * scaleAdjustedAlpha;
                const normalizedDx = dx / distance;
                const normalizedDy = dy / distance;
                
                // Stronger repulsion
                node.vx += normalizedDx * force;
                node.vy += normalizedDy * force;
                other.vx -= normalizedDx * force;
                other.vy -= normalizedDy * force;
              }
            }
          });
        });
        
        // Weaker link forces to allow spreading
        links.forEach(link => {
          const source = nodes.find(n => n.id === link.source);
          const target = nodes.find(n => n.id === link.target);
          
          if (source && target) {
            const dx = target.x - source.x;
            const dy = target.y - source.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            const targetDistance = Math.max(120, (source.radius + target.radius + 100) / Math.min(transform.scale, 1));
            
            if (distance > 0) {
              const force = (distance - targetDistance) * linkForce * scaleAdjustedAlpha;
              const fx = (dx / distance) * force;
              const fy = (dy / distance) * force;
              
              source.vx += fx;
              source.vy += fy;
              target.vx -= fx;
              target.vy -= fy;
            }
          }
        });
      }
      
      // Update positions with moderate damping for movement
      nodes.forEach(node => {
        if (node.fx === undefined) {
          node.x += node.vx;
          node.y += node.vy;
          node.vx *= 0.85; // Moderate damping to allow movement
          node.vy *= 0.85;
          
          // Keep nodes within bounds with more padding
          const padding = node.radius + 50;
          node.x = Math.max(padding, Math.min(width - padding, node.x));
          node.y = Math.max(padding, Math.min(height - padding, node.y));
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
  }, [nodes, links, width, height, transform.scale, isDragging, simulationPaused]);

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
                
                {/* Scale-aware Enhanced Label with Background */}
                <g className="pointer-events-none">
                  {transform.scale > 0.4 && (
                    <>
                      <rect
                        x={node.x - (node.label.length * 3.5)}
                        y={node.y + node.radius + 15}
                        width={node.label.length * 7}
                        height={18}
                        fill="rgba(255, 255, 255, 0.95)"
                        stroke="rgba(0, 0, 0, 0.15)"
                        strokeWidth={1 / transform.scale}
                        rx="4"
                        className="dark:fill-gray-800 dark:stroke-gray-500"
                      />
                      <text
                        x={node.x}
                        y={node.y + node.radius + 26}
                        textAnchor="middle"
                        className="fill-gray-700 dark:fill-gray-200 font-medium"
                        style={{ 
                          fontSize: `${Math.max(10, 12 / Math.sqrt(transform.scale))}px`,
                          fontWeight: node.type === 'entity' ? '600' : '500'
                        }}
                      >
                        {node.label.length > (transform.scale > 1 ? 20 : 12) 
                          ? node.label.substring(0, transform.scale > 1 ? 20 : 12) + '...' 
                          : node.label}
                      </text>
                    </>
                  )}
                </g>
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
      
      {/* Enhanced Controls */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-2">
        <div className="flex gap-2">
          <button
            onClick={() => {
              setTransform(prev => ({ ...prev, scale: Math.min(3, prev.scale * 1.3) }));
              setSimulationPaused(true);
              setTimeout(() => setSimulationPaused(false), 100);
            }}
            className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            title="Zoom In"
          >
            +
          </button>
          <button
            onClick={() => {
              setTransform(prev => ({ ...prev, scale: Math.max(0.3, prev.scale * 0.7) }));
              setSimulationPaused(true);
              setTimeout(() => setSimulationPaused(false), 100);
            }}
            className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            title="Zoom Out"
          >
            -
          </button>
          <button
            onClick={() => {
              setTransform({ x: 0, y: 0, scale: 1 });
              setSimulationPaused(true);
              setTimeout(() => setSimulationPaused(false), 200);
            }}
            className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            title="Reset View"
          >
            Reset
          </button>
          <button
            onClick={() => setSimulationPaused(!simulationPaused)}
            className={`px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg text-sm font-medium transition-colors ${
              simulationPaused 
                ? 'bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-200' 
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
            title={simulationPaused ? "Resume Animation" : "Pause Animation"}
          >
            {simulationPaused ? '▶' : '⏸'}
          </button>
        </div>
        <div className="flex gap-2 mt-2">
          <button
            onClick={() => {
              setForceRedistribute(prev => prev + 1);
              setSimulationPaused(false);
            }}
            className="px-3 py-2 bg-blue-100 dark:bg-blue-800 border border-blue-300 dark:border-blue-700 rounded-lg text-sm font-medium text-blue-700 dark:text-blue-200 hover:bg-blue-200 dark:hover:bg-blue-700 transition-colors"
            title="Spread Out Nodes"
          >
            Spread Out
          </button>
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
          Zoom: {Math.round(transform.scale * 100)}%
        </div>
      </div>
      
      {/* Legend */}
      <div className="absolute top-4 right-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 shadow-lg">
        <div className="text-sm font-medium text-gray-900 dark:text-white mb-2">Legend</div>
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs">
            <div className="w-3 h-3 rounded-full bg-orange-500"></div>
            <span className="text-gray-700 dark:text-gray-300">People</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span className="text-gray-700 dark:text-gray-300">Places</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <div className="w-3 h-3 rounded-full bg-purple-500"></div>
            <span className="text-gray-700 dark:text-gray-300">Other</span>
          </div>
          <div className="flex items-center gap-2 text-xs mt-2 pt-2 border-t border-gray-200 dark:border-gray-600">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            <span className="text-gray-700 dark:text-gray-300">Memories</span>
          </div>
        </div>
      </div>
    </div>
  );
}