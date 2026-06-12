"use client";

/**
 * /admin/login — password gate for the operations dashboard.
 *
 * Client component (we need state, form handlers, and a programmatic redirect).
 * On successful login, redirects to /admin where the dashboard renders.
 */
import { useRouter } from "next/navigation";
import { useState } from "react";

import { adminLogin, ApiError } from "@/lib/api";

export default function AdminLoginPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (submitting) return;

    if (!password) {
      setError("Please enter the password.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await adminLogin(password);
      router.push("/admin");
      router.refresh(); // refetch the now-authenticated dashboard
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Something went wrong. Please try again.";
      setError(message);
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-md px-6 py-20">
      <h1 className="text-3xl font-bold text-ink-900">
        Admin<span className="text-brand-500">.</span>
      </h1>
      <p className="mt-2 text-sm text-ink-600">
        This area is for PerioVive CE operators only.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-4" noValidate>
        <div>
          <label
            htmlFor="password"
            className="block text-sm font-medium text-ink-900"
          >
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={submitting}
            autoFocus
            className="mt-1 w-full rounded-pill border border-ink-200 px-5 py-3 text-ink-900 focus:outline-none focus:border-brand-500 disabled:bg-ink-50"
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-pill bg-brand-500 hover:bg-brand-600 disabled:bg-brand-300 disabled:cursor-not-allowed text-white px-6 py-3 font-semibold transition-colors"
        >
          {submitting ? "Signing in..." : "Sign in"}
        </button>

        {error && (
          <div className="rounded-2xl bg-red-50 px-4 py-3 ring-1 ring-red-200">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}
      </form>
    </main>
  );
}