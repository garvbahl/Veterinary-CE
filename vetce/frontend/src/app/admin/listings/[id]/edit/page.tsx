"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ApiError,
  fetchListing,
  updateListing,
  type ListingUpdatePayload,
} from "@/lib/api";
import { CATEGORY_OPTIONS } from "@/lib/categories";
import type { Listing } from "@/lib/types";

const AUDIENCE_OPTIONS = [
  { value: "vets", label: "Veterinarians" },
  { value: "techs", label: "Technicians" },
  { value: "vets and techs", label: "Both" },
];

const FORMAT_OPTIONS = [
  { value: "live", label: "Live" },
  { value: "on_demand", label: "On Demand" },
  { value: "hybrid", label: "Hybrid" },
];

const STATUS_OPTIONS = [
  { value: "active", label: "Active (visible)" },
  { value: "hidden", label: "Hidden" },
];

export default function EditListingPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const listingId = Number(params.id);

  const [listing, setListing] = useState<Listing | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Form state — initialised from the loaded listing.
  const [title, setTitle] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [description, setDescription] = useState("");
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [creditHours, setCreditHours] = useState("");
  const [raceApproved, setRaceApproved] = useState(false);
  const [audience, setAudience] = useState("");
  const [format, setFormat] = useState("");
  const [presenter, setPresenter] = useState("");
  const [registrationUrl, setRegistrationUrl] = useState("");
  const [cost, setCost] = useState("");
  const [subjectCategory, setSubjectCategory] = useState("");
  const [status, setStatus] = useState("active");

  useEffect(() => {
    if (!Number.isFinite(listingId)) {
      setLoadError("Invalid listing id in URL.");
      return;
    }
    fetchListing(listingId)
      .then((row) => {
        setListing(row);
        setTitle(row.title);
        setSourceUrl(row.source_url);
        setDescription(row.description ?? "");
        setStartsAt(row.starts_at ?? "");
        setEndsAt(row.ends_at ?? "");
        setCreditHours(row.credit_hours != null ? String(row.credit_hours) : "");
        setRaceApproved(row.race_approved === true);
        setAudience(row.audience ?? "");
        setFormat(row.format ?? "");
        setPresenter(row.presenter ?? "");
        setRegistrationUrl(row.registration_url ?? "");
        setCost(row.cost ?? "");
        setSubjectCategory(row.subject_category ?? "");
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          router.push("/admin/login");
          return;
        }
        setLoadError((err as Error).message);
      });
  }, [listingId, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);

    if (!title.trim()) {
      setSubmitError("Title is required.");
      return;
    }
    if (!sourceUrl.trim()) {
      setSubmitError("Source URL is required.");
      return;
    }

    // Build payload of values that differ from "empty/unset". Empty strings
    // become null so the backend can clear fields when needed.
    const payload: ListingUpdatePayload = {
      title: title.trim(),
      source_url: sourceUrl.trim(),
      description: description.trim() || null,
      starts_at: startsAt || null,
      ends_at: endsAt || null,
      format: format || null,
      cost: cost.trim() || null,
      race_approved: raceApproved ? true : null,
      credit_hours: creditHours ? Number(creditHours) : null,
      presenter: presenter.trim() || null,
      audience: audience || null,
      registration_url: registrationUrl.trim() || null,
      subject_category: subjectCategory || null,
      status,
    };

    setSubmitting(true);
    try {
      await updateListing(listingId, payload);
      router.push(`/listings/${listingId}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.push("/admin/login");
        return;
      }
      setSubmitError((err as Error).message);
      setSubmitting(false);
    }
  }

  if (loadError) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="text-2xl font-bold text-ink-900">Edit Listing</h1>
        <div className="mt-6 rounded-2xl bg-red-50 px-6 py-4 ring-1 ring-red-200">
          <div className="font-semibold text-red-700">Could not load listing.</div>
          <div className="mt-1 text-sm text-red-600">{loadError}</div>
        </div>
      </main>
    );
  }

  if (!listing) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <p className="text-ink-500">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-ink-900">
            Edit Listing<span className="text-brand-500">.</span>
          </h1>
          <p className="mt-1 text-sm text-ink-500">
            {listing.provider} · {listing.source}
          </p>
        </div>
        <Link
          href="/admin"
          className="text-sm font-semibold text-brand-600 hover:text-brand-700 transition-colors"
        >
          Back to Admin
        </Link>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Section title="Required">
          <Field label="Title" required>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className={inputClass}
              required
            />
          </Field>

          <Field label="Source URL" required>
            <input
              type="url"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              className={inputClass}
              required
            />
          </Field>

          <Field label="Status" hint="Hidden listings stay in the database but don't show publicly.">
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className={inputClass}
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </Field>
        </Section>

        <Section title="Schedule">
          <Field label="Start date">
            <input
              type="date"
              value={startsAt}
              onChange={(e) => setStartsAt(e.target.value)}
              className={inputClass}
            />
          </Field>

          <Field label="End date">
            <input
              type="date"
              value={endsAt}
              onChange={(e) => setEndsAt(e.target.value)}
              className={inputClass}
            />
          </Field>

          <Field label="Format">
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              className={inputClass}
            >
              <option value="">— pick one —</option>
              {FORMAT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </Field>
        </Section>

        <Section title="Content">
          <Field label="Description">
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className={inputClass}
              rows={4}
            />
          </Field>

          <Field label="Credit hours">
            <input
              type="number"
              step="0.5"
              min="0"
              value={creditHours}
              onChange={(e) => setCreditHours(e.target.value)}
              className={inputClass}
            />
          </Field>

          <Field label="RACE approved">
            <label className="flex items-center gap-2 text-sm text-ink-700">
              <input
                type="checkbox"
                checked={raceApproved}
                onChange={(e) => setRaceApproved(e.target.checked)}
                className="accent-brand-500"
              />
              Listing is RACE-approved
            </label>
          </Field>

          <Field label="Audience">
            <select
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
              className={inputClass}
            >
              <option value="">— pick one —</option>
              {AUDIENCE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Subject category">
            <select
              value={subjectCategory}
              onChange={(e) => setSubjectCategory(e.target.value)}
              className={inputClass}
            >
              <option value="">— none —</option>
              {CATEGORY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Presenter">
            <input
              type="text"
              value={presenter}
              onChange={(e) => setPresenter(e.target.value)}
              className={inputClass}
            />
          </Field>

          <Field label="Registration URL">
            <input
              type="url"
              value={registrationUrl}
              onChange={(e) => setRegistrationUrl(e.target.value)}
              className={inputClass}
            />
          </Field>

          <Field label="Cost">
            <input
              type="text"
              value={cost}
              onChange={(e) => setCost(e.target.value)}
              className={inputClass}
            />
          </Field>
        </Section>

        {submitError && (
          <div className="rounded-xl bg-red-50 px-4 py-3 ring-1 ring-red-200 text-sm text-red-700">
            {submitError}
          </div>
        )}

        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-pill bg-brand-500 hover:bg-brand-600 disabled:opacity-60 text-white px-8 py-3 font-semibold transition-colors"
          >
            {submitting ? "Saving…" : "Save changes"}
          </button>
          <Link
            href={`/listings/${listingId}`}
            className="text-sm font-semibold text-ink-500 hover:text-ink-800 transition-colors"
          >
            Cancel
          </Link>
        </div>
      </form>
    </main>
  );
}

// ===== Subcomponents =====

const inputClass =
  "w-full rounded-lg border border-ink-200 px-3 py-2 text-sm focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 transition-all";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-ink-100 bg-white p-6 shadow-card">
      <h2 className="text-sm font-bold text-ink-900 uppercase tracking-wide mb-4">
        {title}
      </h2>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function Field({
  label,
  required,
  hint,
  children,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-semibold text-ink-700 mb-1.5">
        {label}
        {required && <span className="ml-1 text-brand-500">*</span>}
      </label>
      {children}
      {hint && <p className="mt-1 text-xs text-ink-500">{hint}</p>}
    </div>
  );
}