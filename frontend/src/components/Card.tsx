export function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-line bg-white p-5 shadow-soft">
      <h2 className="mb-3 text-sm font-semibold text-ink">{title}</h2>
      {children}
    </section>
  );
}
