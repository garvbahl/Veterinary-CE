"use client";

import Link from "next/link";
import { useState } from "react";

const NAV_LINKS = [
  { label: "Browse CE", href: "/listings" },
  { label: "Trainers", href: "/trainers" },
  { label: "More CE", href: "/other-providers" },
];

export default function Header() {
  const [open, setOpen] = useState(false);

  return (
    <header className="border-b border-ink-100 bg-white sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link
          href="/"
          className="flex flex-col leading-tight"
          onClick={() => setOpen(false)}
        >
          <span className="text-ink-900 font-extrabold text-xl tracking-tight">
            Veterinary Dental CE
            <span className="text-brand-500">.</span>
          </span>
          <span className="text-[11px] font-medium text-ink-500 tracking-tight flex items-center gap-1">
            by
            <span className="font-extrabold tracking-tight text-[13px]">
              <span className="text-ink-900">PERIO</span>
              <span className="text-[#0FB4E7]">VIVE</span>
              <span className="align-super text-[8px] text-ink-400">™</span>
            </span>
          </span>
        </Link>

        {/* Desktop nav links */}
        <nav className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-ink-600 hover:text-ink-900 font-medium transition-colors"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Desktop CTA */}
        <Link
          href="/listings"
          className="hidden md:inline-block rounded-pill bg-brand-500 hover:bg-brand-600 text-white px-5 py-2 font-semibold text-sm transition-colors"
        >
          Browse Listings →
        </Link>

        {/* Mobile hamburger button */}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          className="md:hidden inline-flex items-center justify-center w-10 h-10 -mr-2 text-ink-900"
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            {open ? (
              <>
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </>
            ) : (
              <>
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </>
            )}
          </svg>
        </button>
      </div>

      {/* Mobile dropdown menu */}
      {open && (
        <nav className="md:hidden border-t border-ink-100 bg-white px-6 py-4 flex flex-col gap-1">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setOpen(false)}
              className="py-2 text-ink-700 hover:text-ink-900 font-medium transition-colors"
            >
              {link.label}
            </Link>
          ))}
          <Link
            href="/listings"
            onClick={() => setOpen(false)}
            className="mt-2 rounded-pill bg-brand-500 hover:bg-brand-600 text-white px-5 py-2.5 font-semibold text-sm text-center transition-colors"
          >
            Browse Listings →
          </Link>
        </nav>
      )}
    </header>
  );
}