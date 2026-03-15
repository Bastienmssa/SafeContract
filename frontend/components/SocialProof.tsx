export function SocialProof() {
  const placeholders = Array(5).fill(null);

  return (
    <section className="px-4 sm:px-6 lg:px-8 py-12 border-y border-slate-200">
      <div className="max-w-5xl mx-auto">
        <p className="text-center text-sm text-slate-500 mb-8">
          Ils nous font confiance
        </p>
        <div className="flex flex-wrap items-center justify-center gap-12 lg:gap-16">
          {placeholders.map((_, i) => (
            <div
              key={i}
              className="h-8 w-24 bg-slate-100 rounded border border-slate-200"
              aria-hidden
            />
          ))}
        </div>
      </div>
    </section>
  );
}
