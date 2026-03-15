import { Shield, ScanSearch, FileCheck } from "lucide-react";

const features = [
  {
    icon: Shield,
    title: "Sécurisation des actifs",
    description:
      "Protégez les fonds de vos utilisateurs avec des contrats validés et audités.",
  },
  {
    icon: ScanSearch,
    title: "Détection de vulnérabilités",
    description:
      "Identification automatique des failles avant le déploiement en production.",
  },
  {
    icon: FileCheck,
    title: "Rapports d'audit instantanés",
    description:
      "Documentation complète et traçable pour vos équipes et investisseurs.",
  },
];

export function ProblemSolution() {
  return (
    <section className="px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
      <div className="max-w-5xl mx-auto">
        <div className="grid sm:grid-cols-3 gap-12 lg:gap-16">
          {features.map(({ icon: Icon, title, description }) => (
            <div key={title} className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-md border border-slate-200 text-primary-500 mb-4">
                <Icon className="w-5 h-5" strokeWidth={1.5} />
              </div>
              <h3 className="text-base font-semibold text-primary-900">
                {title}
              </h3>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                {description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
