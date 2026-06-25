import Link from "next/link";

export const metadata = {
  title: "More Veterinary Dental CE — PerioVive CE",
  description:
    "Additional places to find veterinary dental continuing education: specialty practices, professional organizations, and board-certified specialist directories.",
};

type Provider = {
  name: string;
  category: string;
  blurb: string;
  detail: string;
  website: string;
  cta: string;
};

const PRACTICES: Provider[] = [
  {
    name: "Pet Dental Specialists",
    category: "Specialty Practice",
    blurb:
      "A board-certified veterinary dental and oral surgery practice that provides continuing education to veterinarians and their teams.",
    detail: "Courses are posted directly on their practice site.",
    website: "https://pdsvet.com",
    cta: "Visit Pet Dental Specialists",
  },
  {
    name: "Silo Academy Education Center",
    category: "Specialty Practice",
    blurb:
      "Hands-on veterinary dental wet labs and lectures taught in a dedicated training facility. Most classes are RACE-approved.",
    detail: "Registration and upcoming dates are listed on their site.",
    website: "https://siloacademy.com",
    cta: "Visit Silo Academy",
  },
];

const ORGANIZATIONS: Provider[] = [
  {
    name: "American Veterinary Dental College (AVDC)",
    category: "Specialist Directory",
    blurb:
      "The AVMA-recognized certifying board for veterinary dentistry in North America. Its public directory lists board-certified veterinary dental specialists, many of whom teach and offer CE.",
    detail: "Use the directory to find a board-certified specialist near you.",
    website: "https://avdc.org/find-a-veterinary-specialist/",
    cta: "Find a Specialist",
  },
  {
    name: "Academy of Veterinary Dentistry (AVD)",
    category: "Professional Organization",
    blurb:
      "An international organization of veterinarians with a special interest in animal dental care. AVD Fellows complete additional training and a credentialing examination.",
    detail: "Browse the Fellow directory to find credentialed members.",
    website: "https://www.avdonline.org",
    cta: "Visit the Academy",
  },
  {
    name: "Foundation for Veterinary Dentistry",
    category: "Professional Organization",
    blurb:
      "A nonprofit that supports veterinary dental education and research and helps fund the annual Veterinary Dental Forum.",
    detail: "Learn about the Forum and the educational initiatives they support.",
    website: "https://veterinarydentistry.org",
    cta: "Visit the Foundation",
  },
];

const SEASONAL: Provider[] = [
  {
    name: "Veterinary Dental Forum",
    category: "Annual Conference",
    blurb:
      "The premier annual veterinary dentistry conference, featuring lectures, wet labs, and the field's largest gathering of dental professionals.",
    detail: "Each year's program is published ahead of the event.",
    website: "https://veterinarydentalforum.org",
    cta: "See the Forum",
  },
  {
    name: "Learn Veterinary Dentistry",
    category: "Technician CE",
    blurb:
      "Continuing education for veterinary technicians and assistants, covering anesthesia, radiograph positioning, charting, and instrument skills, taught by a VTS (Dentistry).",
    detail: "New course dates are announced periodically on their site.",
    website: "https://learnvetdentistry.com",
    cta: "Visit Learn Vet Dentistry",
  },
  {
    name: "Vet CE You'll Use",
    category: "On-Demand Courses",
    blurb:
      "Short, focused on-demand veterinary dentistry courses from Dr. Jennifer Mathis, DVM, DAVDC, covering practical topics for general practice teams.",
    detail: "Browse and enroll in individual courses on their site.",
    website: "https://courses.vetceyoulluse.com",
    cta: "Visit Vet CE You'll Use",
  },
];

export default function OtherProvidersPage() {
  return (
    <main className="bg-white">
      {/* ===== HERO ===== */}
      <section className="max-w-6xl mx-auto px-6 py-20 md:py-24">
        <p className="text-brand-500 font-semibold uppercase tracking-wide text-sm">
          More Dental CE
        </p>
        <h1 className="mt-4 text-4xl md:text-6xl font-extrabold text-ink-900 max-w-3xl">
          More places to keep learning<span className="text-brand-500">.</span>
        </h1>
        <p className="mt-6 text-lg text-ink-600 max-w-2xl">
          Our catalog gathers dental CE from across the profession, but it is not
          the whole story. The specialty practices and organizations below are
          excellent sources of veterinary dental education worth knowing about.
        </p>
      </section>

      {/* ===== SPECIALTY PRACTICES ===== */}
      <section className="bg-brand-50/30 border-y border-brand-100">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <h2 className="text-2xl md:text-3xl font-extrabold text-ink-900">
            Specialty practices<span className="text-brand-500">.</span>
          </h2>
          <p className="mt-3 text-ink-600 max-w-2xl">
            Dental and oral surgery practices that run their own hands-on courses
            and wet labs.
          </p>
          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {PRACTICES.map((p) => (
              <ProviderCard key={p.name} provider={p} />
            ))}
          </div>
        </div>
      </section>

      {/* ===== ORGANIZATIONS & DIRECTORIES ===== */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <h2 className="text-2xl md:text-3xl font-extrabold text-ink-900">
          Organizations &amp; directories<span className="text-brand-500">.</span>
        </h2>
        <p className="mt-3 text-ink-600 max-w-2xl">
          Professional bodies and specialist directories that point you to
          credentialed instructors and field-wide events.
        </p>
        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {ORGANIZATIONS.map((p) => (
            <ProviderCard key={p.name} provider={p} />
          ))}
        </div>
      </section>

      {/* ===== WORTH CHECKING BACK ===== */}
      <section className="bg-brand-50/30 border-y border-brand-100">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <h2 className="text-2xl md:text-3xl font-extrabold text-ink-900">
            Worth checking back<span className="text-brand-500">.</span>
          </h2>
          <p className="mt-3 text-ink-600 max-w-2xl">
            These providers run excellent dental CE but publish their schedules
            on their own cycle. Check their sites for the latest dates.
          </p>
          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {SEASONAL.map((p) => (
              <ProviderCard key={p.name} provider={p} />
            ))}
          </div>
        </div>
      </section>

      {/* ===== TRAINERS CROSS-LINK ===== */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="rounded-2xl border border-ink-100 bg-white p-10 md:p-12 shadow-card">
          <p className="text-brand-500 font-semibold uppercase tracking-wide text-sm">
            Hands-on Training
          </p>
          <h2 className="mt-3 text-2xl md:text-3xl font-extrabold text-ink-900">
            Looking for in-clinic instruction<span className="text-brand-500">?</span>
          </h2>
          <p className="mt-4 text-ink-600 max-w-2xl">
            Some specialists bring customized dental training directly to your
            practice team. We feature them on our trainers page.
          </p>
          <div className="mt-6">
            <Link
              href="/trainers"
              className="inline-flex items-center rounded-pill bg-brand-500 hover:bg-brand-600 text-white px-6 py-3 text-sm font-semibold transition-colors"
            >
              See Hands-on Trainers →
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

// ===== Subcomponents =====

function ProviderCard({ provider }: { provider: Provider }) {
  return (
    <article className="flex flex-col rounded-2xl border border-ink-100 bg-white p-6 shadow-card hover:shadow-cardHover transition-shadow">
      <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
        {provider.category}
      </p>
      <h3 className="mt-2 text-xl font-bold text-ink-900 leading-snug">
        {provider.name}
      </h3>
      <p className="mt-4 text-sm text-ink-600 leading-relaxed flex-1">
        {provider.blurb}
      </p>
      <div className="mt-5 pt-5 border-t border-ink-100">
        <p className="text-sm text-ink-700">{provider.detail}</p>
      </div>
      <div className="mt-5">
        <a
          href={provider.website}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-semibold text-brand-600 hover:text-brand-700 transition-colors"
        >
          {provider.cta} →
        </a>
      </div>
    </article>
  );
}