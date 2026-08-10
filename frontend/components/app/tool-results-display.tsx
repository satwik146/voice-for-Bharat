'use client';

import { useDataChannel } from '@livekit/components-react';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';

export function ToolResultsDisplay() {
  const [results, setResults] = useState<any[]>([]);
  const { message } = useDataChannel('tool_results');

  useEffect(() => {
    if (message) {
      try {
        const decoded = new TextDecoder().decode(message.payload);
        const parsed = JSON.parse(decoded);
        setResults((prev) => [parsed, ...prev].slice(0, 3));
      } catch (e) {
        console.error("Failed to parse tool result", e);
      }
    }
  }, [message]);

  return (
    <div className="absolute top-4 right-4 z-50 flex flex-col gap-3 max-w-sm pointer-events-none">
      <AnimatePresence>
        {results.map((res, i) => (
          <motion.div
            key={`${res.tool}-${Date.now()}-${i}`}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="bg-zinc-900/90 text-white backdrop-blur-md border border-zinc-700/50 p-4 rounded-xl shadow-2xl text-sm flex flex-col gap-1 pointer-events-auto"
          >
            <div className="font-bold text-xs uppercase tracking-wider text-zinc-400 mb-1 flex items-center justify-between">
              <span>{res.tool === 'lookup_word_definition' ? '📚 Dictionary Lookup' : '✨ Grammar Check'}</span>
              {res.status === 'offline_fallback' && (
                <span className="text-red-400 bg-red-400/10 px-1.5 py-0.5 rounded text-[10px]">Offline</span>
              )}
            </div>
            
            {res.tool === 'lookup_word_definition' && (
              <>
                <div className="text-lg font-semibold text-blue-200">{res.word}</div>
                {res.definition && <div className="text-zinc-200 mt-1 leading-relaxed">{res.definition}</div>}
              </>
            )}
            
            {res.tool === 'check_sentence_grammar' && (
              <>
                <div className="italic text-zinc-300">"{res.sentence}"</div>
                <div className="mt-2">
                  {res.is_correct ? (
                    <span className="text-green-400 font-medium flex items-center gap-1">✓ Grammatically Correct</span>
                  ) : (
                    <span className="text-orange-400 font-medium">⚠ Needs Improvement</span>
                  )}
                </div>
              </>
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
