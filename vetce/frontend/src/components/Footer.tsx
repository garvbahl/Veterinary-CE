"use client";

import Link from "next/link";
import { useState } from "react";

import { subscribeEmail } from "@/lib/api";
import { ApiError } from "@/lib/api";

const FOOTER_COLUMNS = [
  {
    title: "Browse",
    links: [
      { label: "All Listings", href: "/listings" },
      { label: "Upcoming Events", href: "/listings?sort=starts_at&order=asc" },
      { label: "Trainers", href: "/trainers" },
      { label: "More Dental CE", href: "/other-providers" },
    ],
  },
  {
    title: "Periovive",
    links: [
      { label: "Main Site", href: "https://www.periovive.com" },
      { label: "Contact", href: "mailto:hello@periovive.com" },
    ],
  },
];

type SubscribeState =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "success"; alreadySubscribed: boolean }
  | { kind: "error"; message: string };

export default function Footer() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<SubscribeState>({ kind: "idle" });

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (state.kind === "submitting") return;

    const trimmed = email.trim();
    if (!trimmed) {
      setState({ kind: "error", message: "Please enter an email address." });
      return;
    }

    setState({ kind: "submitting" });

    try {
      const result = await subscribeEmail(trimmed);
      setState({ kind: "success", alreadySubscribed: result.already_subscribed });
      setEmail("");
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Something went wrong. Please try again.";
      setState({ kind: "error", message });
    }
  }

  const isSubmitting = state.kind === "submitting";

  return (
    <>
      {/* Stay in the loop section — Periovive style */}
      <section className="bg-white border-t border-ink-100">
        <div className="max-w-6xl mx-auto px-6 py-20 text-center">
          <h2 className="text-4xl font-extrabold text-ink-900">
            Stay in the loop<span className="text-brand-500">.</span>
          </h2>
          <p className="mt-4 text-lg text-ink-600 max-w-xl mx-auto">
            New providers, new CE drops, new features. Once a month, nothing more.
          </p>

          {state.kind === "success" ? (
            <div className="mt-8 max-w-md mx-auto rounded-2xl bg-brand-50 px-6 py-5 ring-1 ring-brand-200">
              <p className="text-brand-700 font-semibold">
                {state.alreadySubscribed
                  ? "You're already on the list."
                  : "Thanks! You're subscribed."}
              </p>
              <p className="mt-1 text-sm text-brand-600">
                {state.alreadySubscribed
                  ? "We'll keep you posted on new providers and features."
                  : "Watch your inbox for the next CE roundup."}
              </p>
            </div>
          ) : (
            <>
              <form
                className="mt-8 flex flex-col sm:flex-row gap-3 max-w-md mx-auto"
                onSubmit={handleSubmit}
                noValidate
              >
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@yourclinic.com"
                  disabled={isSubmitting}
                  required
                  className="flex-1 rounded-pill border border-ink-200 px-6 py-3 text-ink-900 placeholder:text-ink-400 focus:outline-none focus:border-brand-500 disabled:bg-ink-50 disabled:cursor-not-allowed"
                />
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-pill bg-brand-500 hover:bg-brand-600 disabled:bg-brand-300 disabled:cursor-not-allowed text-white px-8 py-3 font-semibold transition-colors"
                >
                  {isSubmitting ? "Subscribing..." : "Subscribe"}
                </button>
              </form>

              {state.kind === "error" && (
                <p className="mt-4 text-sm text-red-600 max-w-md mx-auto">
                  {state.message}
                </p>
              )}
            </>
          )}
        </div>
      </section>

      {/* Dark footer */}
      <footer className="bg-ink-900 text-ink-200">
          <div className="max-w-6xl mx-auto px-6 py-16 grid grid-cols-2 md:grid-cols-3 gap-8">
          {/* Brand column */}
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-baseline gap-1 text-white font-extrabold text-xl tracking-tight">
              <span>PerioVive CE</span>
              <span className="text-brand-400">.</span>
            </div>
            <p className="mt-4 text-sm leading-relaxed">
              Aggregated veterinary dental continuing education
              from the providers you trust.
            </p>
          </div>

          {/* Link columns */}
          {FOOTER_COLUMNS.map((column) => (
            <div key={column.title}>
              <h3 className="text-white font-semibold mb-4">{column.title}</h3>
              <ul className="space-y-3">
                {column.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-ink-200 hover:text-white transition-colors"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Copyright row */}
        <div className="border-t border-ink-600 py-6">
          <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-ink-400">
            <p>© {new Date().getFullYear()} PerioVive CE. A Periovive Analytics property.</p>
            <p>Listings aggregated from publicly available sources.</p>
          </div>
        </div>
      </footer>
    </>
  );
}