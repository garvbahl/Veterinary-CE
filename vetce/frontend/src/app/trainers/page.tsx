import Link from "next/link";

export const metadata = {
  title: "Hands-on Dental Trainers — PerioVive CE",
  description:
    "Veterinary dental specialists offering in-clinic training and customized hands-on instruction for your practice team.",
};

type Trainer = {
  name: string;
  credentials: string;
  org: string;
  blurb: string;
  region: string;
  website: string;
};

const TRAINERS: Trainer[] = [
  {
    name: "Benita Altier",
    credentials: "LVT, VTS (Dentistry)",
    org: "Pawsitive Dental Education",
    blurb:
      "In-hospital training and conference instruction across the US and Canada. Tailored programs for vet teams looking to build a dental service line.",
    region: "United States & Canada",
    website: "https://pawsitivedental.com",
  },
  {
    name: "RVT Dental Specialist",
    credentials: "RVT, VTS (Dentistry)",
    org: "Tooth 30",
    blurb:
      "Customized in-clinic dental training programs for veterinary teams. Hands-on instruction tailored to your team's case mix and skill level.",
    region: "Calgary, AB",
    website: "https://tooth30tech.com",
  },
  {
    name: "Dr. Amy Thomson",
    credentials: "Board-Certified Veterinary Dentist & Oral Surgeon",
    org: "Toothy Thomson",
    blurb:
      "Mobile specialty service bringing advanced dental and oral surgery directly to general practice clinics across the Greater Toronto Area.",
    region: "Toronto, Etobicoke, Mississauga, Oakville, Brampton, Burlington",
    website: "https://toothythomson.ca",
  },
];

export default function TrainersPage() {
  return (
    <main className="bg-white">
      {/* ===== HERO ===== */}
      <section className="max-w-6xl mx-auto px-6 py-20 md:py-24">
        <p className="text-brand-500 font-semibold uppercase tracking-wide text-sm">
          Hands-on Training
        </p>
        <h1 className="mt-4 text-4xl md:text-6xl font-extrabold text-ink-900 max-w-3xl">
          Bring expertise into your clinic<span className="text-brand-500">.</span>
        </h1>
        <p className="mt-6 text-lg text-ink-600 max-w-2xl">
          Not every CE opportunity lives on a catalog page. Some of the most
          experienced dental specialists offer customized, in-hospital training
          for your whole team. We feature them here so you can find them.
        </p>
      </section>

      {/* ===== TRAINER CARDS ===== */}
      <section className="bg-brand-50/30 border-y border-brand-100">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {TRAINERS.map((t) => (
              <TrainerCard key={t.org} trainer={t} />
            ))}
          </div>
        </div>
      </section>

      {/* ===== AVDT DIRECTORY ===== */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="rounded-2xl border border-ink-100 bg-white p-10 md:p-12 shadow-card">
          <p className="text-brand-500 font-semibold uppercase tracking-wide text-sm">
            Directory
          </p>
          <h2 className="mt-3 text-2xl md:text-3xl font-extrabold text-ink-900">
            Find a VTS (Dentistry) trainer near you<span className="text-brand-500">.</span>
          </h2>
          <p className="mt-4 text-ink-600 max-w-2xl">
            The Academy of Veterinary Dental Technicians maintains a directory
            of board-credentialed members. Many offer in-hospital training in
            addition to their clinical work.
          </p>
          <div className="mt-6">
            <a
              href="https://avdt.us/members"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center rounded-pill bg-brand-500 hover:bg-brand-600 text-white px-6 py-3 text-sm font-semibold transition-colors"
            >
              Browse AVDT Members →
            </a>
          </div>
        </div>
      </section>

      {/* ===== CTA ===== */}
      
    </main>
  );
}

// ===== Subcomponents =====

function TrainerCard({ trainer }: { trainer: Trainer }) {
  return (
    <article className="flex flex-col rounded-2xl border border-ink-100 bg-white p-6 shadow-card hover:shadow-cardHover transition-shadow">
      <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
        {trainer.org}
      </p>
      <h3 className="mt-2 text-xl font-bold text-ink-900 leading-snug">
        {trainer.name}
      </h3>
      <p className="mt-1 text-sm font-medium text-ink-500">
        {trainer.credentials}
      </p>
      <p className="mt-4 text-sm text-ink-600 leading-relaxed flex-1">
        {trainer.blurb}
      </p>
      <div className="mt-5 pt-5 border-t border-ink-100">
        <p className="text-xs font-semibold uppercase tracking-wide text-ink-400">
          Serves
        </p>
        <p className="mt-1 text-sm text-ink-700">{trainer.region}</p>
      </div>
      <div className="mt-5">
        <a
          href={trainer.website}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-semibold text-brand-600 hover:text-brand-700 transition-colors"
        >
          Visit website →
        </a>
      </div>
    </article>
  );
}