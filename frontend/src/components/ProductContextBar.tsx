"use client";

import { useState } from "react";
import { ProductContext } from "@/types";

interface Props {
  product: ProductContext;
  onUpdate: (product: ProductContext) => void;
}

export default function ProductContextBar({ product, onUpdate }: Props) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(product.name);
  const [url, setUrl] = useState(product.url);

  const handleSave = () => {
    onUpdate({ name, url });
    setEditing(false);
  };

  return (
    <div className="flex items-center justify-between px-6 py-3 bg-slate-900/80 border-b border-slate-800">
      <div className="flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
        {editing ? (
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">Analysing:</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              autoFocus
            />
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="product URL"
              className="bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-400 focus:outline-none focus:border-indigo-500"
            />
            <button onClick={handleSave} className="text-xs text-indigo-400 hover:text-indigo-300">
              Save
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">Analysing:</span>
            <span className="text-sm font-medium text-slate-200">[{product.name}]</span>
            <span className="text-sm text-slate-500">{product.url}</span>
          </div>
        )}
      </div>
      {!editing && (
        <button
          onClick={() => setEditing(true)}
          className="text-xs text-slate-500 hover:text-slate-300 border border-slate-700 rounded px-2 py-1 hover:border-slate-500 transition-colors"
        >
          Change product
        </button>
      )}
    </div>
  );
}
