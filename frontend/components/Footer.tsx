import Link from "next/link";

const links = [
  { href: "#cgu", label: "CGU" },
  { href: "#confidentialite", label: "Confidentialité" },
  { href: "#mentions", label: "Mentions légales" },
];

export function Footer() {
  return (
    <footer className="border-t border-light-300 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <p className="text-sm text-primary-600">
          © {new Date().getFullYear()} SafeContract
        </p>
        <nav className="flex gap-6">
          {links.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className="text-sm text-primary-600 hover:text-primary-400 transition-colors"
            >
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}
