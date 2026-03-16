import Link from "next/link";

const links = [
  ["Dashboard", "/dashboard"],
  ["Inbox", "/inbox"],
  ["Analytics", "/analytics"],
  ["AI Assistant", "/ai-assistant"],
  ["Connected Platforms", "/connected-platforms"],
  ["Settings", "/settings"],
];

export function NavigationSidebar() {
  return (
    <aside className="w-64 rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <h1 className="mb-6 text-xl font-semibold">Dating Aggregator</h1>
      <nav className="space-y-2">
        {links.map(([label, href]) => (
          <Link key={href} href={href} className="block rounded-xl px-3 py-2 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800">
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
