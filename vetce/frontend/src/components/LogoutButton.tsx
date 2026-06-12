"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { adminLogout } from "@/lib/api";

export function LogoutButton() {
  const router = useRouter();
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    if (loggingOut) return;
    setLoggingOut(true);
    await adminLogout();
    router.push("/admin/login");
    router.refresh();
  }

  return (
    <button
      type="button"
      onClick={handleLogout}
      disabled={loggingOut}
      className="rounded-pill bg-brand-500 hover:bg-brand-600 disabled:bg-brand-300 disabled:cursor-not-allowed text-white px-5 py-2 text-sm font-semibold transition-colors"
    >
      {loggingOut ? "Signing out..." : "Sign out"}
    </button>
  );
}