import Link from "next/link";

const plans = [
  {
    name: "Starter",
    price: "Gratuit",
    description: "Pour découvrir et tester l'analyse de vos premiers contrats.",
    features: ["1 analyse par semaine", "Rapport basique", "Support communautaire"],
    cta: "Commencer",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "Sur devis",
    description: "Pour les équipes qui déploient régulièrement.",
    features: [
      "Analyses illimitées",
      "Rapports détaillés PDF",
      "Support prioritaire",
      "API dédiée",
    ],
    cta: "Nous contacter",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "Sur devis",
    description: "Pour les protocoles à fort volume et exigences réglementaires.",
    features: [
      "Tout Pro inclus",
      "Audits personnalisés",
      "SLA garanti",
      "Formation équipe",
    ],
    cta: "Prendre RDV",
    highlighted: false,
  },
];

export function Pricing() {
  return (
    <section className="px-4 sm:px-6 lg:px-8 py-24 lg:py-32 bg-slate-50/50">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-2xl font-semibold text-primary-900 text-center mb-4">
          Plans tarifaires
        </h2>
        <p className="text-slate-600 text-center mb-16 max-w-xl mx-auto">
          Choisissez l&apos;offre adaptée à vos besoins.
        </p>
        <div className="grid md:grid-cols-3 gap-6">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`relative rounded-xl border p-6 bg-white ${
                plan.highlighted
                  ? "border-primary-400 ring-1 ring-primary-400/20"
                  : "border-slate-200"
              }`}
            >
              {plan.highlighted && (
                <p className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 text-xs font-medium text-primary-600 bg-primary-50 rounded-full border border-primary-200">
                  Recommandé
                </p>
              )}
              <h3 className="text-lg font-semibold text-primary-900">
                {plan.name}
              </h3>
              <p className="mt-2 text-2xl font-semibold text-primary-900">
                {plan.price}
              </p>
              <p className="mt-2 text-sm text-slate-600">{plan.description}</p>
              <ul className="mt-6 space-y-3">
                {plan.features.map((f) => (
                  <li key={f} className="text-sm text-slate-600 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary-400 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="#analyse"
                className={`mt-8 block w-full py-2.5 text-center text-sm font-medium rounded-md border transition-colors ${
                  plan.highlighted
                    ? "text-white bg-primary-500 hover:bg-primary-600 border-primary-500"
                    : "text-slate-700 bg-white hover:bg-slate-50 border-slate-200"
                }`}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
