"use client";

import { motion } from "framer-motion";

interface Props {
  chips: string[];
  onSelect: (chip: string) => void;
}

export default function SuggestedChips({ chips, onSelect }: Props) {
  return (
    <div className="flex flex-wrap gap-2 justify-center">
      {chips.map((chip, i) => (
        <motion.button
          key={chip}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.1, duration: 0.3 }}
          onClick={() => onSelect(chip)}
          className="px-4 py-2 rounded-full bg-slate-800/60 border border-slate-700/50 text-sm text-slate-300 hover:bg-indigo-500/20 hover:border-indigo-500/40 hover:text-indigo-300 transition-all duration-200 cursor-pointer"
        >
          {chip}
        </motion.button>
      ))}
    </div>
  );
}
