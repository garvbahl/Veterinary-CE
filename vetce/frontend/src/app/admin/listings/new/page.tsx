"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ApiError,
  createListing,
  fetchManualSources,
  type ListingCreatePayload,
  type ManualSource,
} from "@/lib/api";
import { CATEGORY_OPTIONS } from "@/lib/categories";

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

export default function NewListingPage() {
  const router = useRouter();
  const [sources, setSources] = useState<ManualSource[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [sourceId, setSourceId] = useState<string>("");
  const [title, setTitle] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [description, setDescription] = useState("");
  const [onDemand, setOnDemand] = useState(false);
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

  // Load manual sources on mount.
  useEffect(() => {
    fetchManualSources()
      .then((rows) => {
        setSources(rows);
        if (rows.length > 0) setSourceId(String(rows[0].id));
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          router.push("/admin/login");
          return;
        }
        setLoadError((err as Error).message);
      });
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);

    if (!sourceId) {
      setSubmitError("Pick a source.");
      return;
    }
    if (!title.trim()) {
      setSubmitError("Title is required.");
      return;
    }
    if (!sourceUrl.trim()) {
      setSubmitError("Source URL is required.");
      return;
    }
    if (!onDemand && !startsAt) {
      setSubmitError("Either set a start date or check 'On demand'.");
      return;
    }

    const payload: ListingCreatePayload = {
      source_id: Number(sourceId),
      title: title.trim(),
      source_url: sourceUrl.trim(),
      description: description.trim() || null,
      starts_at: onDemand ? null : startsAt || null,
      ends_at: onDemand ? null : endsAt || null,
      format: onDemand ? "on_demand" : format || null,
      cost: cost.trim() || null,
      race_approved: raceApproved ? true : null,
      credit_hours: creditHours ? Number(creditHours) : null,
      presenter: presenter.trim() || null,
      audience: audience || null,
      registration_url: registrationUrl.trim() || null,
      subject_category: subjectCategory || null,
    };

    setSubmitting(true);
    try {
      const created = await createListing(payload);
      router.push(`/listings/${created.id}`);
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
        <h1 className="text-2xl font-bold text-ink-900">Add Listing</h1>
        <div className="mt-6 rounded-2xl bg-red-50 px-6 py-4 ring-1 ring-red-200">
          <div className="font-semibold text-red-700">Could not load form.</div>
          <div className="mt-1 text-sm text-red-600">{loadError}</div>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-3xl font-bold text-ink-900">
          Add Listing<span className="text-brand-500">.</span>
        </h1>
        <Link
          href="/admin"
          className="text-sm font-semibold text-brand-600 hover:text-brand-700 transition-colors"
        >
          Back to Admin
        </Link>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Section title="Required">
          <Field label="Source" required>
            <select
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
              className={inputClass}
              required
            >
              {sources.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.provider_name} ({s.slug})
                </option>
              ))}
            </select>
          </Field>

          <Field label="Title" required>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className={inputClass}
              placeholder="e.g. Advanced Periodontal Surgery Wet Lab"
              required
            />
          </Field>

          <Field label="Source URL" required hint="Link to the original posting on the provider's site.">
            <input
              type="url"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              className={inputClass}
              placeholder="https://example.com/event/abc"
              required
            />
          </Field>

          <Field label="Schedule" required hint="Either a start date OR mark as on-demand.">
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm text-ink-700">
                <input
                  type="checkbox"
                  checked={onDemand}
                  onChange={(e) => setOnDemand(e.target.checked)}
                  className="accent-brand-500"
                />
                On demand (no fixed date)
              </label>
              {!onDemand && (
                <div className="grid grid-cols-2 gap-3">
                  <input
                    type="date"
                    value={startsAt}
                    onChange={(e) => setStartsAt(e.target.value)}
                    className={inputClass}
                    placeholder="Starts at"
                  />
                  <input
                    type="date"
                    value={endsAt}
                    onChange={(e) => setEndsAt(e.target.value)}
                    className={inputClass}
                    placeholder="Ends at (optional)"
                  />
                </div>
              )}
            </div>
          </Field>
        </Section>

        <Section title="Optional">
          <Field label="Description">
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className={inputClass}
              rows={4}
              placeholder="Short description shown on the listing card."
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
              placeholder="e.g. 8"
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

          {!onDemand && (
            <Field label="Format">
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value)}
                className={inputClass}
              >
                <option value="">— pick one (optional) —</option>
                {FORMAT_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </Field>
          )}

          <Field label="Audience">
            <select
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
              className={inputClass}
            >
              <option value="">— pick one (optional) —</option>
              {AUDIENCE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Subject category" hint="If left blank, the listing won't appear publicly until the AI tagger runs (daily). Pick a category to show it immediately.">
            <select
              value={subjectCategory}
              onChange={(e) => setSubjectCategory(e.target.value)}
              className={inputClass}
            >
              <option value="">— leave to AI tagger —</option>
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
              placeholder="e.g. Dr. Jane Smith, DVM, DAVDC"
            />
          </Field>

          <Field label="Registration URL" hint="Direct signup link, if different from source URL.">
            <input
              type="url"
              value={registrationUrl}
              onChange={(e) => setRegistrationUrl(e.target.value)}
              className={inputClass}
              placeholder="https://example.com/register"
            />
          </Field>

          <Field label="Cost" hint="Free-form text like 'Free' or '$450'.">
            <input
              type="text"
              value={cost}
              onChange={(e) => setCost(e.target.value)}
              className={inputClass}
              placeholder="e.g. $450"
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
            {submitting ? "Creating…" : "Create listing"}
          </button>
          <Link
            href="/admin"
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