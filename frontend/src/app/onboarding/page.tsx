export default function Page() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 p-6 dark:bg-zinc-950">
      <div className="w-full max-w-md rounded-3xl border border-zinc-200 bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <h1 className="mb-2 text-2xl font-semibold">Onboarding</h1>
        <p className="mb-6 text-sm text-zinc-500">Connect platforms and configure profile preferences.</p>
        <form className="space-y-3">
          <input placeholder="Email" className="w-full rounded-xl border border-zinc-300 px-3 py-2 dark:border-zinc-700" />
          <input placeholder="Password" type="password" className="w-full rounded-xl border border-zinc-300 px-3 py-2 dark:border-zinc-700" />
          <button className="w-full rounded-xl bg-zinc-900 py-2 text-white dark:bg-zinc-100 dark:text-zinc-900">Continue</button>
        </form>
      </div>
    </div>
  );
}
