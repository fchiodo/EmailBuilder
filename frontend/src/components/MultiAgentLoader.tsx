'use client';

import { useEffect, useState } from 'react';

interface AgentStep {
  step: string;
  agent: string;
  message: string;
  progress: number;
}

interface MultiAgentLoaderProps {
  isVisible: boolean;
  onComplete?: (result: any) => void;
  onError?: (error: string) => void;
  templateRequest: any;
}

const agents = [
  {
    id: 'supervisor',
    name: 'Supervisor',
    icon: '🎯',
    color: 'from-purple-500 to-purple-600',
    description: 'Orchestrazione workflow'
  },
  {
    id: 'retriever',
    name: 'Retriever',
    icon: '🔍',
    color: 'from-blue-500 to-blue-600',
    description: 'Recupero dati prodotti'
  },
  {
    id: 'asset_curator',
    name: 'Asset Curator',
    icon: '🎨',
    color: 'from-green-500 to-green-600',
    description: 'Selezione immagini'
  },
  {
    id: 'copywriter',
    name: 'Copywriter',
    icon: '✍️',
    color: 'from-orange-500 to-orange-600',
    description: 'Generazione copy'
  },
  {
    id: 'template_layout',
    name: 'Template Layout',
    icon: '🏗️',
    color: 'from-pink-500 to-pink-600',
    description: 'Composizione template'
  },
  {
    id: 'render',
    name: 'Render',
    icon: '⚡',
    color: 'from-indigo-500 to-indigo-600',
    description: 'Rendering finale'
  }
];

export default function MultiAgentLoader({
  isVisible,
  onComplete,
  onError,
  templateRequest
}: MultiAgentLoaderProps) {
  const [currentStep, setCurrentStep] = useState<AgentStep | null>(null);
  const [progress, setProgress] = useState(0);
  const [activeAgent, setActiveAgent] = useState<string>('supervisor');
  const [completedAgents, setCompletedAgents] = useState<Set<string>>(new Set());
  const [eventSource, setEventSource] = useState<EventSource | null>(null);

  useEffect(() => {
    if (!isVisible) {
      // Reset state when not visible
      setCurrentStep(null);
      setProgress(0);
      setActiveAgent('supervisor');
      setCompletedAgents(new Set());
      if (eventSource) {
        eventSource.close();
        setEventSource(null);
      }
      return;
    }

    // Start the stream when component becomes visible
    const startStream = async () => {
      try {
        // Try proxy first, then direct connection
        const apiUrl = process.env.NODE_ENV === 'development'
          ? 'http://localhost:8000/generate-stream'
          : '/api/generate-stream';

        const response = await fetch(apiUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          },
          body: JSON.stringify(templateRequest),
        });

        if (!response.ok) {
          throw new Error('Stream failed to start');
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error('No reader available');
        }

        const processStream = async () => {
          try {
            while (true) {
              const { done, value } = await reader.read();

              if (done) break;

              const chunk = decoder.decode(value);

              // Split by double newlines to separate SSE events
              const events = chunk.split('\\n\\n');

              for (const event of events) {
                const lines = event.split('\\n');
                for (const line of lines) {
                  if (line.startsWith('data: ') && line.trim().length > 6) {
                    try {
                      const jsonString = line.slice(6).trim();
                      if (!jsonString) continue; // Skip empty data
                      const data = JSON.parse(jsonString);

                    if (data.step === 'result') {
                      // Final result received
                      setProgress(100);
                      setTimeout(() => {
                        onComplete?.(data.result);
                      }, 500);
                    } else if (data.step === 'error') {
                      onError?.(data.message);
                    } else {
                      // Progress update
                      setCurrentStep(data);
                      setProgress(data.progress);
                      setActiveAgent(data.agent);

                      // Mark previous agents as completed
                      if (data.progress > 0) {
                        const agentIndex = agents.findIndex(a => a.id === data.agent);
                        const completed = new Set<string>();
                        for (let i = 0; i < agentIndex; i++) {
                          completed.add(agents[i].id);
                        }
                        setCompletedAgents(completed);
                      }
                    }
                  } catch (e) {
                    console.error('Error parsing SSE data:', e);
                    console.error('Problematic line:', line);
                    console.error('JSON string:', line.slice(6).trim());
                    // Continue processing other lines instead of breaking
                  }
                }
              }
            }
          } catch (error) {
            console.error('Stream processing error:', error);
            onError?.('Errore durante la comunicazione con il server');
          }
        };

        processStream();

      } catch (error) {
        console.error('Failed to start stream:', error);
        onError?.('Impossibile avviare la generazione');
      }
    };

    startStream();

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [isVisible, templateRequest]);

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="bg-white rounded-2xl p-8 max-w-2xl w-full mx-4 animate-fadeIn">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <span className="text-white text-2xl">🤖</span>
          </div>
          <h3 className="text-2xl font-bold text-slate-900 mb-2">
            Multi-Agent AI Processing
          </h3>
          <p className="text-slate-600">
            I nostri agenti AI stanno collaborando per creare la tua email
          </p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-700">Progresso Generale</span>
            <span className="text-sm font-bold text-slate-900">{progress}%</span>
          </div>
          <div className="w-full bg-slate-200 rounded-full h-3">
            <div
              className="bg-gradient-to-r from-purple-500 to-indigo-600 h-3 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Current Step Info */}
        {currentStep && (
          <div className="bg-slate-50 rounded-xl p-4 mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
              <span className="font-medium text-slate-900">{currentStep.message}</span>
            </div>
          </div>
        )}

        {/* Agents Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {agents.map((agent, index) => {
            const isActive = activeAgent === agent.id;
            const isCompleted = completedAgents.has(agent.id);
            const isPending = !isActive && !isCompleted;

            return (
              <div
                key={agent.id}
                className={`p-4 rounded-xl border-2 transition-all duration-300 ${
                  isActive
                    ? 'border-blue-500 bg-blue-50 scale-105'
                    : isCompleted
                    ? 'border-green-500 bg-green-50'
                    : 'border-slate-200 bg-white'
                }`}
              >
                <div className="text-center">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-2 ${
                    isActive
                      ? `bg-gradient-to-br ${agent.color} animate-pulse`
                      : isCompleted
                      ? 'bg-gradient-to-br from-green-500 to-green-600'
                      : 'bg-slate-200'
                  }`}>
                    <span className={`text-xl ${
                      isActive || isCompleted ? 'text-white' : 'text-slate-600'
                    }`}>
                      {isCompleted ? '✓' : agent.icon}
                    </span>
                  </div>
                  <h4 className={`font-semibold text-sm mb-1 ${
                    isActive ? 'text-blue-900' : isCompleted ? 'text-green-900' : 'text-slate-700'
                  }`}>
                    {agent.name}
                  </h4>
                  <p className={`text-xs ${
                    isActive ? 'text-blue-600' : isCompleted ? 'text-green-600' : 'text-slate-500'
                  }`}>
                    {agent.description}
                  </p>

                  {/* Processing indicator */}
                  {isActive && (
                    <div className="mt-2">
                      <div className="flex space-x-1 justify-center">
                        <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce"></div>
                        <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="mt-6 text-center">
          <p className="text-xs text-slate-500">
            🚀 Powered by LangChain Multi-Agent Architecture
          </p>
        </div>
      </div>
    </div>
  );
}