"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

export function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-zinc-200 bg-white/90 p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900/90"
    >
      <h3 className="mb-2 text-sm font-semibold text-zinc-500 dark:text-zinc-400">{title}</h3>
      {children}
    </motion.section>
  );
}
